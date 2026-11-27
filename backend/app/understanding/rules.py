"""Deterministic, pattern-based understanding of English ordering messages.

Used on its own when no language model is configured or the model call fails, and
always used alongside the model as a safety net for allergy statements.
"""

import re

from app.schemas import Candidate, RequestConstraints, Understanding
from app.vocabulary import ALLERGEN_SYNONYMS, CUISINES, INGREDIENT_GROUPS, singular

FOODS = {
    "chicken", "lamb", "beef", "meat", "fish", "sea bass", "prawn", "shrimp", "seafood",
    "mushroom", "halloumi", "paneer", "cheese", "parmesan", "chickpea", "lentil", "falafel",
    "hummus", "rice", "potato", "tomato", "onion", "garlic", "lemon", "lime", "mint",
    "mango", "date", "honey", "saffron", "coconut", "spinach", "courgette", "zucchini",
    "pepper", "chilli", "olive", "caper", "cucumber", "carrot", "celery", "yoghurt",
    "cream", "butter", "egg", "pistachio", "almond", "cashew", "walnut", "peanut", "nut",
    "pine nut", "sesame", "tahini", "raisin", "coriander", "cilantro", "cumin", "curry",
    "kunafa", "risotto", "shawarma", "kabsa", "soup", "pasta", "bread", "chocolate",
    "okra", "eggplant", "aubergine", "broccoli", "cauliflower", "avocado", "pork", "bean",
}
# Words that precede "allergy" without naming one.
NOT_ALLERGY_NAMES = {
    "a", "an", "my", "the", "food", "any", "have", "no", "his", "her", "their", "serious", "bad",
}
NOT_FOODS = {"nothing", "anything", "none", "something", "everything"}
SOMEONE_ELSE = re.compile(
    r"\b(?:my|our) (?:\w+ )?(?:friend|wife|husband|partner|son|daughter|kid|child|children|"
    r"baby|brother|sister|mum|mom|dad|mother|father|parent|grandma|grandpa|grandmother|"
    r"grandfather|nephew|niece|boyfriend|girlfriend|flatmate|roommate|colleague|boss|"
    r"neighbou?r|guest|youngest|eldest)s?\b"
    r"|\b(?:someone|somebody|anyone|people|a (?:friend|guest|person)) (?:who|with|that)\b"
    r"|\bone of (?:our|my|the) (?:guests|friends|colleagues|kids)\b"
    r"|\bfor (?:someone|somebody|a guest|a friend)\b"
    r"|\b(?:he|she)(?: is|'s| has| can't| cannot)\b"
    r"|\bthey(?: are|'re| have| can't| cannot)\b(?=.*\ballerg)"
)
# The customer speaking about themselves in the same clause outweighs a mention of others.
SELF = re.compile(
    r"\bi(?:'m| am)?(?: also| really| both| do)? (?:allergic|love|like|enjoy|adore|prefer|"
    r"hate|dislike|can't|cannot|don't|vegetarian|vegan|pescatarian)\b"
    r"|\bi (?:also )?have (?:a |an )?(?:[a-z]+ ){1,2}allerg"
    r"|\b(?:so am i|me too|me and|and me|and i|myself and|and myself)\b"
)
SPICY_WORDS = ("spicy", "spice", "spiciness", "heat", "hot food", "hot dishes")

