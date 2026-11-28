"""Arabic text handling and the Arabic words that map to canonical values.

Memory is stored once, in canonical English keys, whatever language it was said in.
Everything here is about getting from Arabic wording to those keys.
"""

import re

ARABIC_LETTER = re.compile(r"[ء-ي]")
_MARKS = re.compile(r"[ـً-ٰٟ]")
_SPELLING = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه", "ى": "ي",
    "؟": "?", "،": ",", "؛": ";", "’": "'",
    **{digit: str(i % 10) for i, digit in enumerate("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹")},
})
_PREFIXES = ("وال", "بال", "لل", "ال", "و")


def is_arabic(text: str) -> bool:
    return bool(ARABIC_LETTER.search(text))


def fold(text: str) -> str:
    """Comparable form: no vowel marks, one spelling per letter, Western digits."""
    return _MARKS.sub("", text.lower()).translate(_SPELLING)


def _table(entries: dict[str, tuple[str, ...] | str]) -> dict:
    return {fold(word): value for word, value in entries.items()}


# Multi-word entries are matched before single words, so coconut is not read as a walnut.
ALLERGENS = _table({
    "سمسم": ("sesame",), "طحينة": ("sesame",), "طحينية": ("sesame",),
    "مكسرات": ("peanut", "tree_nut"), "فول سوداني": ("peanut",), "فستق عبيد": ("peanut",),
    "لوز": ("tree_nut",), "كاجو": ("tree_nut",), "جوز": ("tree_nut",), "فستق": ("tree_nut",),
    "بندق": ("tree_nut",), "صنوبر": ("tree_nut",), "جوز الهند": (),
    "حليب": ("milk",), "لبن": ("milk",), "ألبان": ("milk",), "منتجات الألبان": ("milk",),
    "لاكتوز": ("milk",), "جبن": ("milk",), "جبنة": ("milk",), "أجبان": ("milk",),
    "بيض": ("egg",), "سمك": ("fish",), "أسماك": ("fish",),
    "جمبري": ("crustacean",), "روبيان": ("crustacean",), "قريدس": ("crustacean",),
    "قشريات": ("crustacean",), "محار": ("mollusc",), "رخويات": ("mollusc",),
    "مأكولات بحرية": ("fish", "crustacean", "mollusc"),
    "جلوتين": ("gluten",), "غلوتين": ("gluten",), "قمح": ("gluten",),
    "صويا": ("soy",), "خردل": ("mustard",), "كرفس": ("celery",), "كبريتيت": ("sulphites",),
})

FOODS = _table({
    "دجاج": "chicken", "فراخ": "chicken", "لحم": "meat", "خروف": "lamb", "غنم": "lamb",
    "لحم غنم": "lamb", "لحم خروف": "lamb", "بقر": "beef", "لحم بقر": "beef",
    "سمك": "fish", "روبيان": "prawn", "جمبري": "prawn", "فطر": "mushroom",
    "مشروم": "mushroom", "حلومي": "halloumi", "جبن": "cheese", "جبنة": "cheese",
    "عدس": "lentil", "حمص": "hummus", "فلافل": "falafel", "رز": "rice", "أرز": "rice",
    "مانجو": "mango", "باذنجان": "eggplant", "ثوم": "garlic", "بصل": "onion",
    "كزبرة": "coriander", "كمون": "cumin", "زيتون": "olive", "كاري": "curry",
    "كبسة": "kabsa", "كنافة": "kunafa", "شوربة": "soup", "شاورما": "shawarma",
    "طماطم": "tomato", "ليمون": "lemon", "نعناع": "mint", "عسل": "honey", "تمر": "date",
    "زعفران": "saffron", "بطاطس": "potato", "سبانخ": "spinach", "مكسرات": "nut",
    "لوز": "almond", "فستق": "pistachio", "كاجو": "cashew", "جوز": "walnut",
})

DIETS = _table({
    "نباتي": "vegetarian", "نباتية": "vegetarian", "نباتي صرف": "vegan", "فيغن": "vegan",
    "فيجن": "vegan", "خالي من الجلوتين": "gluten_free", "خالي من الألبان": "dairy_free",
})
SPICE = _table({
    "بدون حار": "none", "خفيف": "mild", "متوسط": "medium", "وسط": "medium", "حار": "hot",
})
CUISINES = _table({
    "هندي": "indian", "خليجي": "gulf", "شامي": "levantine", "متوسطي": "mediterranean",
})


def _candidates(word: str) -> list[str]:
    """The word and the word without an attached "the", "and" or "for the"."""
    return [word] + [
        word[len(p):] for p in _PREFIXES if word.startswith(p) and len(word) - len(p) > 1
    ]


def find(text: str, table: dict) -> list:
    """Values for every entry of `table` mentioned in `text`, longest phrases first."""
    words = re.findall(r"[ء-ي]+", fold(text))
    found = []
    i = 0
    while i < len(words):
        for size in (3, 2, 1):
            chunk = words[i:i + size]
            if len(chunk) < size:
                continue
            # Only the first word of a phrase carries an attached prefix, except that a
            # following "the" is dropped too: "الفول السوداني".
            rest = " ".join(w.removeprefix("ال") for w in chunk[1:])
            keys = [" ".join(filter(None, (head, rest))) for head in _candidates(chunk[0])]
            keys.append(" ".join(chunk))
            match = next((k for k in keys if k in table), None)
            if match is not None:
                found.append(table[match])
                i += size
                break
        else:
            i += 1
    return found
