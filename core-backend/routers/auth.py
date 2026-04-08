import secrets
import traceback
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from jose import jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import engine, User, Wallet, settings

ERROR_LOG = "error.log"


def log_error(msg: str):
    with open(ERROR_LOG, "a") as f:
        f.write(f"{msg}\n")
        f.write(traceback.format_exc())
        f.write("\n")


router = APIRouter(prefix="/auth", tags=["auth"])

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    email: str


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=ALGORITHM)


def get_base_url() -> str:
    return settings.google_redirect_uri.replace("/auth/google/callback", "")


async def get_current_user(authorization: Optional[str] = Header(None)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM], options={"verify_exp": False})
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    async with AsyncSession(engine) as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user


@router.get("/google/login")
async def google_login(show_token: str = "false"):
    state = secrets.token_urlsafe(16)
    if show_token == "true":
        state = f"show_token:true:{state}"
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.google_client_id}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"redirect_uri={settings.google_redirect_uri}&"
        f"state={state}"
    )
    return RedirectResponse(url=google_auth_url, status_code=302)


@router.get("/google/callback")
async def google_callback(code: str, state: str = ""):
    show_token = False
    if state and state.startswith("show_token:true:"):
        show_token = True
        state = state.replace("show_token:true:", "")
    
    try:
        from httpx import AsyncClient
        token_url = "https://oauth2.googleapis.com/token"

        async with AsyncClient() as client:
            token_response = await client.post(token_url, data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code"
            })

        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Token exchange failed: {token_response.text}")

        token_data = token_response.json()
        id_token_str = token_data.get("id_token")

        try:
            id_info = id_token.verify_oauth2_token(id_token_str, google_requests.Request(), audience=settings.google_client_id)
        except Exception:
            import base64
            import json
            parts = id_token_str.split('.')
            padded = parts[1] + '=' * (4 - len(parts[1]) % 4)
            id_info = json.loads(base64.urlsafe_b64decode(padded))

        email = id_info["email"]
        google_id = id_info["sub"]

        async with AsyncSession(engine) as db:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            if user is None:
                user = User(
                    email=email,
                    google_id=google_id,
                    encrypted_wallet_blob=None
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
            elif user.google_id != google_id:
                raise HTTPException(status_code=400, detail="Google ID mismatch")

            access_token = create_access_token({"sub": user.id, "email": user.email})

            callback_url = f"{get_base_url()}/auth/callback?token={access_token}"
            if show_token:
                callback_url += "&show_token=true"
            return RedirectResponse(url=callback_url, status_code=302)
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"[Auth] google_callback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "is_admin": getattr(current_user, 'is_admin', False),
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }


@router.get("/callback")
async def auth_callback(token: str, show_token: str = ""):
    if show_token == "true":
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>RZC Login</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d0d14; color: #fff; min-height: 100vh; display: flex; align-items: center; justify-content: center; margin: 0; padding: 20px; box-sizing: border-box; }}
                .container {{ text-align: center; max-width: 500px; width: 100%; }}
                h2 {{ color: #4caf50; margin-bottom: 1rem; }}
                p {{ color: #888; margin-bottom: 1.5rem; }}
                .token-box {{ background: #1f1f2e; border: 1px solid #333; border-radius: 8px; padding: 1rem; font-family: monospace; font-size: 0.85rem; word-break: break-all; color: #ffd700; margin-bottom: 1rem; max-height: 150px; overflow-y: auto; text-align: left; }}
                .btn {{ background: #ffd700; color: #0d0d14; border: none; padding: 0.75rem 2rem; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 1rem; }}
                .btn:hover {{ background: #ffed4a; }}
                .copied {{ color: #4caf50; margin-top: 1rem; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Login Successful!</h2>
                <p>Copy your token below and paste it in the mobile app:</p>
                <div class="token-box" id="token">{token}</div>
                <button class="btn" onclick="copyToken()">Copy Token</button>
                <p id="copied" class="copied" style="display:none;">Copied!</p>
            </div>
            <script>
                function copyToken() {{
                    navigator.clipboard.writeText(document.getElementById('token').innerText);
                    document.getElementById('copied').style.display = 'block';
                }}
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
    return RedirectResponse(url=f"{settings.frontend_url}/auth/callback?token={token}", status_code=302)


class MobileGoogleAuth(BaseModel):
    id_token: str
    email: str
    name: str
    google_id: str


@router.post("/google-mobile")
async def google_mobile_auth(request: MobileGoogleAuth):
    try:
        async with AsyncSession(engine) as db:
            result = await db.execute(select(User).where(User.email == request.email))
            user = result.scalar_one_or_none()

            if user is None:
                user = User(
                    email=request.email,
                    google_id=request.google_id,
                    encrypted_wallet_blob=None
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
            elif user.google_id != request.google_id:
                raise HTTPException(status_code=400, detail="Google ID mismatch")

            access_token = create_access_token({"sub": user.id, "email": user.email})

            return {
                "token": access_token,
                "user_id": user.id,
                "email": user.email
            }
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"[Auth] google_mobile_auth error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