TEMPORARY = re.compile(
    r"\b(today|tonight|right now|this time|for now|this order|this meal|at the moment|"
    r"just for|currently craving|this evening|this afternoon)\b"
)
HEDGE = re.compile(
    r"\b(i think|i might|maybe|possibly|probably|not sure|not certain|i guess|might be|"
    r"may be|i suspect|sometimes|mostly|trying to|try to|kind of|sort of|i wonder)\b"
)
# Softened wording ("not much", "rarely") that should not become a firm rule.
SOFTENED = re.compile(
    r"(?:\bnot|n't) (?:\w+ ){0,2}(?:much|often|really)\b|\brarely\b|\bnot a lot of\b"
)
CLAUSE_BREAK = re.compile(
    r"[.!?;\n]+|,?\s+\b(?:but|although|though|however)\b\s+|,\s*(?=i\b|i'm\b|my\b)|"
    # "me and my son" stays together, so the customer is not lost from the statement.
    r"(?<!\bme)(?<!\bmyself)\s+and\s+(?=i\b|i'm\b|i've\b|my\b)|"
    r",\s*(?=(?:recommend|suggest|what|can|show|give)\b)"
)
DIET_NAME = r"(vegetarian|vegan|pescatarian|gluten[- ]free|dairy[- ]free)"
FIRST_PERSON = (
    r"\b(?:i am|i'm|im|i've been|i have been|i've gone|i went|i became|"
    r"i might be|i may be|we are|we're)\b"
)


def clauses(message: str) -> list[str]:
    text = message.lower().replace("’", "'")
    return [c.strip(" ,") for c in CLAUSE_BREAK.split(text) if c and c.strip(" ,")]


def about_someone_else(clause: str) -> bool:
    """Whether a clause describes another person rather than the customer."""
    return bool(SOMEONE_ELSE.search(clause)) and not SELF.search(clause)


def clause_is_about_someone_else(message: str, quote: str) -> bool:
    """Judge a quoted fragment by the whole clause it came from."""
    quote = " ".join(quote.lower().replace("’", "'").split()).strip(" .,!?;")
    holding = [
        c for c in clauses(message)
        if quote in " ".join(c.split()) or " ".join(c.split()) in quote
    ]
    return all(about_someone_else(c) for c in holding or [quote])


def _items(fragment: str) -> list[str]:
    """Split "peanuts, sesame and shellfish" into separate terms."""
    fragment = re.split(
        r"\b(?:so|because|since|please|which|when|if|what|can|could|do|recommend)\b", fragment
    )[0]
    items = []
    for part in re.split(r",|\band\b|\bor\b|&|/", fragment):
        part = re.sub(
            r"\b(a|an|the|any|all|also|too|anymore|any more|now|really|very|actually|"
            r"food|foods|dishes|stuff|products|today|tonight|either|much|though|kind of)\b",
            " ", part,
        )
        term = " ".join(part.split()).strip(" -'")
        if term and len(term.split()) <= 3 and term not in NOT_FOODS:
            items.append(singular(term))
    return items


def _foods_in(text: str) -> list[str]:
    """Known food words mentioned in a clause, longest phrases first."""
    words = " " + " ".join(singular(w) for w in re.findall(r"[a-z']+", text)) + " "
    found = []
    for food in sorted(FOODS | set(ALLERGEN_SYNONYMS) | set(INGREDIENT_GROUPS),
                       key=lambda f: (-len(f), f)):
        if f" {food} " in words:
            found.append(food)
            words = words.replace(f" {food} ", " | ")
    return found


class _Extraction:
    def __init__(self) -> None:
        self.preferences: list[Candidate] = []
        self.request = RequestConstraints()
        self.dish_names: list[str] = []

    def add(self, category: str, value: str, clause: str, *, retract: bool = False) -> None:
        self.preferences.append(Candidate(
            category=category,
            value=value[:60],
            operation="retract" if retract else "assert",
            scope="temporary" if TEMPORARY.search(clause) else "persistent",
            certainty="uncertain" if HEDGE.search(clause) else "explicit",
            evidence=clause[:300],
        ))


def _is_food(term: str) -> bool:
    return term in FOODS or term in INGREDIENT_GROUPS or term in ALLERGEN_SYNONYMS


def _others_allergies(clause: str, out: _Extraction) -> bool:
    """Another diner's allergy shapes this chat but is not this customer's memory."""
    stated = re.search(
        r"\ballerg(?:ic|y) to (.+)|\bintolerant to (.+)|(?:can't|cannot) (?:eat|have|take) (.+)",
        clause,
    )
    if stated:
        terms = _items(next(g for g in stated.groups() if g))
    else:
        named = re.search(r"\b((?:tree |pine )?[a-z]+) allerg(?:y|ies)\b", clause)
        terms = [singular(named.group(1))] if named else []
        terms = [t for t in terms if t not in NOT_ALLERGY_NAMES]
        if not terms and "allerg" in clause:
            terms = _foods_in(clause)
    terms = [t for t in terms if t in ALLERGEN_SYNONYMS or "allerg" in clause]
    if re.search(r"\bnot allergic\b|n't allergic\b", clause):
        return True
    out.request.allergies.extend(t for t in terms if t not in NOT_ALLERGY_NAMES)
    return bool(terms)


