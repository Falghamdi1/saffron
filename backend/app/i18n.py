"""Every sentence the assistant can say, in English and Arabic.

Replies are composed from these templates and menu records, never generated, so both
languages state the same facts. Values stay canonical; only their labels change.
"""

from app import language
from app.vocabulary import label

Language = str  # "en" or "ar"


def language_of(text: str) -> Language:
    return "ar" if language.is_arabic(text) else "en"


ARABIC_VALUES = {
    "milk": "الألبان", "egg": "البيض", "fish": "السمك", "crustacean": "القشريات",
    "mollusc": "الرخويات", "peanut": "الفول السوداني", "tree_nut": "المكسرات الشجرية",
    "gluten": "الجلوتين", "soy": "الصويا", "sesame": "السمسم", "mustard": "الخردل",
    "celery": "الكرفس", "sulphites": "الكبريتيت",
    "vegetarian": "نباتي", "vegan": "نباتي صرف", "pescatarian": "نباتي مع السمك",
    "gluten_free": "خالٍ من الجلوتين", "dairy_free": "خالٍ من الألبان",
    "none": "بدون حار", "mild": "خفيف", "medium": "متوسط", "hot": "حار",
    "levantine": "الشامي", "gulf": "الخليجي", "indian": "الهندي",
    "mediterranean": "المتوسطي",
    "chicken": "الدجاج", "meat": "اللحم", "lamb": "لحم الغنم", "beef": "لحم البقر",
    "prawn": "الروبيان", "mushroom": "الفطر", "halloumi": "الحلومي", "cheese": "الجبن",
    "lentil": "العدس", "hummus": "الحمص", "falafel": "الفلافل", "rice": "الأرز",
    "mango": "المانجو", "eggplant": "الباذنجان", "garlic": "الثوم", "onion": "البصل",
    "coriander": "الكزبرة", "cumin": "الكمون", "olive": "الزيتون", "curry": "الكاري",
    "kabsa": "الكبسة", "kunafa": "الكنافة", "soup": "الشوربة", "shawarma": "الشاورما",
    "tomato": "الطماطم", "lemon": "الليمون", "mint": "النعناع", "honey": "العسل",
    "date": "التمر", "saffron": "الزعفران", "potato": "البطاطس", "spinach": "السبانخ",
    "nut": "المكسرات", "almond": "اللوز", "pistachio": "الفستق", "cashew": "الكاجو",
    "walnut": "الجوز",
}


def name(value: str, lang: Language) -> str:
    """A canonical value as the diner reads it. Unknown values are shown as stored."""
    if lang == "ar":
        return ARABIC_VALUES.get(value, value)
    return label(value)


def join(parts: list[str], lang: Language, *, last: str = "and") -> str:
    if len(parts) == 1:
        return parts[0]
    if lang == "ar":
        word = {"and": " و", "or": " أو "}[last]
        return "، ".join(parts[:-1]) + word + parts[-1]
    return f"{', '.join(parts[:-1])} {last} {parts[-1]}"


