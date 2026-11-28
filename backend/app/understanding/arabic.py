"""Pattern-based reading of Arabic messages, including common Gulf wording.

Deliberately narrower than a model: allergies, diets, spice, price limits and simple
tastes. It exists so that clear safety statements survive when the model is unavailable.
Text is folded first (see `app.language.fold`), so patterns use folded spelling.
"""

import re

from app import language
from app.schemas import Candidate, RequestConstraints

# "ابي" and "ابغي" mean "I want" in Gulf Arabic, so they are not "my father".
OTHERS = re.compile(
    r"\b(?:و)?(?:زوجتي|زوجي|ولدي|ابني|بنتي|ابنتي|امي|والدتي|ابوي|والدي|اخوي|اخي|اختي|"
    r"صديقي|صاحبي|صديقتي|خويي|خويتي|ضيوفي|ضيوفنا|ضيفي|ضيف|طفلي|اطفالي|عيالي|جدتي|جدي|"
    r"زميلي|زميلتي)\b"
    r"|\b(?:شخص|واحد)\b|\b(?:عنده|عندها|عندهم)\b"
)
SELF = re.compile(r"(?:^|\s)(?:انا|وانا|وعندي)(?:\s|$)|عندي\s+(?:\S+\s+)?حساسيه")
HEDGE = re.compile(r"\b(?:اظن|اعتقد|يمكن|مدري|شكلي|ربما|احتمال|مو متاكد|لست متاكد)")
TEMPORARY = re.compile(r"\b(?:اليوم|الليله|هالمره|هالليله|هذي المره|هذه المره)")
CLAUSE_BREAK = re.compile(
    r"[.!?;\n]+|\s+(?:بس|لكن|ولكن)\s+|\s+(?=وانا\b)"
    # "... and I like ..." starts a new statement; "... and fish" does not.
    r"|\s+و(?=(?:احب|اعشق|اكره|ما احب|ابي|ابغي|ميزانيتي)\b)"
    r"|,\s*(?=(?:و)?(?:انا|عندي|ابي|ابغي|وش|ايش|شو|زوجتي|زوجي|ولدي|بنتي|لكن|بس)\b)"
)
WITHOUT = r"(?:بدون|بلا|من غير|ما فيه|ما فيها|مافيه|خالي من)\s+(.*)"
ASKING = r"\s+(?:وش|ايش|شو|ماذا|ممكن|ابي|ابغي|اقترح|تنصحني)\b"
NO_ALLERGY = re.compile(
    r"(?:ما عندي|ماعندي|ليس عندي|ليس لدي|ما عاد عندي|لم يعد لدي|مو عندي|مو|ما عدت|لست)\s+"
    r"(?:اي\s+)?(?:حساسيه|حساس|حساسه|اتحسس)\s*(.*)"
)
ALLERGY = re.compile(r"(?:حساسيه|حساسه|حساس|اتحسس|تتحسس|يتحسس|يتحسسون)\s*(.*)")
CANNOT = re.compile(r"(?:ما اقدر|ماقدر|لا استطيع|ما ينفع لي|ممنوع علي)\s+(?:اكل|تناول)\s+(.*)")
DIET = r"(نباتي صرف|نباتيه|نباتي|فيغن|فيجن)"
HOT = r"(?:الحار|حار|الحر|الشطه|الفلفل الحار)"
BUDGET = re.compile(
    r"(?:اقل من|تحت|ما يتجاوز|لا يتجاوز|بحدود|في حدود|ميزانيتي)\D{0,12}(\d{1,4})"
)
CATEGORY = (
    ("dessert", r"حلا|حلي|حلويات|تحليه"),
    ("starter", r"مقبلات|مقبل"),
    ("drink", r"مشروب|مشروبات|عصير"),
    ("main", r"طبق رئيسي|الرئيسي|العشا|عشاء|الغدا|غداء"),
)


def about_someone_else(clause: str) -> bool:
    return bool(OTHERS.search(clause)) and not SELF.search(clause)


def clauses(message: str) -> list[str]:
    return [c.strip(" ,") for c in CLAUSE_BREAK.split(language.fold(message)) if c.strip(" ,")]


class Reading:
    def __init__(self) -> None:
        self.preferences: list[Candidate] = []
        self.request = RequestConstraints()
        self.intent = ""

    def add(self, category: str, value: str, clause: str, *, retract: bool = False) -> None:
        self.preferences.append(Candidate(
            category=category,
            value=value[:60],
            operation="retract" if retract else "assert",
            scope="temporary" if TEMPORARY.search(clause) else "persistent",
            certainty="uncertain" if HEDGE.search(clause) else "explicit",
            evidence=clause[:300],
        ))


