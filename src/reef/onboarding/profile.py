from reef.memory.store import MemoryStore

async def save_profile(store: MemoryStore, *, name: str, aliases: list[str],
                       github_owner: str, github_repo: str) -> None:
    """Persist the onboarding profile as memory rows so the InstructionProvider injects it."""
    await store.write("profile", "name", name)
    await store.write("profile", "aliases", ", ".join(aliases))
    await store.write("profile", "github_owner", github_owner)
    await store.write("profile", "github_repo", github_repo)
