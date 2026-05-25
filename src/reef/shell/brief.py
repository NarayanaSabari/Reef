from reef.memory.store import Memory


def build_brief_prompt(memories: list[Memory]) -> str:
    """Prompt for the morning brief; terse when the user prefers brief mornings."""
    terse = any(m.key == "mornings" and "brief" in m.value.lower() for m in memories)
    style = "Be very brief - a few words per item." if terse else "A short paragraph is fine."
    return (
        "Give the user their morning brief: today's calendar, any PRs waiting on them, "
        f"and anything urgent in email. {style}"
    )