def _allergens(fragment: str) -> list[str]:
    """Canonical allergens or known foods named in the fragment, else the raw words."""
    fragment = re.split(ASKING, f" {fragment}")[0].strip()
    named = [a for group in language.find(fragment, language.ALLERGENS) for a in group]
    named += [
        food for food in language.find(fragment, language.FOODS)
        if food in ("mango", "tomato", "garlic", "onion", "coriander", "cumin", "lemon",
                    "honey", "date", "mushroom", "eggplant", "potato", "mint")
    ]
    if named:
        return list(dict.fromkeys(named))
    # Kept as written: the diner is asked to say which allergen it is.
    words = re.sub(r"^(?:من|ل|علي|ضد)\s+", "", fragment).split()
    return [" ".join(words[:3])] if words else []


def _allergy(clause: str, out: Reading) -> bool:
    other = about_someone_else(clause)
    removal = NO_ALLERGY.search(clause)
    stated = None if removal else ALLERGY.search(clause)
    cannot = None if removal or stated else CANNOT.search(clause)
    match = removal or stated or cannot
    if not match:
        return False
    terms = _allergens(match.group(1))
    if cannot:
        # "I can't eat X" is only an allergy statement when X is a known allergen.
        terms = [a for g in language.find(match.group(1), language.ALLERGENS) for a in g]
        if not terms:
            return False
    for term in terms:
        if other:
            if not removal:
                out.request.allergies.append(term)
        else:
            out.add("allergy", term, clause, retract=bool(removal))
            if cannot:
                out.preferences[-1].certainty = "uncertain"
    return True


def _diet(clause: str, out: Reading) -> bool:
    gone = re.search(rf"(?:ما عدت|لم اعد|مو|لست|ماني|تركت)\s+{DIET}", clause)
    stated = re.search(rf"(?:انا|وانا|صرت|اصبحت)\s+{DIET}|^{DIET}$", clause)
    match = gone or stated
    if not match or about_someone_else(clause):
        return False
    name = next(g for g in match.groups() if g)
    out.add("diet", language.DIETS[name], clause, retract=bool(gone))
    return True


def _spice_and_taste(clause: str, out: Reading) -> None:
    if about_someone_else(clause):
        return
    dislike = re.search(r"(?:ما احب|ما نحب|لا احب|ما ابي|ما ابغي|اكره|ما اقدر علي)\s+(.*)", clause)
    like = None if dislike else re.search(r"(?:احب|اعشق|افضل|يعجبني)\s+(.*)", clause)
    match = dislike or like
    if match and re.search(HOT, match.group(1)):
        out.add("spice", "none" if dislike else "hot", clause)
        return
    if match:
        category = "dislike" if dislike else "like"
        for food in language.find(match.group(1), language.FOODS):
            out.add(category, food, clause)
        return
    if re.search(rf"(?:بدون|بلا|مو|من غير)\s+{HOT}", clause):
        out.request.spice = 0
    elif re.search(rf"(?:ابي|ابغي|اريد|نبي|ودي)\b.*{HOT}", clause):
        out.request.spice = 3


def _request(clause: str, out: Reading) -> None:
    without = re.search(WITHOUT, clause)
    if without:
        out.request.avoid.extend(language.find(without.group(1), language.FOODS))
        clause = clause[:without.start()]
    for category, pattern in CATEGORY:
        if re.search(rf"(?:^|\s|ال|و|لل)(?:{pattern})\b", clause):
            out.request.category = category
    amount = BUDGET.search(clause)
    if amount:
        if "ميزانيتي" in clause or re.search(r"\b(?:دايم|دائما|عاده)\b", clause):
            out.add("budget", amount.group(1), clause)
        else:
            out.request.max_price = float(amount.group(1))
    if re.search(r"ارخص", clause):
        out.request.cheaper = True
    wanting = re.search(r"(?:ابي|ابغي|اريد|ودي|اشتهي|عطني|عندكم)\s+(.*)", clause)
    if wanting:
        out.request.wants.extend(language.find(wanting.group(1), language.FOODS))


def _intent(text: str, out: Reading) -> str:
    if re.search(r"قارن|الفرق بين", text):
        return "compare"
    if re.search(r"عندكم|فيه عندكم|هل\s", text):
        return "dish_question"
    if (
        re.search(r"تنصح|اقترح|ابي|ابغي|اريد|جوعان|وش اكل|ايش اكل|اشتهي|ارخص|قائمه", text)
        or out.request != RequestConstraints()
    ):
        return "recommend"
    if out.preferences:
        return "share"
    if re.search(r"مرحبا|السلام|هلا|اهلا|صباح|مساء", text):
        return "greeting"
    return "other"


def read(message: str) -> Reading:
    out = Reading()
    for clause in clauses(message):
        if not _allergy(clause, out):
            if not _diet(clause, out):
                _spice_and_taste(clause, out)
            _request(clause, out)
        else:
            # Courses and prices can share a clause with an allergy.
            _request(clause.split("حساس")[0], out)
            tail = re.split(ASKING, clause)
            if len(tail) > 1:
                _request(clause[len(tail[0]):], out)
    out.intent = _intent(language.fold(message), out)
    return out