def _allergies(clause: str, out: _Extraction) -> bool:
    if about_someone_else(clause):
        return _others_allergies(clause, out)
    removal = re.search(
        r"(?:not|no longer|n't|never was)\s+(?:actually\s+|really\s+)?allergic to (.+)"
        r"|outgr(?:own|ew) (?:my )?(.+?) allergy"
        r"|(?:remove|delete|forget|drop) (?:my |the )?(.+?) allergy"
        r"|(?:don't|do not) have (?:a |an |any )?(.+?) allergy"
        r"|\bno (?:more )?((?:tree |pine )?[a-z]+) allergy",
        clause,
    )
    if removal:
        for term in _items(next(g for g in removal.groups() if g)):
            out.add("allergy", term, clause, retract=True)
        return True

    stated = re.search(r"\ballerg(?:ic|y) to (.+)", clause)
    terms = _items(stated.group(1)) if stated else []
    if not terms:
        named = re.search(r"\b((?:tree |pine )?[a-z]+) allerg(?:y|ies)\b", clause)
        if named and named.group(1) not in NOT_ALLERGY_NAMES:
            terms = [singular(named.group(1))]
    for term in terms:
        out.add("allergy", term, clause)
    if terms:
        return True

    if re.search(r"\blactose[- ]intolerant\b", clause):
        out.add("diet", "dairy_free", clause)
        return True
    cannot = re.search(r"\bi (?:can't|cannot|can not|shouldn't) (?:eat|have|take) (.+)", clause)
    intolerant = re.search(r"\bintolerant to (.+)", clause)
    match = cannot or intolerant
    if match and not TEMPORARY.search(clause):
        allergens = [t for t in _items(match.group(1)) if t in ALLERGEN_SYNONYMS]
        for term in allergens:
            out.add("allergy", term, clause)
            if cannot:
                out.preferences[-1].certainty = "uncertain"
        return bool(allergens)
    return False


def _diets(clause: str, out: _Extraction) -> bool:
    gone = re.search(
        rf"(?:no longer|not|n't|stopped being|quit being|gave up being)\s+(?:a\s+)?{DIET_NAME}",
        clause,
    )
    if gone:
        out.add("diet", gone.group(1), clause, retract=True)
        return True
    eats_meat = re.search(
        r"\bi (?:eat|can eat|started eating|am eating) (?:meat|chicken)\b"
        r"(?=.*\b(?:again|now|these days)\b)|\bi (?:started|am back to) eating meat\b",
        clause,
    )
    if eats_meat:
        out.add("diet", "vegetarian", clause, retract=True)
        out.add("diet", "vegan", clause, retract=True)
        return True
    stated = re.search(
        rf"{FIRST_PERSON}(?:\s+\w+){{0,2}}?\s+(?:a\s+)?{DIET_NAME}"
        rf"|\bi (?:follow|keep|am on|only eat) (?:a )?{DIET_NAME}"
        rf"|^(?:also\s+|and\s+)?{DIET_NAME}(?: diet)?(?: now)?$",
        clause,
    )
    if stated:
        out.add("diet", next(g for g in stated.groups() if g), clause)
        return True
    if re.search(r"\bi (?:don't|do not|no longer) eat meat (?:or|and) fish\b", clause):
        out.add("diet", "vegetarian", clause)
        return True
    if re.search(
        r"\bi (?:don't|do not|rarely|avoid) (?:really )?(?:eat )?(?:much )?(?:eating )?meat\b"
        r"|\bcutting (?:down on|back on|out) meat\b", clause,
    ):
        out.add("diet", "vegetarian", clause)
        out.preferences[-1].certainty = "uncertain"
        return True
    return False