_EN = {
    "help": "Tell me what you feel like eating, anything you can't have, or a budget. "
            "You can also ask me to compare two dishes.",
    "welcome": "Welcome to Saffron.",
    "offer": "Would you like some suggestions?",
    "which_dishes": "Which two dishes would you like me to compare?",
    "unknown_dish": "“{name}” isn't on our menu, so I can't tell you anything about it.",
    "instead": "These are on the menu instead.",
    "notice": "Checked against recorded ingredient and “may contain” data for {allergies}. "
              "This cannot rule out cross-contact in the kitchen, so please tell your server "
              "about the allergy.",
    "untracked": "{names} is not a formally tracked allergen here: only ingredient names "
                 "were checked.",
    "table": "For this chat only, I'm also avoiding {allergies}. It is not saved to your "
             "preferences; if it is your own allergy, tell me “I'm allergic to …”.",
    "unmatched": "I couldn't find an option with {wants} that fits.",
    "nothing_cheaper": "Nothing cheaper fits your requirements.",
    "nothing": "Nothing on the menu meets all of your requirements right now. I won't relax "
               "an allergy or diet, but you could raise the budget or change the course.",
    "here_one": "Here is {names}.",
    "here_many": "Here are {names}.",
    "left_out_one": "I left out 1 dish that breaks one of your requirements.",
    "left_out_many": "I left out {count} dishes that break one of your requirements.",
    "earlier_limit": "I'm still keeping to the SAR {amount} limit you gave earlier in this "
                     "chat.",
    "facts": "{name} is SAR {price}. Ingredients: {ingredients}. Allergens: {allergens}.",
    "none_recorded": "none recorded",
    "may_contain": "May contain {allergens}.",
    "incomplete": "Its allergen information is incomplete.",
    "not_for_you": "I don't recommend it for you: {problems}.",
    "compare": "Here are {names} side by side. {cheapest} is the least expensive.",
    "unsuitable": "Not suitable for you: {dishes}.",
    "v_unavailable": "currently unavailable",
    "v_unidentified": "an allergy has not been identified",
    "v_contains": "contains {food}",
    "v_may_contain": "may contain {food}",
    "v_incomplete": "allergen information is incomplete",
    "v_not_diet": "not {diet}",
    "v_dislike": "includes {food}, which you avoid",
    "v_budget": "SAR {price} is over your SAR {limit} budget",
    "r_want": "Matches your request for {food}",
    "r_likes": "Features {foods}, which you like",
    "r_favourite": "One of your saved favourites",
    "r_cuisine": "{cuisine} cuisine, which you enjoy",
    "r_spice": "Spice level is {level}, as you prefer",
    "r_diet": "Meets your {diets} requirement",
    "r_budget": "SAR {price}, within your SAR {limit} budget",
    "r_allergies": "No {allergies} listed in its recorded ingredients",
    "c_incomplete": "Allergen information for this dish is incomplete.",
    "c_spicier": "Spicier than you usually like.",
    "d_allergy": "allergy to {value}",
    "d_diet": "{value} diet",
    "d_like": "likes {value}",
    "d_dislike": "dislikes {value}",
    "d_cuisine": "enjoys {value} cuisine",
    "d_spice": "{value} spice level",
    "d_budget": "budget of SAR {value} per dish",
    "d_favorite_dish": "favourite dish: {value}",
    "temporary_use": "Using “{what}” for this chat only.",
    "temporary_drop": "Setting aside “{what}” for this chat only.",
    "kept": "I've kept your {what}. Please confirm before I remove it.",
    "removed": "Removed: {what}.",
    "ask": "Should I remember this: {what}?",
    "ask_avoid": "Until you confirm, I'll avoid it to be safe.",
    "unidentified": "I couldn't tell which allergen “{value}” is, so I won't suggest dishes "
                    "yet. Choose it under My preferences with “Add an allergy”, then dismiss "
                    "this one.",
    "updated": "Updated: {what} (was: {previous}).",
    "saved": "Remembered: {what}.",
    "allergy_conflict": "You have an allergy on record that covers {food}, so I haven't "
                        "added it as a favourite. Your allergy protection stays in place.",
    "diet_conflict": "You're saved as {diet}, which doesn't include {food}. If that has "
                     "changed, tell me “I'm no longer {diet}”.",
}

