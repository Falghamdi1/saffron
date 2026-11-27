"""Canonical food vocabulary shared by understanding, memory and recommendation.

Preferences are stored using these canonical values so that "nuts", "a nut" and
"tree nuts" all refer to the same thing when memory is compared or filtered.
"""

ALLERGENS = (
    "milk", "egg", "fish", "crustacean", "mollusc", "peanut", "tree_nut",
    "gluten", "soy", "sesame", "mustard", "celery", "sulphites",
)

# A phrase may expand to several allergens. Where a phrase is ambiguous
# ("nuts", "shellfish") it expands to every allergen it could mean.
ALLERGEN_SYNONYMS: dict[str, tuple[str, ...]] = {
    "milk": ("milk",), "dairy": ("milk",), "lactose": ("milk",), "cheese": ("milk",),
    "egg": ("egg",),
    "fish": ("fish",),
    "shellfish": ("crustacean", "mollusc"), "seafood": ("fish", "crustacean", "mollusc"),
    "crustacean": ("crustacean",), "prawn": ("crustacean",), "shrimp": ("crustacean",),
    "crab": ("crustacean",), "lobster": ("crustacean",),
    "mollusc": ("mollusc",), "mollusk": ("mollusc",),
    "peanut": ("peanut",), "groundnut": ("peanut",),
    "nut": ("peanut", "tree_nut"),
    "tree nut": ("tree_nut",), "almond": ("tree_nut",), "cashew": ("tree_nut",),
    "walnut": ("tree_nut",), "pistachio": ("tree_nut",), "pine nut": ("tree_nut",),
    "hazelnut": ("tree_nut",),
    "gluten": ("gluten",), "wheat": ("gluten",),
    "soy": ("soy",), "soya": ("soy",),
    "sesame": ("sesame",), "tahini": ("sesame",),
    "mustard": ("mustard",),
    "celery": ("celery",),
    "sulphite": ("sulphites",), "sulfite": ("sulphites",),
}

ALLERGEN_LABELS = {
    "milk": "dairy", "egg": "egg", "fish": "fish", "crustacean": "crustaceans",
    "mollusc": "molluscs", "peanut": "peanuts", "tree_nut": "tree nuts",
    "gluten": "gluten", "soy": "soy", "sesame": "sesame", "mustard": "mustard",
    "celery": "celery", "sulphites": "sulphites",
}

# The first three are mutually exclusive eating patterns; the rest stack.
EATING_PATTERNS = ("vegetarian", "vegan", "pescatarian")
DIETS = (*EATING_PATTERNS, "gluten_free", "dairy_free")

SPICE_LEVELS = ("none", "mild", "medium", "hot")
CATEGORIES = ("starter", "main", "dessert", "drink")
CUISINES = ("levantine", "gulf", "indian", "mediterranean")

# Food words that stand for a group of ingredients on the menu.
INGREDIENT_GROUPS: dict[str, tuple[str, ...]] = {
    "meat": ("lamb", "chicken", "beef"),
    "seafood": ("prawns", "sea bass", "fish"),
    "fish": ("sea bass",),
    "cheese": ("cheese", "halloumi", "paneer", "parmesan"),
    "nut": ("almonds", "cashew", "walnut", "pistachio", "pine nuts"),
    "curry": ("curry", "vindaloo", "tikka", "butter chicken"),
    "rice": ("basmati rice", "arborio rice"),
    "pepper": ("red pepper", "bell pepper"),
    "chickpea": ("chickpeas", "falafel", "hummus"),
}


# Words naming a whole allergen class. Disliking "dairy" covers every dairy dish,
# while disliking "cheese" covers only dishes that contain cheese.
ALLERGEN_CLASSES = ("dairy", "nut", "tree nut", "shellfish", "seafood", "gluten", "egg", "soy")


def singular(word: str) -> str:
    """Reduce a food term to a comparable singular form."""
    word = " ".join(word.lower().split())
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("oes"):
        return word[:-2]
    if word.endswith("s") and not word.endswith(("ss", "us")):
        return word[:-1]
    return word


def allergens_for(term: str) -> tuple[str, ...]:
    """Return the canonical allergens a phrase refers to, or () if none."""
    term = singular(term.replace("_", " ")).removesuffix(" allergy")
    if term in ALLERGEN_SYNONYMS:
        return ALLERGEN_SYNONYMS[term]
    # "sesame seeds" or "peanut butter" must still resolve to the tracked allergen.
    found: list[str] = []
    for word in term.split():
        found += ALLERGEN_SYNONYMS.get(singular(word), ())
    return tuple(dict.fromkeys(found))


def label(value: str) -> str:
    """Human readable form of a canonical value."""
    return ALLERGEN_LABELS.get(value, value.replace("_", "-"))
