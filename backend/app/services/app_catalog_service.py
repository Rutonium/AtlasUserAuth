from __future__ import annotations

KNOWN_APP_KEYS = (
    "atlas_user_auth_admin",
    "asset_management",
    "drawing_extractor",
    "people_planner",
)


DEFAULT_RIGHTS_DEFINITIONS: dict[str, dict[str, dict[str, bool]]] = {
    "asset_management": {
        "checkout": {"1": True, "2": True, "3": True, "4": True, "5": True},
        "manageRentals": {"1": False, "2": True, "3": True, "4": True, "5": True},
        "manageWarehouse": {"1": False, "2": False, "3": True, "4": True, "5": True},
        "manageEquipment": {"1": False, "2": False, "3": False, "4": True, "5": True},
        "manageUsers": {"1": False, "2": False, "3": False, "4": False, "5": True},
    },
}
