"""Test diners and an independent constraint checker.

`violations_by_oracle` deliberately re-implements the hard constraints from the raw
menu records, so the recommender is not graded by its own filtering code.
"""

import uuid
from dataclasses import dataclass, field

from fastapi.testclient import TestClient

from app.setup_db import load_menu_file

MENU = {item.id: item for item in load_menu_file()}


class Diner:
    """A signed-in user talking to the application over HTTP."""

    def __init__(self, client: TestClient, name: str | None = None) -> None:
        self.client = client
        self.name = name or f"diner-{uuid.uuid4().hex[:10]}"
        response = client.post("/api/local-auth/session", json={"name": self.name})
        response.raise_for_status()
        self.headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
        self.conversation_id = None

    def say(self, message: str) -> dict:
        response = self.client.post(
            "/api/chat",
            json={"message": message, "conversation_id": self.conversation_id},
            headers=self.headers,
        )
        response.raise_for_status()
        body = response.json()
        self.conversation_id = body["conversation_id"]
        return body["message"]

    def new_conversation(self) -> None:
        self.conversation_id = None

    def get(self, path: str):
        return self.client.get(path, headers=self.headers)

    def post(self, path: str):
        return self.client.post(path, headers=self.headers)

    def memory(self) -> dict:
        return self.get("/api/memory").json()

    def preferences(self, status: str = "active") -> set[tuple[str, str]]:
        return {
            (p["category"], p["value"])
            for p in self.memory()["preferences"] if p["status"] == status
        }

    def preference_id(self, category: str, value: str) -> str:
        return next(
            p["id"] for p in self.memory()["preferences"]
            if (p["category"], p["value"]) == (category, value)
        )


def picks(message: dict) -> list[str]:
    return [r["item"]["id"] for r in message["payload"]["recommendations"]]


@dataclass(frozen=True)
class Limits:
    """Ground truth a recommendation must respect, stated by the scenario author."""

    allergens: tuple[str, ...] = ()
    diets: tuple[str, ...] = ()
    avoid_ingredients: tuple[str, ...] = ()
    max_price: float | None = None


def violations_by_oracle(item_id: str, limits: Limits) -> list[str]:
    item = MENU.get(item_id)
    if item is None:
        return ["not a menu item"]
    found = []
    if not item.available:
        found.append("unavailable")
    found += [a for a in limits.allergens if a in item.allergens or a in item.may_contain]
    if limits.allergens and not item.allergen_info_complete:
        found.append("unverified allergens")
    found += [d for d in limits.diets if d not in item.diets]
    found += [
        food for food in limits.avoid_ingredients
        if any(food in ingredient for ingredient in item.ingredients)
    ]
    if limits.max_price is not None and item.price > limits.max_price:
        found.append("over budget")
    return found


@dataclass
class Tally:
    """Counts gathered while scenarios run."""

    recommendations: int = 0
    violations: list[str] = field(default_factory=list)

    def check(self, message: dict, limits: Limits) -> None:
        """Record every recommendation and fail on any hard-constraint breach."""
        for item_id in picks(message):
            self.recommendations += 1
            broken = violations_by_oracle(item_id, limits)
            if broken:
                self.violations.append(f"{item_id}: {', '.join(broken)}")
                raise AssertionError(f"{item_id} breaks {broken}")
