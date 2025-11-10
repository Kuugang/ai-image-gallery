from gotrue import User, UserAttributes  # type: ignore
from pydantic import BaseModel, EmailStr, Field


# Shared properties
class Token(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"


# request
class UserIn(Token, User):  # type: ignore
    pass


# Properties to receive via API on creation
# in
class UserCreate(BaseModel):
    pass


# Properties to receive via API on update
# in
class UserUpdate(UserAttributes):  # type: ignore
    pass


# response


class UserInDBBase(BaseModel):
    pass


# Properties to return to client via api
# out
class UserOut(Token):
    user_id: str | None = None
    email: str | None = None


# Properties properties stored in DB
class UserInDB(User):  # type: ignore
    pass


# Auth Request Schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class UpdatePasswordRequest(BaseModel):
    access_token: str
    new_password: str = Field(..., min_length=6)
