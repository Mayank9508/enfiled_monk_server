import json
import logging
from datetime import date
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def check_availability(bike_id: str, db):
    bike = await db.fetchrow("SELECT id, rent_price_per_day, security_deposit FROM bikes WHERE id = $1", bike_id)
    if not bike:
        raise HTTPException(status_code=404, detail="Bike not found")

    available_count = await db.fetchval("""
        SELECT COUNT(*) FROM bike_units WHERE bike_id = $1 AND status = 'available'
    """, bike_id)

    return {
        "bike_id": bike_id,
        "available_units": available_count,
        "is_available": available_count > 0,
        "rent_price_per_day": float(bike["rent_price_per_day"]),
        "security_deposit": float(bike["security_deposit"])
    }


async def create_booking(user_id: str, data, db):
    if data.end_date <= data.start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    if data.start_date < date.today():
        raise HTTPException(status_code=400, detail="Start date cannot be in the past")

    bike = await db.fetchrow("""
        SELECT id, rent_price_per_day, security_deposit, available_cities FROM bikes WHERE id = $1
    """, data.bike_id)

    if not bike:
        raise HTTPException(status_code=404, detail="Bike not found")

    raw_cities = bike["available_cities"]
    available_cities = json.loads(raw_cities) if isinstance(raw_cities, str) else raw_cities

    if data.city not in available_cities:
        raise HTTPException(
            status_code=400,
            detail=f"This bike is not available in '{data.city}'. Available cities: {available_cities}"
        )

    available_unit = await db.fetchrow("""
        SELECT id FROM bike_units 
        WHERE bike_id = $1 AND status = 'available'
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    """, data.bike_id)

    if not available_unit:
        raise HTTPException(status_code=400, detail="No bike units available for this model right now")

    days = (data.end_date - data.start_date).days
    amount = float(bike["rent_price_per_day"]) * days

    booking = await db.fetchrow("""
        INSERT INTO bookings 
        (user_id, bike_id, bike_unit_id, booking_type, city, start_date, end_date, 
         amount, status, notes)
        VALUES ($1, $2, $3, 'rental', $4, $5, $6, $7, 'confirmed', $8)
        RETURNING id, created_at
    """, user_id, data.bike_id, available_unit["id"], data.city, data.start_date,
         data.end_date, amount, data.notes)

    await db.execute("UPDATE bike_units SET status = 'rented' WHERE id = $1", available_unit["id"])

    logger.info(f"Booking created: {booking['id']} for user: {user_id}")

    return {
        "message": "Bike booked successfully",
        "booking": {
            "id": str(booking["id"]),
            "bike_id": data.bike_id,
            "city": data.city,
            "start_date": str(data.start_date),
            "end_date": str(data.end_date),
            "days": days,
            "amount": amount,
            "security_deposit": float(bike["security_deposit"]),
            "status": "confirmed",
            "created_at": str(booking["created_at"])
        }
    }


async def get_my_bookings(user_id: str, db):
    bookings = await db.fetch("""
        SELECT bookings.id, bookings.bike_id, bikes.series, bikes.variant, bikes.title,
               bookings.city, bookings.start_date, bookings.end_date, bookings.amount, 
               bookings.status, bookings.created_at
        FROM bookings
        JOIN bikes ON bikes.id = bookings.bike_id
        WHERE bookings.user_id = $1 AND bookings.booking_type = 'rental'
        ORDER BY bookings.created_at DESC
    """, user_id)

    return {"bookings": [
        {
            "id": str(b["id"]),
            "bike_id": str(b["bike_id"]),
            "bike_title": b["title"],
            "series": b["series"],
            "variant": b["variant"],
            "city": b["city"],
            "start_date": str(b["start_date"]),
            "end_date": str(b["end_date"]),
            "amount": float(b["amount"]),
            "status": b["status"],
            "created_at": str(b["created_at"])
        } for b in bookings
    ]}


async def cancel_booking(booking_id: str, user_id: str, db):
    booking = await db.fetchrow("""
        SELECT id, user_id, bike_unit_id, status FROM bookings WHERE id = $1
    """, booking_id)

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if str(booking["user_id"]) != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this booking")

    if booking["status"] in ["completed", "cancelled"]:
        raise HTTPException(status_code=400, detail=f"Booking cannot be cancelled — current status is '{booking['status']}'")

    await db.execute("UPDATE bookings SET status = 'cancelled' WHERE id = $1", booking_id)

    if booking["bike_unit_id"]:
        await db.execute("UPDATE bike_units SET status = 'available' WHERE id = $1", booking["bike_unit_id"])

    logger.info(f"Booking cancelled: {booking_id}")
    return {"message": "Booking cancelled successfully"}