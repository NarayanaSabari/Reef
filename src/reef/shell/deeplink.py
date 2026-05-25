from dataclasses import dataclass


@dataclass(frozen=True)
class DeepLink:
    action: str
    context: dict


def encode_deeplink(action: str, **context) -> dict:
    """Build a macOS-notification userInfo payload that routes back into Reef."""
    return {"reef_action": action, "reef_context": context}


def decode_deeplink(userinfo: dict) -> DeepLink | None:
    """Parse a notification userInfo payload; None if it isn't a Reef deep-link."""
    action = userinfo.get("reef_action")
    if not action:
        return None
    return DeepLink(action=action, context=userinfo.get("reef_context", {}))
