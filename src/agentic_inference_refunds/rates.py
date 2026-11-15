"""Rate cards and pricing.

A rate card is JSON: ``{"id", "provider", "as_of", "verified", "sources", "models":
{model: {"aliases", "input", "output", "cache_read", "cache_write_5m",
"cache_write_1h"}}, "units": {unit: {"usd"}}}``. Prices are USD per million tokens.
Bundled cards load first; cards passed with ``--rates`` override models with the
same normalized name. A record whose model is in no card is reported as unpriced,
never guessed.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .records import UsageRecord

BUNDLED_DIR = Path(__file__).parent / "data" / "rates"
PRICE_FIELDS = ("input", "output", "cache_read", "cache_write_5m", "cache_write_1h")


def normalize_model(name: str) -> str:
    n = (name or "").strip().lower()
    n = re.sub(r"^(anthropic|openai|azure-openai|github-copilot|copilot)[/:]", "", n)
    n = re.sub(r"[._\s]+", "-", n)
    return n


@dataclass
class RateBook:
    cards: list = field(default_factory=list)
    _index: dict = field(default_factory=dict)
    units: dict = field(default_factory=dict)

    @classmethod
    def load(cls, extra=(), bundled: bool = True) -> "RateBook":
        book = cls()
        paths = sorted(BUNDLED_DIR.glob("*.json")) if bundled else []
        paths += [Path(p).expanduser() for p in extra]
        for p in paths:
            book.add(json.loads(Path(p).read_text()), str(p))
        return book

    def add(self, card: dict, origin: str = "") -> None:
        card = dict(card)
        card.setdefault("id", Path(origin).stem or "card")
        p = Path(origin) if origin else None
        # Record where a card came from without leaking local paths into shared claims.
        card["origin"] = ("bundled/" + p.name) if p and p.parent.resolve() == BUNDLED_DIR.resolve() else (p.name if p else "")
        self.cards.append(card)
        for model, rates in (card.get("models") or {}).items():
            missing = [f for f in PRICE_FIELDS if f not in rates]
            if missing:
                raise ValueError(f"rate card {card['id']}: model {model} is missing {missing}")
            entry = {"card": card["id"], "model": model, "verified": bool(card.get("verified")), "as_of": card.get("as_of"), **rates}
            for key in [model, *rates.get("aliases", [])]:
                self._index[normalize_model(key)] = entry
        for unit, spec in (card.get("units") or {}).items():
            self.units[unit] = {"card": card["id"], "verified": bool(card.get("verified")), **spec}

    def lookup(self, model: str):
        return self._index.get(normalize_model(model))

    def price(self, r: UsageRecord) -> dict:
        rate = self.lookup(r.model)
        if rate is None:
            return {"priced": False, "rate_key": None, "input": 0.0, "cache_read": 0.0, "cache_write": 0.0, "output": 0.0, "total": 0.0}
        m = 1_000_000
        parts = {
            "input": r.input_tokens * rate["input"] / m,
            "cache_read": r.cache_read_tokens * rate["cache_read"] / m,
            # Unknown-TTL writes are priced at the 5-minute rate: the lower bound.
            "cache_write": (r.cache_write_5m_tokens + r.cache_write_tokens) * rate["cache_write_5m"] / m
            + r.cache_write_1h_tokens * rate["cache_write_1h"] / m,
            "output": r.output_tokens * rate["output"] / m,
        }
        parts["total"] = sum(parts.values())
        return {"priced": True, "rate_key": rate["model"], "card": rate["card"], "verified": rate["verified"], **parts}

    def unit_price(self, unit: str):
        return self.units.get(unit)

    def summary(self) -> list:
        out = []
        for c in self.cards:
            out.append(
                {
                    "id": c["id"],
                    "provider": c.get("provider"),
                    "as_of": c.get("as_of"),
                    "verified": bool(c.get("verified")),
                    "origin": c.get("origin"),
                    "sources": c.get("sources", []),
                    "models": {k: {f: v[f] for f in PRICE_FIELDS} for k, v in (c.get("models") or {}).items()},
                    "units": c.get("units", {}),
                }
            )
        return out
