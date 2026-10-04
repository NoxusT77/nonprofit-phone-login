from typing import Any

import pytest

from nonprofit_login.access_policy import MemberRole, PortalArea
from nonprofit_login.phone_login import CompleteLogin, NonprofitPhoneLogin


class RecordingAuth:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def send_phone_code(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append("send")
        return {"id": "delivery_123"}

    def verify_phone(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append("verify")
        return {"user_id": "member_42"}

    def create_session(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(f"session:{kwargs['user_id']}")
        return {"session_id": "session_123"}


def test_campaign_manager_gets_reporting_session_after_verified_code() -> None:
    auth = RecordingAuth()
    login = NonprofitPhoneLogin(auth)

    result = login.complete(
        CompleteLogin(
            phone="+12025550123",
            code="482901",
            role=MemberRole.CAMPAIGN_MANAGER,
            requested_area=PortalArea.CAMPAIGN_REPORTING,
            request_id="login-request-42",
        )
    )

    assert result.model_dump() == {
        "session_id": "session_123",
        "area": PortalArea.CAMPAIGN_REPORTING,
        "state": "access_granted",
    }
    assert auth.calls == ["verify", "session:member_42"]


def test_donor_is_rejected_before_phone_or_session_calls() -> None:
    auth = RecordingAuth()
    login = NonprofitPhoneLogin(auth)

    with pytest.raises(PermissionError, match="donor cannot enter campaign_reporting"):
        login.complete(
            CompleteLogin(
                phone="+12025550123",
                code="482901",
                role=MemberRole.DONOR,
                requested_area=PortalArea.CAMPAIGN_REPORTING,
                request_id="login-request-43",
            )
        )

    assert auth.calls == []

