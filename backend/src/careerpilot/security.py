import re
from pathlib import Path

FORMULA_PREFIXES = ("=", "+", "-", "@")
_SECRETS = re.compile(r"(?i)(api[_-]?key|authorization|password|token)\s*[:=]\s*([^\s,;]+)")
_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")


def safe_path(root: Path, candidate: Path) -> Path:
    root = root.resolve()
    resolved = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("path escapes authorized root")
    return resolved


def escape_excel_formula(value: str) -> str:
    return f"'{value}" if value.startswith(FORMULA_PREFIXES) else value


def redact(value: str) -> str:
    value = _EMAIL.sub("[REDACTED_EMAIL]", value)
    return _SECRETS.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)


def mark_untrusted(value: str) -> dict[str, str | bool]:
    return {"content": value, "trusted": False}
