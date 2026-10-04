from enum import Enum


class MemberRole(str, Enum):
    DONOR = "donor"
    VOLUNTEER = "volunteer"
    CAMPAIGN_MANAGER = "campaign_manager"


class PortalArea(str, Enum):
    DONOR_RECEIPTS = "donor_receipts"
    VOLUNTEER_REMINDERS = "volunteer_reminders"
    CAMPAIGN_REPORTING = "campaign_reporting"


ROLE_AREAS: dict[MemberRole, frozenset[PortalArea]] = {
    MemberRole.DONOR: frozenset({PortalArea.DONOR_RECEIPTS}),
    MemberRole.VOLUNTEER: frozenset({PortalArea.VOLUNTEER_REMINDERS}),
    MemberRole.CAMPAIGN_MANAGER: frozenset(
        {
            PortalArea.DONOR_RECEIPTS,
            PortalArea.VOLUNTEER_REMINDERS,
            PortalArea.CAMPAIGN_REPORTING,
        }
    ),
}


def allowed_area(role: MemberRole, requested_area: PortalArea) -> PortalArea:
    if requested_area not in ROLE_AREAS[role]:
        raise PermissionError(f"{role.value} cannot enter {requested_area.value}")
    return requested_area

