import random
import logging
from datetime import datetime, timedelta
from fastapi import HTTPException, Response
from app.utils.email import send_otp_email
from app.utils.hashing import hash_password, verify_password
from app.utils.jwt import create_access_token, create_refresh_token, verify_token

logger = logging.getLogger(__name__)


def generate_otp() -> str:
    return str(random.randint(100000, 999999))


async def register(data, db):
    logger.info(f"Register attempt: {data.email}")

    user = await db.fetchrow("SELECT id FROM users WHERE email = $1", data.email)
    if user:
        logger.warning(f"Email already exists: {data.email}")
        raise HTTPException(status_code=400, detail="Email already registered")

    user = await db.fetchrow("SELECT id FROM users WHERE phone = $1", data.phone)
    if user:
        logger.warning(f"Phone already exists: {data.phone}")
        raise HTTPException(status_code=400, detail="Phone already registered")

    hashed = hash_password(data.password)
    user = await db.fetchrow(
        """
        INSERT INTO users (full_name, email, phone, password_hash)
        VALUES ($1, $2, $3, $4)
        RETURNING id, full_name, email, phone, role, is_verified, is_blocked, created_at
    """,
        data.full_name,
        data.email,
        data.phone,
        hashed,
    )

    logger.info(f"User registered successfully: {data.email}")
    return {
        "message": "User registered successfully",
        "user": {
            "id": str(user["id"]),
            "full_name": user["full_name"],
            "email": user["email"],
            "phone": user["phone"],
            "role": user["role"],
            "is_verified": user["is_verified"],
            "is_blocked": user["is_blocked"],
            "created_at": str(user["created_at"]),
        },
    }


async def login(data, response: Response, db):
    logger.info(f"Login attempt: {data.email}")

    user = await db.fetchrow(
        """
        SELECT id, full_name, email, password_hash, role, is_verified, is_blocked
        FROM users WHERE email = $1
    """,
        data.email,
    )

    if not user:
        logger.warning(f"User not found: {data.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(data.password, user["password_hash"]):
        logger.warning(f"Wrong password: {data.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user["is_blocked"]:
        logger.warning(f"Blocked user tried to login: {data.email}")
        raise HTTPException(status_code=403, detail="Your account has been blocked")

    access_token = create_access_token({"sub": str(user["id"]), "role": user["role"]})
    refresh_token = create_refresh_token({"sub": str(user["id"])})

    await db.execute(
        """
        UPDATE refresh_tokens
        SET revoked = TRUE
        WHERE user_id = $1 AND revoked = FALSE
    """,
        user["id"],
    )

    await db.execute(
        """
        INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
        VALUES ($1, $2, NOW() + INTERVAL '7 days')
    """,
        user["id"],
        refresh_token,
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=1800,
        samesite="lax",
        secure=False,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=604800,
        samesite="lax",
        secure=False,
    )

    logger.info(f"Login successful: {data.email}")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(user["id"]),
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role"],
            "is_verified": user["is_verified"],
            "is_blocked": user["is_blocked"],
        },
    }


async def refresh_token(data, response: Response, db):
    token = data.refresh_token

    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id = payload.get("sub")

    row = await db.fetchrow(
        """
        SELECT id FROM refresh_tokens 
        WHERE user_id = $1 AND token_hash = $2 AND revoked = FALSE AND expires_at > NOW()
    """,
        user_id,
        token,
    )

    if not row:
        raise HTTPException(status_code=401, detail="Refresh token revoked or expired")

    user = await db.fetchrow(
        """
        SELECT role, is_blocked FROM users WHERE id = $1
    """,
        user_id,
    )

    if user["is_blocked"]:
        raise HTTPException(status_code=403, detail="Your account has been blocked")

    new_access_token = create_access_token({"sub": user_id, "role": user["role"]})

    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        max_age=1800,
        samesite="lax",
        secure=False,
    )

    logger.info(f"Access token refreshed for user: {user_id}")
    return {"access_token": new_access_token, "token_type": "bearer"}


