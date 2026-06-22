import json
import logging
from fastapi import HTTPException
from app.utils.hashing import hash_password, verify_password

logger = logging.getLogger(__name__)


async def get_profile(current_user: dict, db):
    user_id = current_user.get("sub")

    user = await db.fetchrow(
        """
        SELECT id, full_name, email, phone, role, is_verified, is_blocked, addresses, created_at
        FROM users WHERE id = $1
    """,
        user_id,
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    raw = user["addresses"]
    addresses = json.loads(raw) if isinstance(raw, str) else list(raw) if raw else []

    logger.info(f"Profile fetched: {user['email']}")
    return {
        "id": str(user["id"]),
        "full_name": user["full_name"],
        "email": user["email"],
        "phone": user["phone"],
        "role": user["role"],
        "is_verified": user["is_verified"],
        "is_blocked": user["is_blocked"],
        "addresses": addresses,
        "created_at": str(user["created_at"]),
    }


async def update_profile(current_user: dict, data, db):
    user_id = current_user.get("sub")

    fields = []
    params = []
    i = 1

    if data.full_name is not None:
        fields.append(f"full_name = ${i}")
        params.append(data.full_name)
        i += 1

    if data.phone is not None:
        existing = await db.fetchrow(
            "SELECT id FROM users WHERE phone = $1 AND id != $2", data.phone, user_id
        )
        if existing:
            raise HTTPException(status_code=400, detail="Phone already in use")
        fields.append(f"phone = ${i}")
        params.append(data.phone)
        i += 1

    if not fields:
        raise HTTPException(status_code=400, detail="Nothing to update")

    fields.append("updated_at = NOW()")
    params.append(user_id)

    user = await db.fetchrow(
        f"""
        UPDATE users SET {', '.join(fields)}
        WHERE id = ${i}
        RETURNING id, full_name, email, phone, role, updated_at
    """,
        *params,
    )

    logger.info(f"Profile updated: {user_id}")
    return {
        "id": str(user["id"]),
        "full_name": user["full_name"],
        "email": user["email"],
        "phone": user["phone"],
        "role": user["role"],
        "updated_at": str(user["updated_at"]),
    }


async def add_address(current_user: dict, data, db):
    user_id = current_user.get("sub")

    user = await db.fetchrow("SELECT addresses FROM users WHERE id = $1", user_id)
    raw = user["addresses"]
    addresses = json.loads(raw) if isinstance(raw, str) else list(raw) if raw else []

    new_address = data.address.model_dump()

    if new_address["is_default"]:
        for addr in addresses:
            addr["is_default"] = False

    addresses.append(new_address)

    await db.execute(
        """
        UPDATE users SET addresses = $1, updated_at = NOW()
        WHERE id = $2
    """,
        json.dumps(addresses),
        user_id,
    )

    logger.info(f"Address added for user: {user_id}")
    return {"message": "Address added successfully", "addresses": addresses}


async def update_address(current_user: dict, index: int, data, db):
    user_id = current_user.get("sub")

    user = await db.fetchrow("SELECT addresses FROM users WHERE id = $1", user_id)
    raw = user["addresses"]
    addresses = json.loads(raw) if isinstance(raw, str) else list(raw) if raw else []

    if index < 0 or index >= len(addresses):
        raise HTTPException(status_code=404, detail="Address not found")

    # Purana address lo
    existing_address = addresses[index]

    # Sirf jo fields bheje hain wahi update karo
    updated = data.address.model_dump(exclude_none=True)
    existing_address.update(updated)

    # is_default handle karo
    if updated.get("is_default"):
        for i, addr in enumerate(addresses):
            if i != index:
                addr["is_default"] = False

    addresses[index] = existing_address

    await db.execute(
        """
        UPDATE users SET addresses = $1, updated_at = NOW()
        WHERE id = $2
    """,
        json.dumps(addresses),
        user_id,
    )

    logger.info(f"Address updated for user: {user_id}")
    return {"message": "Address updated successfully", "addresses": addresses}


async def delete_address(current_user: dict, index: int, db):
    user_id = current_user.get("sub")

    user = await db.fetchrow("SELECT addresses FROM users WHERE id = $1", user_id)
    raw = user["addresses"]
    addresses = json.loads(raw) if isinstance(raw, str) else list(raw) if raw else []

    if index < 0 or index >= len(addresses):
        raise HTTPException(status_code=404, detail="Address not found")

    addresses.pop(index)

    await db.execute(
        """
        UPDATE users SET addresses = $1, updated_at = NOW()
        WHERE id = $2
    """,
        json.dumps(addresses),
        user_id,
    )

    logger.info(f"Address deleted for user: {user_id}")
    return {"message": "Address deleted successfully", "addresses": addresses}


async def change_password(current_user: dict, data, db):
    user_id = current_user.get("sub")

    user = await db.fetchrow("SELECT password_hash FROM users WHERE id = $1", user_id)

    if not verify_password(data.old_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    hashed = hash_password(data.new_password)
    await db.execute(
        """
        UPDATE users SET password_hash = $1, updated_at = NOW()
        WHERE id = $2
    """,
        hashed,
        user_id,
    )

    logger.info(f"Password changed for user: {user_id}")
    return {"message": "Password changed successfully"}
