"""Context for AI workers (docs/contracts/MEMORY.md "Context for workers"): up to 5 relevant notes are added to an
AI step's task under "Relevant notes:". Meaning search when its index works, keyword search otherwise.
A step can opt out with the setting use_memory = "no"."""
import re
import vault

MAX_NOTES, SNIPPET = 5, 400
SKIP_PREFIXES = ("environments/", "claims/")  # flow files and claims are not background knowledge


def _strip_front_matter(text: str) -> str:
    return re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)


def find(task: str, k: int = MAX_NOTES) -> list[str]:
    paths = []
    try:
        import memory_index
        paths = [p for p, _ in memory_index.search(task, k=k * 2)]
    except Exception:
        words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9]{3,}", task)][:12]
        paths = vault.search(" ".join(words), k=k * 2) if words else []
    return [p for p in paths if not p.startswith(SKIP_PREFIXES)][:k]


def block(task: str, cfg: dict) -> str:
    if str(cfg.get("use_memory", "yes")).strip().lower() in ("no", "false", "0", "off"):
        return ""
    lines = []
    for p in find(task):
        try:
            body = _strip_front_matter(vault.read_note(p)).strip().replace("\n", " ")
        except Exception:
            continue
        lines.append(f"- {p}: {body[:SNIPPET]}")
    return ("\n\nRelevant notes:\n" + "\n".join(lines)) if lines else ""
