"""String helpers."""
import re


def title_case(text):
    return " ".join(w.capitalize() for w in text.split())


def slugify(text):
    """Lowercase, replace each run of non-alphanumerics with a single '-'."""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")
