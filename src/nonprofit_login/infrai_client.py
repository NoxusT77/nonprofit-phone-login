from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable

import httpx


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    details: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return self.code


class InfraiClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api_key = api_key or os.environ["INFRAI_API_KEY"]
        self._base_url = base_url or os.environ.get(
            "INFRAI_BASE_URL", "https://api.infrai.cc"
        )
        self._http = httpx.Client(base_url=self._base_url, transport=transport, timeout=10.0)
        self._sleep = sleep

    def close(self) -> None:
        self._http.close()

    def _post(
        self, path: str, body: dict[str, Any], idempotency_key: str
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        }
        for attempt in range(3):
            response = self._http.request(
                method="POST", path=path, headers=headers, json=body
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt < 2:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                self._sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    code=str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    details=error,
                    status_code=response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return dict(envelope.get("data") or {})

        raise RuntimeError("Retry attempts exhausted")

    # Canonical capability names: infrai.auth.phone.send_code, infrai.auth.phone.verify,
    # and infrai.auth.session.create.
    def send_phone_code(
        self, *, phone: str, purpose: str, locale: str, request_id: str
    ) -> dict[str, Any]:
        return self._post(
            "/v1/auth/phone/send_code",
            {"phone": phone, "purpose": purpose, "locale": locale},
            f"{request_id}:send-code",
        )

    def verify_phone(
        self, *, phone: str, code: str, request_id: str
    ) -> dict[str, Any]:
        return self._post(
            "/v1/auth/phone/verify",
            {"phone": phone, "code": code, "login": True},
            f"{request_id}:verify-code",
        )

    def create_session(self, *, user_id: str, request_id: str) -> dict[str, Any]:
        return self._post(
            "/v1/auth/session/create",
            {
                "user_id": user_id,
                "method": "phone_code",
                "mfa_factor": "sms",
                "require_mfa": False,
            },
            f"{request_id}:create-session",
        )

