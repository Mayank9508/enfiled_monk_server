import json
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def get_cart(user_id: str, session_id: str, db):
    if user_id:
        items = await db.fetch(
            """
            SELECT cart_items.id, cart_items.product_id, cart_items.quantity, 
                   products.name, products.slug, products.price, products.sale_price, 
                   products.images, products.stock, products.is_active
            FROM cart_items
            JOIN products ON products.id = cart_items.product_id
            WHERE cart_items.user_id = $1
            ORDER BY cart_items.created_at DESC
        """,
            user_id,
        )
    else:
        items = await db.fetch(
            """
            SELECT cart_items.id, cart_items.product_id, cart_items.quantity, 
                   products.name, products.slug, products.price, products.sale_price, 
                   products.images, products.stock, products.is_active
            FROM cart_items
            JOIN products ON products.id = cart_items.product_id
            WHERE cart_items.session_id = $1
            ORDER BY cart_items.created_at DESC
        """,
            session_id,
        )

    cart_items = []
    total = 0
    has_issues = False

    for item in items:
        if item["sale_price"]:
            price = float(item["sale_price"])
        else:
            price = float(item["price"])

        if item["sale_price"]:
            sale_price_value = float(item["sale_price"])
        else:
            sale_price_value = None

        images = (
            json.loads(item["images"])
            if isinstance(item["images"], str)
            else item["images"]
        )

        # Stock / availability check
        is_out_of_stock = not item["is_active"] or item["stock"] == 0
        has_insufficient_stock = item["stock"] < item["quantity"] and item["stock"] > 0

        if is_out_of_stock or has_insufficient_stock:
            has_issues = True

        subtotal = price * item["quantity"]
        total += subtotal

        cart_items.append(
            {
                "id": str(item["id"]),
                "product_id": str(item["product_id"]),
                "name": item["name"],
                "slug": item["slug"],
                "price": float(item["price"]),
                "sale_price": sale_price_value,
                "quantity": item["quantity"],
                "stock": item["stock"],
                "images": images,
                "subtotal": subtotal,
                "is_out_of_stock": is_out_of_stock,
                "has_insufficient_stock": has_insufficient_stock,
            }
        )

    return {
        "items": cart_items,
        "total": total,
        "item_count": len(cart_items),
        "has_issues": has_issues,
    }


async def add_to_cart(user_id: str, session_id: str, data, db):
    product = await db.fetchrow(
        "SELECT id, stock FROM products WHERE id = $1 AND is_active = TRUE",
        data.product_id,
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product["stock"] < data.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    if user_id:
        existing = await db.fetchrow(
            """
            SELECT id, quantity FROM cart_items 
            WHERE user_id = $1 AND product_id = $2
        """,
            user_id,
            data.product_id,
        )
    else:
        existing = await db.fetchrow(
            """
            SELECT id, quantity FROM cart_items 
            WHERE session_id = $1 AND product_id = $2
        """,
            session_id,
            data.product_id,
        )

    if existing:
        new_qty = existing["quantity"] + data.quantity
        await db.execute(
            """
            UPDATE cart_items SET quantity = $1, updated_at = NOW()
            WHERE id = $2
        """,
            new_qty,
            existing["id"],
        )
        logger.info(f"Cart item quantity updated: {existing['id']}")
        return {"message": "Cart updated successfully"}

    if user_id:
        await db.execute(
            """
            INSERT INTO cart_items (user_id, product_id, quantity)
            VALUES ($1, $2, $3)
        """,
            user_id,
            data.product_id,
            data.quantity,
        )
    else:
        await db.execute(
            """
            INSERT INTO cart_items (session_id, product_id, quantity)
            VALUES ($1, $2, $3)
        """,
            session_id,
            data.product_id,
            data.quantity,
        )

    logger.info(f"Item added to cart: {data.product_id}")
    return {"message": "Item added to cart successfully"}


async def update_cart_item(cart_item_id: str, user_id: str, session_id: str, data, db):
    if user_id:
        existing = await db.fetchrow(
            """
            SELECT cart_items.id, cart_items.product_id, products.stock 
            FROM cart_items
            JOIN products ON products.id = cart_items.product_id
            WHERE cart_items.id = $1 AND cart_items.user_id = $2
        """,
            cart_item_id,
            user_id,
        )
    else:
        existing = await db.fetchrow(
            """
            SELECT cart_items.id, cart_items.product_id, products.stock 
            FROM cart_items
            JOIN products ON products.id = cart_items.product_id
            WHERE cart_items.id = $1 AND cart_items.session_id = $2
        """,
            cart_item_id,
            session_id,
        )

    if not existing:
        raise HTTPException(status_code=404, detail="Cart item not found")

    if data.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")

    if data.quantity > existing["stock"]:
        raise HTTPException(
            status_code=400, detail=f"Only {existing['stock']} items available in stock"
        )

    await db.execute(
        """
        UPDATE cart_items SET quantity = $1, updated_at = NOW()
        WHERE id = $2
    """,
        data.quantity,
        cart_item_id,
    )

    logger.info(f"Cart item updated: {cart_item_id}")
    return {"message": "Cart item updated successfully"}


async def remove_cart_item(cart_item_id: str, user_id: str, session_id: str, db):
    if user_id:
        existing = await db.fetchrow(
            "SELECT id FROM cart_items WHERE id = $1 AND user_id = $2",
            cart_item_id,
            user_id,
        )
    else:
        existing = await db.fetchrow(
            "SELECT id FROM cart_items WHERE id = $1 AND session_id = $2",
            cart_item_id,
            session_id,
        )

    if not existing:
        raise HTTPException(status_code=404, detail="Cart item not found")

    await db.execute("DELETE FROM cart_items WHERE id = $1", cart_item_id)

    logger.info(f"Cart item removed: {cart_item_id}")
    return {"message": "Item removed from cart successfully"}


async def merge_cart(user_id: str, session_id: str, db):
    guest_items = await db.fetch(
        "SELECT product_id, quantity FROM cart_items WHERE session_id = $1", session_id
    )

    for item in guest_items:
        existing = await db.fetchrow(
            """
            SELECT id, quantity FROM cart_items 
            WHERE user_id = $1 AND product_id = $2
        """,
            user_id,
            item["product_id"],
        )

        if existing:
            new_qty = existing["quantity"] + item["quantity"]
            await db.execute(
                "UPDATE cart_items SET quantity = $1, updated_at = NOW() WHERE id = $2",
                new_qty,
                existing["id"],
            )
        else:
            await db.execute(
                """
                INSERT INTO cart_items (user_id, product_id, quantity)
                VALUES ($1, $2, $3)
            """,
                user_id,
                item["product_id"],
                item["quantity"],
            )

    await db.execute("DELETE FROM cart_items WHERE session_id = $1", session_id)

    logger.info(f"Guest cart merged for user: {user_id}")
    return {"message": "Cart merged successfully"}


async def clear_cart(user_id: str, session_id: str, db):
    if user_id:
        await db.execute("DELETE FROM cart_items WHERE user_id = $1", user_id)
    else:
        await db.execute("DELETE FROM cart_items WHERE session_id = $1", session_id)

    logger.info(
        f"Cart cleared for {'user: ' + user_id if user_id else 'session: ' + session_id}"
    )
    return {"message": "Cart cleared successfully"}
