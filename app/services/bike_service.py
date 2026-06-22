import json
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def get_all_bikes(db, series=None, city=None, status="available"):
    query = "SELECT * FROM bikes WHERE 1=1"
    params = []
    i = 1

    if status:
        query += f" AND status = ${i}"
        params.append(status)
        i += 1

    if series:
        query += f" AND series = ${i}"
        params.append(series)
        i += 1

    if city:
        query += f" AND available_cities @> ${i}::jsonb"
        params.append(json.dumps([city]))
        i += 1

    query += " ORDER BY created_at DESC"

    bikes = await db.fetch(query, *params)
    return {"bikes": [format_bike(b) for b in bikes]}


async def get_bike_by_id(bike_id: str, db):
    bike = await db.fetchrow("SELECT * FROM bikes WHERE id = $1", bike_id)

    if not bike:
        raise HTTPException(status_code=404, detail="Bike not found")

    return format_bike(bike)


async def create_bike(data, db):
    bike = await db.fetchrow(
        """
        INSERT INTO bikes 
        (series, variant, engine_cc, title, description, rent_price_per_day, 
         security_deposit, images, available_cities, specifications, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        RETURNING *
    """,
        data.series,
        data.variant,
        data.engine_cc,
        data.title,
        data.description,
        data.rent_price_per_day,
        data.security_deposit,
        json.dumps(data.images),
        json.dumps(data.available_cities),
        json.dumps(data.specifications),
        data.status,
    )

    logger.info(f"Bike created: {data.title}")
    return format_bike(bike)


async def update_bike(bike_id: str, data, db):
    existing = await db.fetchrow("SELECT id FROM bikes WHERE id = $1", bike_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Bike not found")

    fields = []
    params = []
    i = 1

    field_map = {
        "series": data.series,
        "variant": data.variant,
        "engine_cc": data.engine_cc,
        "title": data.title,
        "description": data.description,
        "rent_price_per_day": data.rent_price_per_day,
        "security_deposit": data.security_deposit,
        "status": data.status,
    }

    for column, value in field_map.items():
        if value is not None:
            fields.append(f"{column} = ${i}")
            params.append(value)
            i += 1

    if data.images is not None:
        fields.append(f"images = ${i}")
        params.append(json.dumps(data.images))
        i += 1

    if data.available_cities is not None:
        fields.append(f"available_cities = ${i}")
        params.append(json.dumps(data.available_cities))
        i += 1

    if data.specifications is not None:
        fields.append(f"specifications = ${i}")
        params.append(json.dumps(data.specifications))
        i += 1

    if not fields:
        raise HTTPException(status_code=400, detail="Nothing to update")

    params.append(bike_id)

    bike = await db.fetchrow(
        f"""
        UPDATE bikes SET {', '.join(fields)}
        WHERE id = ${i} RETURNING *
    """,
        *params,
    )

    logger.info(f"Bike updated: {bike_id}")
    return format_bike(bike)


async def delete_bike(bike_id: str, db):
    existing = await db.fetchrow("SELECT id FROM bikes WHERE id = $1", bike_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Bike not found")

    await db.execute("UPDATE bikes SET status = 'maintenance' WHERE id = $1", bike_id)

    logger.info(f"Bike removed: {bike_id}")
    return {"message": "Bike removed successfully"}


def format_bike(b):
    images = json.loads(b["images"]) if isinstance(b["images"], str) else b["images"]
    available_cities = (
        json.loads(b["available_cities"])
        if isinstance(b["available_cities"], str)
        else b["available_cities"]
    )
    specifications = (
        json.loads(b["specifications"])
        if isinstance(b["specifications"], str)
        else b["specifications"]
    )

    return {
        "id": str(b["id"]),
        "series": b["series"],
        "variant": b["variant"],
        "engine_cc": b["engine_cc"],
        "title": b["title"],
        "description": b["description"],
        "rent_price_per_day": float(b["rent_price_per_day"]),
        "security_deposit": float(b["security_deposit"]),
        "images": images,
        "available_cities": available_cities,
        "specifications": specifications,
        "status": b["status"],
        "created_at": str(b["created_at"]),
    }