def _spice_level(clause: str) -> int | None:
    spicy = r"(?:spicy|spice|spiciness|chilli|heat)"
    # A limit on heat ("nothing too spicy") must not be read as a wish for it.
    limited = (
        r"(?:\bnot|\bnothing|n't|\bcannot|\bno|\bhate|\bdislike)\s+(?:\w+\s+){0,2}?"
        r"(?:too|very|really|overly|super|extremely)\s+(?:spicy|hot)\b"
        rf"|\btoo (?:spicy|hot) for me\b|\bsensitive to {spicy}\b"
    )
    if re.search(limited, clause):
        return 1
    if re.search(rf"\b(?:no {spicy}|not spicy at all|non[- ]spicy|zero {spicy})\b"
                 rf"|(?:can't|cannot|hate|don't like|dislike|can not) (?:\w+ ){{0,2}}{spicy}",
                 clause):
        return 0
    if re.search(rf"\b(?:mild|not too {spicy}|not very {spicy}|less {spicy}|a little {spicy}|"
                 rf"slightly {spicy}|not so {spicy}|not spicy)\b", clause):
        return 1
    if re.search(r"\bmedium(?: spic\w+| heat)\b|\bmoderately spicy\b|\bmedium[- ]spiced\b", clause):
        return 2
    if any(word in clause for word in SPICY_WORDS) or "fiery" in clause:
        return 3
    return None


def _spice(clause: str, out: _Extraction) -> bool:
    level = _spice_level(clause)
    if level is None:
        return False
    standing = re.search(
        r"\bi (?:\w+ ){0,2}?(?:like|love|enjoy|prefer|hate|dislike|can't|cannot|don't)\b"
        r"|\bmy spice\b|\bi'm (?:not (?:a fan|good with)|sensitive to)\b", clause,
    )
    if standing and not TEMPORARY.search(clause):
        out.add("spice", ("none", "mild", "medium", "hot")[level], clause)
    else:
        out.request.spice = level
    return True


def _budget(clause: str, out: _Extraction) -> None:
    amount = re.search(
        r"(?:budget(?:\s+\w+){0,3}?|under|below|less than|max(?:imum)?(?: of)?|up to|"
        r"no more than|within|spend(?: about| around)?)"
        r"\s*(?:is\s+|of\s+)?(?:sar\s*|sr\s*)?(\d{1,4})",
        clause,
    )
    if not amount:
        return
    standing = re.search(
        r"\bmy (?:usual )?budget\b|\bi (?:usually|always|normally|never)\b", clause
    )
    if standing and not TEMPORARY.search(clause):
        out.add("budget", amount.group(1), clause)
    else:
        out.request.max_price = float(amount.group(1))


def _tastes(clause: str, out: _Extraction) -> bool:
    dislike = re.search(
        r"\bi (?:really |absolutely |just |actually )?(?:hate|dislike|detest|loathe|can't stand|"
        r"don't like|do not like|don't enjoy|no longer like|no longer love|stopped liking|"
        r"don't love|don't eat|do not eat|never eat) (.+)|\b(?:i'm )?not a (?:big )?fan of (.+)",
        clause,
    )
    if dislike:
        fragment = next(g for g in dislike.groups() if g)
        changed = re.search(r"anymore|any more|no longer|stopped", clause)
        for term in _items(fragment):
            if term in SPICY_WORDS or not (_is_food(term) or _is_food(term.split()[-1])):
                continue
            if changed:
                out.add("like", term, clause, retract=True)
            out.add("dislike", term, clause)
        return True

    like = re.search(
        r"\bi (?:really |absolutely |also |now |actually |do )?"
        r"(?:love|like|enjoy|adore|prefer) (.+)"
        r"|\bmy favou?rite(?: \w+)? (?:is|are) (.+)|\bi'm (?:a big |a )?fan of (.+)",
        clause,
    )
    if like and not re.search(r"\b(?:would|'d) (?:like|love|prefer)\b", clause):
        fragment = next(g for g in like.groups() if g)
        for term in _items(fragment):
            words = term.split()
            if words[0] in CUISINES:
                out.add("cuisine", words[0], clause)
            elif _is_food(term):
                out.add("like", term, clause)
        return True
    return False


