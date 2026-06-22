import json
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

GST_RATE = 0.18  # 18% GST


async def place_order(user_id: str, data, db):
    # Step 1: Cart items fetch karo
    cart_items = await db.fetch(
        """
        SELECT cart_items.id, cart_items.product_id, cart_items.quantity,
               products.name, products.price, products.sale_price, products.stock, products.is_active
        FROM cart_items
        JOIN products ON products.id = cart_items.product_id
        WHERE cart_items.user_id = $1
    """,
        user_id,
    )

    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Step 2: Stock check karo har product ka
    for item in cart_items:
        if not item["is_active"]:
            raise HTTPException(
                status_code=400, detail=f"{item['name']} is no longer available"
            )
        if item["stock"] < item["quantity"]:
            raise HTTPException(
                status_code=400, detail=f"Insufficient stock for {item['name']}"
            )

    # Step 3: Address decide karo
    delivery_address = await resolve_address(user_id, data, db)

    # Step 4: Subtotal calculate karo
    subtotal = 0
    for item in cart_items:
        if item["sale_price"]:
            price = float(item["sale_price"])
        else:
            price = float(item["price"])
        subtotal += price * item["quantity"]

    # Step 5: Coupon apply karo (agar diya hai)
    discount_amount = 0
    coupon_id = None

    if data.coupon_code:
        coupon = await validate_coupon(data.coupon_code, subtotal, db)
        coupon_id = coupon["id"]
        if coupon["discount_type"] == "flat":
            discount_amount = float(coupon["discount_value"])
        else:  # percent
            discount_amount = subtotal * (float(coupon["discount_value"]) / 100)
            if coupon["max_discount"]:
                discount_amount = min(discount_amount, float(coupon["max_discount"]))

    # Step 6: GST aur total calculate karo
    taxable_amount = subtotal - discount_amount
    gst_amount = taxable_amount * GST_RATE
    total_amount = taxable_amount + gst_amount

    # Step 7: Order banao
    order = await db.fetchrow(
        """
        INSERT INTO orders 
        (user_id, coupon_id, delivery_address, subtotal, discount_amount, gst_amount, total_amount, payment_method, payment_status, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING id, created_at
    """,
        user_id,
        coupon_id,
        json.dumps(delivery_address),
        subtotal,
        discount_amount,
        gst_amount,
        total_amount,
        data.payment_method,
        "pending",
        "confirmed",
    )

    order_id = order["id"]

    # Step 8: Order items banao + stock minus karo
    for item in cart_items:
        if item["sale_price"]:
            unit_price = float(item["sale_price"])
        else:
            unit_price = float(item["price"])

        total_price = unit_price * item["quantity"]

        await db.execute(
            """
            INSERT INTO order_items (order_id, product_id, quantity, unit_price, total_price)
            VALUES ($1, $2, $3, $4, $5)
        """,
            order_id,
            item["product_id"],
            item["quantity"],
            unit_price,
            total_price,
        )

        await db.execute(
            """
            UPDATE products SET stock = stock - $1 WHERE id = $2
        """,
            item["quantity"],
            item["product_id"],
        )

    # Step 9: Coupon used_count badhao
    if coupon_id:
        await db.execute(
            "UPDATE coupons SET used_count = used_count + 1 WHERE id = $1", coupon_id
        )

    # Step 10: Cart khali karo
    await db.execute("DELETE FROM cart_items WHERE user_id = $1", user_id)

    logger.info(f"Order placed: {order_id} for user: {user_id}")

    return {
        "message": "Order placed successfully",
        "order": {
            "id": str(order_id),
            "subtotal": subtotal,
            "discount_amount": discount_amount,
            "gst_amount": gst_amount,
            "total_amount": total_amount,
            "payment_method": data.payment_method,
            "status": "confirmed",
            "created_at": str(order["created_at"]),
        },
    }


async def resolve_address(user_id: str, data, db):
    user = await db.fetchrow("SELECT addresses FROM users WHERE id = $1", user_id)
    raw = user["addresses"]
    addresses = json.loads(raw) if isinstance(raw, str) else list(raw) if raw else []

    if data.new_address:
        return data.new_address.model_dump()

    if data.address_index is not None:
        if data.address_index < 0 or data.address_index >= len(addresses):
            raise HTTPException(status_code=400, detail="Invalid address index")
        return addresses[data.address_index]

    # Koi address nahi diya — default address use karo agar hai
    for addr in addresses:
        if addr.get("is_default"):
            return addr

    if addresses:
        return addresses[0]

    raise HTTPException(
        status_code=400, detail="No address provided and no saved address found"
    )