_AR = {
    "help": "أخبرني بما تشتهيه، أو ما لا يمكنك أكله، أو ميزانيتك. ويمكنني أيضاً مقارنة طبقين.",
    "welcome": "أهلاً بك في زعفران.",
    "offer": "هل تود بعض الاقتراحات؟",
    "which_dishes": "أي طبقين تريد أن أقارن بينهما؟",
    "unknown_dish": "«{name}» ليس في قائمتنا، لذلك لا أستطيع إخبارك بشيء عنه.",
    "instead": "هذه أطباق موجودة في القائمة.",
    "notice": "تم الفحص مقابل بيانات المكونات و«قد يحتوي على» المسجلة بخصوص {allergies}. "
              "لا يمكن استبعاد التلامس المتبادل في المطبخ، فأرجو إبلاغ النادل بالحساسية.",
    "untracked": "{names} ليس من مسببات الحساسية المتتبعة هنا: تم فحص أسماء المكونات فقط.",
    "table": "لهذه المحادثة فقط، سأتجنب أيضاً {allergies}. لم أحفظها في تفضيلاتك؛ وإذا كانت "
             "حساسيتك أنت فقل «عندي حساسية من …».",
    "unmatched": "لم أجد خياراً فيه {wants} يناسبك.",
    "nothing_cheaper": "لا يوجد خيار أرخص يناسب متطلباتك.",
    "nothing": "لا يوجد طبق في القائمة يحقق جميع متطلباتك حالياً. لن أتجاوز حساسية أو نظاماً "
               "غذائياً، لكن يمكنك رفع الميزانية أو تغيير نوع الطبق.",
    "here_one": "أقترح عليك {names}.",
    "here_many": "أقترح عليك {names}.",
    "left_out_one": "استبعدت طبقاً واحداً يخالف أحد متطلباتك.",
    "left_out_many": "استبعدت {count} أطباق تخالف أحد متطلباتك.",
    "earlier_limit": "ما زلت ملتزماً بحد {amount} ر.س الذي ذكرته سابقاً في هذه المحادثة.",
    "facts": "{name} بسعر {price} ر.س. المكونات: {ingredients}. مسببات الحساسية: {allergens}.",
    "none_recorded": "لا يوجد مسجل",
    "may_contain": "قد يحتوي على {allergens}.",
    "incomplete": "معلومات الحساسية لهذا الطبق غير مكتملة.",
    "not_for_you": "لا أنصحك به: {problems}.",
    "compare": "هذه مقارنة بين {names}. الأقل سعراً: {cheapest}.",
    "unsuitable": "لا يناسبك: {dishes}.",
    "v_unavailable": "غير متوفر حالياً",
    "v_unidentified": "توجد حساسية لم يتم تحديدها",
    "v_contains": "يحتوي على {food}",
    "v_may_contain": "قد يحتوي على {food}",
    "v_incomplete": "معلومات الحساسية غير مكتملة",
    "v_not_diet": "لا يناسب نظام {diet}",
    "v_dislike": "فيه {food} الذي تتجنبه",
    "v_budget": "سعره {price} ر.س ويتجاوز ميزانيتك {limit} ر.س",
    "r_want": "يطابق طلبك: {food}",
    "r_likes": "فيه {foods} الذي تحبه",
    "r_favourite": "من أطباقك المفضلة",
    "r_cuisine": "من المطبخ {cuisine} الذي تحبه",
    "r_spice": "درجة الحرارة {level} كما تفضل",
    "r_diet": "يناسب نظامك: {diets}",
    "r_budget": "{price} ر.س ضمن ميزانيتك {limit} ر.س",
    "r_allergies": "لا يوجد {allergies} ضمن مكوناته المسجلة",
    "c_incomplete": "معلومات الحساسية لهذا الطبق غير مكتملة.",
    "c_spicier": "أحرّ مما تفضل عادة.",
    "d_allergy": "حساسية من {value}",
    "d_diet": "نظام {value}",
    "d_like": "تحب {value}",
    "d_dislike": "لا تحب {value}",
    "d_cuisine": "تحب المطبخ {value}",
    "d_spice": "درجة الحرارة المفضلة: {value}",
    "d_budget": "ميزانية {value} ر.س للطبق",
    "d_favorite_dish": "طبق مفضل: {value}",
    "temporary_use": "سأطبق «{what}» في هذه المحادثة فقط.",
    "temporary_drop": "سأتجاوز «{what}» في هذه المحادثة فقط.",
    "kept": "أبقيت {what}. أرجو التأكيد قبل أن أزيلها.",
    "removed": "تم الحذف: {what}.",
    "ask": "هل أحفظ هذا: {what}؟",
    "ask_avoid": "سأتجنبه احتياطاً إلى أن تؤكد.",
    "unidentified": "لم أتمكن من تحديد مسبب الحساسية «{value}»، لذلك لن أقترح أطباقاً الآن. "
                    "اختره من «تفضيلاتي» عبر «إضافة حساسية»، ثم ارفض هذا السجل.",
    "updated": "تم التحديث: {what} (كان: {previous}).",
    "saved": "حفظت: {what}.",
    "allergy_conflict": "لديك حساسية مسجلة تشمل {food}، لذلك لم أضفه إلى ما تحب. "
                        "حمايتك من الحساسية باقية.",
    "diet_conflict": "أنت مسجل بنظام {diet} الذي لا يشمل {food}. إذا تغير ذلك فقل "
                     "«ما عدت {diet}».",
}

STRINGS = {"en": _EN, "ar": _AR}


def say(lang: Language, key: str, **values: object) -> str:
    return STRINGS[lang][key].format(**values)