async def logout(data, response: Response, db):
    payload = verify_token(data.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    await db.execute(
        """
        UPDATE refresh_tokens 
        SET revoked = TRUE 
        WHERE token_hash = $1 AND revoked = FALSE
    """,
        data.refresh_token,
    )

    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")

    logger.info(f"User logged out: {payload.get('sub')}")
    return {"message": "Logged out successfully"}


async def get_me(current_user: dict, db):
    user_id = current_user.get("sub")

    user = await db.fetchrow(
        """
        SELECT id, full_name, email, phone, role, is_verified, is_blocked, created_at 
        FROM users WHERE id = $1
    """,
        user_id,
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(f"User info fetched: {user['email']}")
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


async def forgot_password(email: str, db):
    user = await db.fetchrow("SELECT id, full_name FROM users WHERE email = $1", email)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    otp = generate_otp()
    otp_expiry = datetime.utcnow() + timedelta(minutes=10)

    await db.execute(
        """
        UPDATE users 
        SET otp_code = $1, otp_purpose = $2, otp_expiry = $3
        WHERE email = $4
    """,
        otp,
        "forgot_password",
        otp_expiry,
        email,
    )

    sent = send_otp_email(email, otp, "forgot_password")
    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send OTP email")

    logger.info(f"OTP sent to {email}")
    return {"message": "OTP sent to your email"}


async def reset_password(email: str, otp: str, new_password: str, db):
    user = await db.fetchrow(
        """
        SELECT otp_code, otp_purpose, otp_expiry 
        FROM users WHERE email = $1
    """,
        email,
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user["otp_code"] != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if user["otp_purpose"] != "forgot_password":
        raise HTTPException(status_code=400, detail="Invalid OTP purpose")

    if datetime.utcnow() > user["otp_expiry"]:
        raise HTTPException(status_code=400, detail="OTP expired")

    hashed = hash_password(new_password)
    await db.execute(
        """
        UPDATE users 
        SET password_hash = $1, otp_code = NULL, otp_purpose = NULL, otp_expiry = NULL
        WHERE email = $2
    """,
        hashed,
        email,
    )

    logger.info(f"Password reset successful for {email}")
    return {"message": "Password reset successfully"}


async def send_otp(email: str, db):
    user = await db.fetchrow(
        "SELECT id, is_verified FROM users WHERE email = $1", email
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user["is_verified"]:
        raise HTTPException(status_code=400, detail="Email already verified")

    otp = generate_otp()
    otp_expiry = datetime.utcnow() + timedelta(minutes=10)

    await db.execute(
        """
        UPDATE users 
        SET otp_code = $1, otp_purpose = $2, otp_expiry = $3
        WHERE email = $4
    """,
        otp,
        "signup",
        otp_expiry,
        email,
    )

    sent = send_otp_email(email, otp, "signup")
    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send OTP email")

    logger.info(f"Signup OTP sent to {email}")
    return {"message": "OTP sent to your email"}


async def verify_otp(email: str, otp: str, db):
    user = await db.fetchrow(
        """
        SELECT otp_code, otp_purpose, otp_expiry, is_verified
        FROM users WHERE email = $1
    """,
        email,
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user["is_verified"]:
        raise HTTPException(status_code=400, detail="Email already verified")

    if user["otp_code"] != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if user["otp_purpose"] != "signup":
        raise HTTPException(status_code=400, detail="Invalid OTP purpose")

    if datetime.utcnow() > user["otp_expiry"]:
        raise HTTPException(status_code=400, detail="OTP expired")

    await db.execute(
        """
        UPDATE users 
        SET is_verified = TRUE, otp_code = NULL, otp_purpose = NULL, otp_expiry = NULL
        WHERE email = $1
    """,
        email,
    )

    logger.info(f"Email verified successfully: {email}")
    return {"message": "Email verified successfully"}
