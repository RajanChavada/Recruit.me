from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class EmailCandidate:
    email: str
    pattern: str


def _normalize_company_domain(company: str | None) -> str | None:
    """Very small heuristic to turn a company name into a plausible email domain.

    This is intentionally conservative.
    - If company already looks like a domain, keep it.
    - Otherwise, normalize to lowercase and drop non-alnum characters.

    NOTE: This does NOT "research" the real domain. It's a best-effort fallback.
    """

    if not company:
        return None

    c = company.strip().lower()

    # Small curated mapping for common org abbreviations.
    # This avoids naive guesses like "rbc.com" vs "royalbank.com" etc.
    # Keep this list tiny and intentional for MVP; expand as needed.
    known = {
        "rbc": "rbc.com",
        "royal bank of canada": "rbc.com",
        "rbc capital markets": "rbc.com",
    }
    if c in known:
        return known[c]

    # If they already gave a domain-like string.
    if "." in c and " " not in c and re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", c):
        return c

    # Normalize company name into a naive domain.
    # e.g., "Borealis AI" -> "borealisai.com"
    base = re.sub(r"[^a-z0-9]+", "", c)
    if not base:
        return None
    return f"{base}.com"


def _split_name(full_name: str | None) -> tuple[str | None, str | None]:
    if not full_name:
        return None, None

    tokens = [t for t in re.split(r"\s+", full_name.strip()) if t]
    if len(tokens) == 0:
        return None, None

    # Strip punctuation.
    tokens = [re.sub(r"[^A-Za-z'-]", "", t) for t in tokens]
    tokens = [t for t in tokens if t]

    if len(tokens) == 0:
        return None, None

    first = tokens[0].lower()
    last = tokens[-1].lower() if len(tokens) > 1 else None
    return first, last


def generate_email_candidates(*, name: str | None, company: str | None) -> list[EmailCandidate]:
    """Generate plausible corporate email candidates.

    Contract:
    - Inputs: person name + company name (or domain)
    - Output: ordered list of candidates (most common patterns first)

    This is used as a deterministic fallback to "flood" the model with options.
    The LLM can then pick the best candidate (and explain why) WITHOUT needing
    actual web browsing.
    """

    first, last = _split_name(name)
    domain = _normalize_company_domain(company)

    if not first or not domain:
        return []

    # If no last name, only patterns that make sense.
    if not last:
        return [EmailCandidate(email=f"{first}@{domain}", pattern="first@domain")]

    f = first[0]
    l = last[0]

    candidates: list[EmailCandidate] = [
        EmailCandidate(email=f"{first}.{last}@{domain}", pattern="first.last@domain"),
        EmailCandidate(email=f"{first}{last}@{domain}", pattern="firstlast@domain"),
        EmailCandidate(email=f"{f}{last}@{domain}", pattern="flast@domain"),
        EmailCandidate(email=f"{first}{l}@{domain}", pattern="firstl@domain"),
        EmailCandidate(email=f"{first}_{last}@{domain}", pattern="first_last@domain"),
        EmailCandidate(email=f"{last}.{first}@{domain}", pattern="last.first@domain"),
    ]

    # Dedup while preserving order
    seen: set[str] = set()
    out: list[EmailCandidate] = []
    for c in candidates:
        if c.email not in seen:
            out.append(c)
            seen.add(c.email)

    return out
