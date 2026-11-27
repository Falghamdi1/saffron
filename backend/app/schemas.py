"""Domain models passed between the pipeline stages."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Category = Literal[
    "allergy", "diet", "like", "dislike", "cuisine", "spice", "budget", "favorite_dish"
]
Status = Literal["active", "pending", "superseded", "retracted"]
Certainty = Literal["confirmed", "inferred"]
Intent = Literal["recommend", "compare", "dish_question", "share", "greeting", "other"]
MenuCategory = Literal["starter", "main", "dessert", "drink"]


class MenuItem(BaseModel):
    id: str
    name: str
    category: MenuCategory
    cuisine: str
    price: float = Field(gt=0)
    spice_level: int = Field(ge=0, le=3)
    description: str
    ingredients: list[str]
    allergens: list[str]
    may_contain: list[str]
    diets: list[str]
    available: bool = True
    allergen_info_complete: bool = True


class Candidate(BaseModel):
    """A proposed memory change. It has no effect until the memory policy accepts it."""

    category: Category
    value: str = Field(min_length=1, max_length=60)
    operation: Literal["assert", "retract"] = "assert"
    scope: Literal["persistent", "temporary"] = "persistent"
    certainty: Literal["explicit", "uncertain"] = "explicit"
    evidence: str = Field(default="", max_length=300)


class RequestConstraints(BaseModel):
    """What the user wants right now. Lives with the conversation, not the profile."""

    category: MenuCategory | None = None
    wants: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    diets: list[str] = Field(default_factory=list)
    relaxed_diets: list[str] = Field(default_factory=list)
    max_price: float | None = Field(default=None, gt=0)
    spice: int | None = Field(default=None, ge=0, le=3)
    cheaper: bool = False

    @field_validator("max_price", mode="before")
    @classmethod
    def no_limit_when_not_positive(cls, value):
        """Models sometimes send 0 to mean "no budget"."""
        return None if isinstance(value, int | float) and value <= 0 else value


class Understanding(BaseModel):
    intent: Intent = "other"
    preferences: list[Candidate] = Field(default_factory=list)
    request: RequestConstraints = Field(default_factory=RequestConstraints)
    dish_names: list[str] = Field(default_factory=list)


class Preference(BaseModel):
    id: str
    category: Category
    value: str
    status: Status
    certainty: Certainty
    removal_requested: bool = False
    source_text: str = ""
    created_at: str = ""
    updated_at: str = ""


class MemoryNote(BaseModel):
    """A user-visible account of what the memory manager did with a statement."""

    kind: Literal["saved", "updated", "removed", "needs_confirmation", "conflict", "temporary"]
    message: str
    preference_id: str | None = None


class Recommendation(BaseModel):
    item: MenuItem
    reasons: list[str]
    cautions: list[str] = Field(default_factory=list)
    score: float = 0.0


class Exclusion(BaseModel):
    item_id: str
    name: str
    reasons: list[str]