def _request(clause: str, out: _Extraction, preference_clause: bool) -> None:
    request = out.request
    for category, pattern in (
        ("starter", r"\b(starters?|appeti[sz]ers?)\b"),
        ("main", r"\b(mains?|main course|entree|dinner|lunch)\b"),
        ("dessert", r"\b(desserts?|something sweet)\b"),
        ("drink", r"\b(drinks?|beverages?|something to drink)\b"),
    ):
        if re.search(pattern, clause):
            request.category = category
    if re.search(r"\b(cheaper|less expensive|something cheap|more affordable)\b", clause):
        request.cheaper = True
    for cuisine in CUISINES:
        if cuisine in clause and not preference_clause:
            request.wants.append(cuisine)
    if preference_clause:
        return

    avoided = re.findall(r"\b(?:without|no|hold the|skip the) ([a-z ]+)", clause)
    for fragment in avoided:
        request.avoid.extend(f for f in _foods_in(fragment))
    wanting = re.search(
        r"\b(want|would like|'d like|craving|in the mood for|something with|recommend|suggest|"
        r"fancy|give me|show me|looking for|got any|any|have|something|anything)\b(.*)", clause,
    )
    if wanting:
        tail = re.sub(r"\b(?:without|no|hold the|skip the) [a-z ]+", " ", wanting.group(2))
        request.wants.extend(f for f in _foods_in(tail) if f not in request.avoid)
        diet = re.search(DIET_NAME, tail)
        if diet:
            request.diets.append(diet.group(1).replace("-", "_").replace(" ", "_"))


def _intent(text: str, out: _Extraction) -> str:
    comparing = r"\bcompare\b|\bdifference between\b|\bvs\.?\b|\bversus\b"
    if re.search(comparing + r"|\bwhich is (?:better|cheaper|spicier)\b", text):
        return "compare"
    asked = re.search(
        r"\b(?:do you (?:have|serve|do)|can i (?:get|have|order)|i'll have|tell me about|"
        r"what(?:'s| is) in(?: the)?|how much is(?: the)?)"
        r"\s+(?:a |an |the |some |any )?([a-z' -]+)",
        text,
    )
    if asked:
        stop = r"\b(?:please|today|tonight|for|with|without|that|which)\b"
        name = re.split(stop, asked.group(1))[0]
        if name.strip():
            out.dish_names.append(name.strip(" -'"))
        return "dish_question"
    if re.search(
        r"\b(recommend|suggest|what should|what can|hungry|craving|show me|options|menu|"
        r"something|i want|i'd like|in the mood|what do you|cheaper)\b", text,
    ) or out.request != RequestConstraints():
        return "recommend"
    if out.preferences:
        return "share"
    if re.search(r"\b(dinner|lunch|eat|food|order)\b", text):
        return "recommend"
    if re.match(r"\s*(hi|hello|hey|salam|good (?:morning|evening|afternoon))\b", text):
        return "greeting"
    return "other"


def understand(message: str) -> Understanding:
    out = _Extraction()
    for clause in clauses(message):
        allergy = _allergies(clause, out)
        diet = _diets(clause, out)
        spice = _spice(clause, out)
        _budget(clause, out)
        taste = False if allergy or diet else _tastes(clause, out)
        _request(clause, out, preference_clause=allergy or diet or taste)
        if spice and out.request.spice is None and TEMPORARY.search(clause):
            out.request.spice = _spice_level(clause)

    text = message.lower().replace("’", "'")
    intent = _intent(text, out)
    out.request.wants = [
        w for w in dict.fromkeys(out.request.wants) if w not in out.request.avoid
    ]
    return Understanding(
        intent=intent, preferences=out.preferences, request=out.request,
        dish_names=out.dish_names,
    )
