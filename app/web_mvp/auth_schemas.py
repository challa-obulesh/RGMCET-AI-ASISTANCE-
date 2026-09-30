"""Pydantic schemas for authentication and user management."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field
from typing import Literal


class UserRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: Literal["student", "professor"] = "student"


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    name: str


class UserProfile(BaseModel):
    user_id: str
    name: str
    email: str
    role: str
    professor_id: str | None = None
