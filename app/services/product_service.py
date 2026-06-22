import json
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def get_all_products(db, category=None, sub_category=None, search=None):
    query = "SELECT * FROM products WHERE is_active = TRUE"
    params = []
    i = 1

    if category:
        query += f" AND category = ${i}"
        params.append(category)
        i += 1

    if sub_category:
        query += f" AND sub_category = ${i}"
        params.append(sub_category)
        i += 1

    if search:
        query += f" AND name ILIKE ${i}"
        params.append(f"%{search}%")
        i += 1

    query += " ORDER BY created_at DESC"

    products = await db.fetch(query, *params)
    return {"products": [format_product(p) for p in products]}


async def get_product_by_id(product_id: str, db):
    product = await db.fetchrow("SELECT * FROM products WHERE id = $1", product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return format_product(product)


async def create_product(data, db):
    existing = await db.fetchrow("SELECT id FROM products WHERE slug = $1", data.slug)
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists")

    product = await db.fetchrow(
        """
        INSERT INTO products 
        (category, sub_category, child_category, name, slug, description, 
        price, sale_price, stock, images, compatible_bikes, is_active)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        RETURNING *
    """,
        data.category,
        data.sub_category,
        data.child_category,
        data.name,
        data.slug,
        data.description,
        data.price,
        data.sale_price,
        data.stock,
        json.dumps(data.images),
        json.dumps(data.compatible_bikes),
        data.is_active,
    )

    logger.info(f"Product created: {data.name}")
    return format_product(product)


async def update_product(product_id: str, data, db):
    existing = await db.fetchrow("SELECT id FROM products WHERE id = $1", product_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")

    fields = []
    params = []
    i = 1

    if data.category is not None:
        fields.append(f"category = ${i}")
        params.append(data.category)
        i += 1
    if data.sub_category is not None:
        fields.append(f"sub_category = ${i}")
        params.append(data.sub_category)
        i += 1
    if data.child_category is not None:
        fields.append(f"child_category = ${i}")
        params.append(data.child_category)
        i += 1
    if data.name is not None:
        fields.append(f"name = ${i}")
        params.append(data.name)
        i += 1
    if data.slug is not None:
        fields.append(f"slug = ${i}")
        params.append(data.slug)
        i += 1
    if data.description is not None:
        fields.append(f"description = ${i}")
        params.append(data.description)
        i += 1
    if data.price is not None:
        fields.append(f"price = ${i}")
        params.append(data.price)
        i += 1
    if data.sale_price is not None:
        fields.append(f"sale_price = ${i}")
        params.append(data.sale_price)
        i += 1
    if data.stock is not None:
        fields.append(f"stock = ${i}")
        params.append(data.stock)
        i += 1
    if data.images is not None:
        fields.append(f"images = ${i}")
        params.append(json.dumps(data.images))
        i += 1
    if data.compatible_bikes is not None:
        fields.append(f"compatible_bikes = ${i}")
        params.append(json.dumps(data.compatible_bikes))
        i += 1
    if data.is_active is not None:
        fields.append(f"is_active = ${i}")
        params.append(data.is_active)
        i += 1

    fields.append("updated_at = NOW()")
    params.append(product_id)

    product = await db.fetchrow(
        f"""
        UPDATE products SET {', '.join(fields)}
        WHERE id = ${i} RETURNING *
    """,
        *params,
    )

    logger.info(f"Product updated: {product_id}")
    return format_product(product)


async def delete_product(product_id: str, db):
    existing = await db.fetchrow("SELECT id FROM products WHERE id = $1", product_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.execute("UPDATE products SET is_active = FALSE WHERE id = $1", product_id)

    logger.info(f"Product deleted: {product_id}")
    return {"message": "Product deleted successfully"}


def format_product(p):
    images = json.loads(p["images"]) if isinstance(p["images"], str) else p["images"]
    compatible_bikes = json.loads(p["compatible_bikes"]) if isinstance(p["compatible_bikes"], str) else p["compatible_bikes"]
    
    return {
        "id": str(p["id"]),
        "category": p["category"],
        "sub_category": p["sub_category"],
        "child_category": p["child_category"],
        "name": p["name"],
        "slug": p["slug"],
        "description": p["description"],
        "price": float(p["price"]),
        "sale_price": float(p["sale_price"]) if p["sale_price"] else None,
        "stock": p["stock"],
        "images": images,
        "compatible_bikes": compatible_bikes,
        "is_active": p["is_active"],
        "created_at": str(p["created_at"]),
        "updated_at": str(p["updated_at"])
    }
