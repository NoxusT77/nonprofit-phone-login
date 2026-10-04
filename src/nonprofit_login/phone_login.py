from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .access_policy import MemberRole, PortalArea, allowed_area


class StartLogin(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    locale: str = Field(default="en", min_length=2, max_length=10)
    request_id: str = Field(min_length=8, max_length=100)


class CodeSent(BaseModel):
    state: str = "code_sent"


class CompleteLogin(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    code: str = Field(min_length=4, max_length=10)
    role: MemberRole
    requested_area: PortalArea
    request_id: str = Field(min_length=8, max_length=100)


class LoginGranted(BaseModel):
    session_id: str
    area: PortalArea
    state: str = "access_granted"


class NonprofitPhoneLogin:
    def __init__(self, auth: Any) -> None:
        self._auth = auth

    def close(self) -> None:
        close = getattr(self._auth, "close", None)
        if close is not None:
            close()

    def start(self, command: StartLogin) -> CodeSent:
        self._auth.send_phone_code(
            phone=command.phone,
            purpose="nonprofit_login",
            locale=command.locale,
            request_id=command.request_id,
        )
        return CodeSent()

    def complete(self, command: CompleteLogin) -> LoginGranted:
        area = allowed_area(command.role, command.requested_area)
        verification = self._auth.verify_phone(
            phone=command.phone,
            code=command.code,
            request_id=command.request_id,
        )
        session = self._auth.create_session(
            user_id=str(verification["user_id"]), request_id=command.request_id
        )
        return LoginGranted(session_id=str(session["session_id"]), area=area)
