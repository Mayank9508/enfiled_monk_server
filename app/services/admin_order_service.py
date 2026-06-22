import json
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def get_all_orders(db, status=None, payment_status=None):
    query = """
        SELECT orders.id, orders.user_id, users.full_name, users.email,
               orders.subtotal, orders.discount_amount, orders.gst_amount, orders.total_amount,
               orders.payment_method, orders.payment_status, orders.status, orders.created_at
        FROM orders
        JOIN users ON users.id = orders.user_id
        WHERE 1=1 
    """
    params = []
    i = 1

    if status:
        query += f" AND orders.status = ${i}"
        params.append(status)
        i += 1

    if payment_status:
        query += f" AND orders.payment_status = ${i}"
        params.append(payment_status)
        i += 1

    query += " ORDER BY orders.created_at DESC"

    orders = await db.fetch(query, *params)

    return {
        "orders": [
            {
                "id": str(o["id"]),
                "user_id": str(o["user_id"]),
                "customer_name": o["full_name"],
                "customer_email": o["email"],
                "subtotal": float(o["subtotal"]),
                "discount_amount": float(o["discount_amount"]),
                "gst_amount": float(o["gst_amount"]),
                "total_amount": float(o["total_amount"]),
                "payment_method": o["payment_method"],
                "payment_status": o["payment_status"],
                "status": o["status"],
                "created_at": str(o["created_at"]),
            }
            for o in orders
        ]
    }


async def get_order_by_id(order_id: str, db):
    order = await db.fetchrow(
        """
        SELECT orders.id, orders.user_id, users.full_name, users.email, users.phone,
               orders.delivery_address, orders.subtotal, orders.discount_amount, orders.gst_amount,
               orders.total_amount, orders.payment_method, orders.payment_status, orders.status, orders.created_at
        FROM orders
        JOIN users ON users.id = orders.user_id
        WHERE orders.id = $1
    """,
        order_id,
    )

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

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
        "customer_name": order["full_name"],
        "customer_email": order["email"],
        "customer_phone": order["phone"],
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


async def update_order_status(order_id: str, status: str, db):
    valid_statuses = ["cart", "confirmed", "shipped", "delivered", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400, detail=f"Invalid status — must be one of {valid_statuses}"
        )

    existing = await db.fetchrow("SELECT id FROM orders WHERE id = $1", order_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Order not found")

    await db.execute("UPDATE orders SET status = $1 WHERE id = $2", status, order_id)

    logger.info(f"Admin updated order status: {order_id} to {status}")
    return {"message": f"Order status updated to '{status}'"}


async def update_payment_status(order_id: str, payment_status: str, db):
    valid_statuses = ["pending", "paid", "failed", "refunded"]
    if payment_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid payment status — must be one of {valid_statuses}",
        )

    existing = await db.fetchrow("SELECT id FROM orders WHERE id = $1", order_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Order not found")

    await db.execute(
        "UPDATE orders SET payment_status = $1 WHERE id = $2", payment_status, order_id
    )

    logger.info(f"Admin updated payment status: {order_id} to {payment_status}")
    return {"message": f"Payment status updated to '{payment_status}'"}
