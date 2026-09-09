from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from lib.auth import (
    COOKIE_NAME,
    TTL_DAYS,
    User,
    UserPublic,
    check_senha,
    current_user,
    make_token,
)
from lib.db import db

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    senha: str


def _public(user: User) -> UserPublic:
    return UserPublic(id=user.id, email=user.email, nome=user.nome,
                      role=user.role, store_id=user.store_id)


@router.post("/login", response_model=UserPublic)
async def login(payload: LoginRequest, response: Response):
    doc = await db.users.find_one({"email": payload.email.strip().lower()})
    if not doc:
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")
    doc.pop("_id", None)
    user = User(**doc)
    if not check_senha(payload.senha, user.senha_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")
    response.set_cookie(
        COOKIE_NAME, make_token(user), httponly=True, samesite="lax",
        max_age=TTL_DAYS * 86400, path="/",
    )
    return _public(user)


@router.post("/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return None


@router.get("/me", response_model=UserPublic)
async def me(user: User = Depends(current_user)):
    return _public(user)
