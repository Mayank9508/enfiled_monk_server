import logging
from fastapi import HTTPException
from app.utils.hashing import hash_password

logger = logging.getLogger(__name__)


async def get_all_users(db):
    users = await db.fetch("""
        SELECT id, full_name, email, phone, role, is_verified, is_blocked, created_at
        FROM users ORDER BY created_at DESC
    """)

    logger.info("Admin fetched all users")
    return {
        "users": [
            {
                "id": str(u["id"]),
                "full_name": u["full_name"],
                "email": u["email"],
                "phone": u["phone"],
                "role": u["role"],
                "is_verified": u["is_verified"],
                "is_blocked": u["is_blocked"],
                "created_at": str(u["created_at"]),
            }
            for u in users
        ]
    }


async def get_user_by_id(user_id: str, db):
    user = await db.fetchrow(
        """
        SELECT id, full_name, email, phone, role, is_verified, is_blocked, addresses, created_at
        FROM users WHERE id = $1
    """,
        user_id,
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(f"Admin fetched user: {user_id}")
    return {
        "id": str(user["id"]),
        "full_name": user["full_name"],
        "email": user["email"],
        "phone": user["phone"],
        "role": user["role"],
        "is_verified": user["is_verified"],
        "is_blocked": user["is_blocked"],
        "addresses": user["addresses"],
        "created_at": str(user["created_at"]),
    }


async def create_user(data, db):
    existing = await db.fetchrow("SELECT id FROM users WHERE email = $1", data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    existing = await db.fetchrow("SELECT id FROM users WHERE phone = $1", data.phone)
    if existing:
        raise HTTPException(status_code=400, detail="Phone already registered")

    hashed = hash_password(data.password)
    user = await db.fetchrow(
        """
        INSERT INTO users (full_name, email, phone, password_hash, role, is_verified)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, full_name, email, phone, role, is_verified, is_blocked, created_at
    """,
        data.full_name,
        data.email,
        data.phone,
        hashed,
        data.role,
        data.is_verified,
    )

    logger.info(f"Admin created user: {data.email}")
    return {
        "id": str(user["id"]),
        "full_name": user["full_name"],
        "email": user["email"],
        "phone": user["phone"],
        "role": user["role"],
        "is_verified": user["is_verified"],
        "is_blocked": user["is_blocked"],
        "created_at": str(user["created_at"]),
    }


async def update_user(user_id: str, data, db):
    existing = await db.fetchrow("SELECT id FROM users WHERE id = $1", user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    fields = []
    params = []
    i = 1

    if data.full_name is not None:
        fields.append(f"full_name = ${i}")
        params.append(data.full_name)
        i += 1
    if data.phone is not None:
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
        RETURNING id, full_name, email, phone, role, is_verified, is_blocked, updated_at
    """,
        *params,
    )

    logger.info(f"Admin updated user: {user_id}")
    return {
        "id": str(user["id"]),
        "full_name": user["full_name"],
        "email": user["email"],
        "phone": user["phone"],
        "role": user["role"],
        "is_verified": user["is_verified"],
        "is_blocked": user["is_blocked"],
        "updated_at": str(user["updated_at"]),
    }


async def delete_user(user_id: str, db):
    existing = await db.fetchrow("SELECT id FROM users WHERE id = $1", user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    await db.execute("DELETE FROM users WHERE id = $1", user_id)

    logger.info(f"Admin deleted user: {user_id}")
    return {"message": "User deleted successfully"}


async def reset_user_password(user_id: str, data, db):
    existing = await db.fetchrow("SELECT id FROM users WHERE id = $1", user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    hashed = hash_password(data.new_password)
    await db.execute(
        """
        UPDATE users SET password_hash = $1, updated_at = NOW()
        WHERE id = $2
    """,
        hashed,
        user_id,
    )

    logger.info(f"Admin reset password for user: {user_id}")
    return {"message": "Password reset successfully"}


async def block_user(user_id: str, data, db):
    existing = await db.fetchrow("SELECT id FROM users WHERE id = $1", user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    await db.execute(
        """
        UPDATE users SET is_blocked = $1, updated_at = NOW()
        WHERE id = $2
    """,
        data.is_blocked,
        user_id,
    )

    action = "blocked" if data.is_blocked else "unblocked"
    logger.info(f"Admin {action} user: {user_id}")
    return {"message": f"User {action} successfully"}


async def verify_user(user_id: str, data, db):
    existing = await db.fetchrow("SELECT id FROM users WHERE id = $1", user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    await db.execute(
        """
        UPDATE users SET is_verified = $1, updated_at = NOW()
        WHERE id = $2
    """,
        data.is_verified,
        user_id,
    )

    action = "verified" if data.is_verified else "unverified"
    logger.info(f"Admin {action} user: {user_id}")
    return {"message": f"User {action} successfully"}


async def change_role(user_id: str, data, db):
    existing = await db.fetchrow("SELECT id FROM users WHERE id = $1", user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    if data.role not in ["user", "admin"]:
        raise HTTPException(
            status_code=400, detail="Invalid role — must be 'user' or 'admin'"
        )

    await db.execute(
        """
        UPDATE users SET role = $1, updated_at = NOW()
        WHERE id = $2
    """,
        data.role,
        user_id,
    )

    logger.info(f"Admin changed role for user: {user_id} to {data.role}")
    return {"message": f"User role changed to {data.role}"}
