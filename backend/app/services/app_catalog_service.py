from __future__ import annotations

KNOWN_APP_KEYS = (
    "atlas_user_auth_admin",
    "asset_management",
    "drawing_extractor",
    "gangways",
    "people_planner",
    "tender_robot",
    "weldoc",
)


LOGIN_LAUNCHER_APPS = (
    {
        "app_key": "drawing_extractor",
        "label": "DrawingExtractor",
        "description": "Open drawing lookup and extraction workflows.",
        "path": "/drawing_extractor/",
    },
    {
        "app_key": "people_planner",
        "label": "PeoplePlanner",
        "description": "Plan staffing, availability, and team allocation.",
        "path": "/peopleplanner/",
    },
    {
        "app_key": "asset_management",
        "label": "AssetManagement",
        "description": "Manage equipment, rentals, and warehouse operations.",
        "path": "/asset_management/",
    },
    {
        "app_key": "weldoc",
        "label": "Weldoc",
        "description": "Review welding records and production documentation.",
        "path": "/welding_records/",
    },
    {
        "app_key": "tender_robot",
        "label": "Tender Robot",
        "description": "Work with tender automation and bid preparation.",
        "path": "/tenders/",
    },
    {
        "app_key": "gangways",
        "label": "Gangways",
        "description": "Access gangway-related planning and operations.",
        "path": "/gangways/",
    },
)


def list_login_launcher_apps() -> list[dict[str, str]]:
    return [dict(item) for item in LOGIN_LAUNCHER_APPS]


DEFAULT_RIGHTS_DEFINITIONS: dict[str, dict[str, dict[str, bool]]] = {
    "asset_management": {
        "checkout": {"1": True, "2": True, "3": True, "4": True, "5": True},
        "manageRentals": {"1": False, "2": True, "3": True, "4": True, "5": True},
        "manageWarehouse": {"1": False, "2": False, "3": True, "4": True, "5": True},
        "manageEquipment": {"1": False, "2": False, "3": False, "4": True, "5": True},
        "manageUsers": {"1": False, "2": False, "3": False, "4": False, "5": True},
    },
}