async def validate_coupon(code: str, subtotal: float, db):
    coupon = await db.fetchrow(
        """
        SELECT id, discount_type, discount_value, min_order_amount, max_discount, 
               expires_at, usage_limit, used_count, is_active
        FROM coupons WHERE code = $1
    """,
        code,
    )

    if not coupon:
        raise HTTPException(status_code=400, detail="Invalid coupon code")

    if not coupon["is_active"]:
        raise HTTPException(status_code=400, detail="Coupon is not active")

    if (
        coupon["expires_at"]
        and coupon["expires_at"] < __import__("datetime").datetime.utcnow()
    ):
        raise HTTPException(status_code=400, detail="Coupon has expired")

    if coupon["usage_limit"] and coupon["used_count"] >= coupon["usage_limit"]:
        raise HTTPException(status_code=400, detail="Coupon usage limit reached")

    if coupon["min_order_amount"] and subtotal < float(coupon["min_order_amount"]):
        raise HTTPException(
            status_code=400,
            detail=f"Minimum order amount is {coupon['min_order_amount']}",
        )

    return coupon


async def get_my_orders(user_id: str, db):
    orders = await db.fetch(
        """
        SELECT id, subtotal, discount_amount, gst_amount, total_amount, 
               payment_method, payment_status, status, created_at
        FROM orders WHERE user_id = $1 ORDER BY created_at DESC
    """,
        user_id,
    )

    return {"orders": [format_order(o) for o in orders]}


async def get_order_by_id(order_id: str, user_id: str, db):
    order = await db.fetchrow(
        """
        SELECT id, user_id, delivery_address, subtotal, discount_amount, gst_amount, 
               total_amount, payment_method, payment_status, status, created_at
        FROM orders WHERE id = $1
    """,
        order_id,
    )

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if str(order["user_id"]) != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this order")

    items = await db.fetch(
        """
        SELECT order_items.id, order_items.product_id, order_items.quantity, 
               order_items.unit_price, order_items.total_price, products.name, products.images
        FROM order_items
        JOIN products ON products.id = order_items.product_id
        WHERE order_items.order_id = $1
    """,
        order_id,
    )

    raw_addr = order["delivery_address"]
    address = json.loads(raw_addr) if isinstance(raw_addr, str) else raw_addr

    return {
        "id": str(order["id"]),
        "delivery_address": address,
        "subtotal": float(order["subtotal"]),
        "discount_amount": float(order["discount_amount"]),
        "gst_amount": float(order["gst_amount"]),
        "total_amount": float(order["total_amount"]),
        "payment_method": order["payment_method"],
        "payment_status": order["payment_status"],
        "status": order["status"],
        "created_at": str(order["created_at"]),
        "items": [
            {
                "id": str(i["id"]),
                "product_id": str(i["product_id"]),
                "name": i["name"],
                "images": (
                    json.loads(i["images"])
                    if isinstance(i["images"], str)
                    else i["images"]
                ),
                "quantity": i["quantity"],
                "unit_price": float(i["unit_price"]),
                "total_price": float(i["total_price"]),
            }
            for i in items
        ],
    }


def format_order(o):
    return {
        "id": str(o["id"]),
        "subtotal": float(o["subtotal"]),
        "discount_amount": float(o["discount_amount"]),
        "gst_amount": float(o["gst_amount"]),
        "total_amount": float(o["total_amount"]),
        "payment_method": o["payment_method"],
        "payment_status": o["payment_status"],
        "status": o["status"],
        "created_at": str(o["created_at"]),
    }


async def cancel_order(order_id: str, user_id: str, db):
    order = await db.fetchrow(
        """
        SELECT id, user_id, status FROM orders WHERE id = $1
    """,
        order_id,
    )

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if str(order["user_id"]) != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to cancel this order"
        )

    if order["status"] in ["shipped", "delivered", "cancelled"]:
        raise HTTPException(
            status_code=400,
            detail=f"Order cannot be cancelled — current status is '{order['status']}'",
        )

    # Order items lo aur stock wapas add karo
    items = await db.fetch(
        """
        SELECT product_id, quantity FROM order_items WHERE order_id = $1
    """,
        order_id,
    )

    for item in items:
        await db.execute(
            """
            UPDATE products SET stock = stock + $1 WHERE id = $2
        """,
            item["quantity"],
            item["product_id"],
        )

    # Order status update karo
    await db.execute(
        """
        UPDATE orders SET status = 'cancelled' WHERE id = $1
    """,
        order_id,
    )

    logger.info(f"Order cancelled: {order_id} by user: {user_id}")
    return {"message": "Order cancelled successfully"}
