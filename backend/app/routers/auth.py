from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.login_throttle import check_throttled, record_failure, record_success
from app.core.ratelimit import limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.deps import CurrentUser, DbDep
from app.models import User
from app.schemas import Token, UserOut, UserRegister

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, payload: UserRegister, db: DbDep):
    exists = (
        await db.execute(
            select(User).where(
                (User.username == payload.username) | (User.email == payload.email)
            )
        )
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="用户名或邮箱已被注册")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return Token(
        access_token=create_access_token(user.username, user.id),
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(request: Request, payload: LoginRequest, db: DbDep):
    # 账号维度慢速限流：同用户名窗口内多次失败后暂时拒绝（防绕过 IP 限流的爆破）
    if check_throttled(payload.username):
        raise HTTPException(status_code=429, detail="失败次数过多，请 5 分钟后再试")

    user = (
        await db.execute(select(User).where(User.username == payload.username))
    ).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        record_failure(payload.username)
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    record_success(payload.username)
    return Token(
        access_token=create_access_token(user.username, user.id),
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: CurrentUser):
    return current_user
