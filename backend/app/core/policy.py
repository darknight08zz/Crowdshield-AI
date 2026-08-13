from typing import Dict, Any

DEFAULT_NOTIFICATION_POLICY: Dict[str, Any] = {
    "LOW": {
        "risk_range": "0 - 24",
        "inform_citizen": False,
        "notify_operator": False,
        "require_operator_approval": False,
        "description": "Normal telemetry monitoring; no proactive alerts."
    },
    "MODERATE": {
        "risk_range": "25 - 49",
        "inform_citizen": False,
        "notify_operator": True,
        "require_operator_approval": True,
        "description": "Notify operator dashboard; require manual approval before dispatching alerts."
    },
    "MEDIUM": {
        "risk_range": "25 - 49",
        "inform_citizen": False,
        "notify_operator": True,
        "require_operator_approval": True,
        "description": "Alias for MODERATE risk level."
    },
    "HIGH": {
        "risk_range": "50 - 74",
        "inform_citizen": True,
        "notify_operator": True,
        "require_operator_approval": True,
        "description": "Publish citizen safety rerouting advisory; dispatch officer squad upon operator approval."
    },
    "CRITICAL": {
        "risk_range": "75 - 100",
        "inform_citizen": True,
        "notify_operator": True,
        "require_operator_approval": False,
        "description": "Auto-dispatch emergency gate opening and push high-priority alerts to ground squads & citizens."
    }
}

active_policy: Dict[str, Any] = dict(DEFAULT_NOTIFICATION_POLICY)


def get_current_notification_policy() -> Dict[str, Any]:
    return active_policy


def update_notification_policy(new_policy: Dict[str, Any]) -> Dict[str, Any]:
    global active_policy
    active_policy.update(new_policy)
    return active_policy
