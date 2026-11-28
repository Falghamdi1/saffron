import type { Lang } from "./i18n";
import type { MenuItem, Preference } from "./types";

// Display labels for the canonical values the server stores.
const ENGLISH: Record<string, string> = {
  milk: "dairy",
  peanut: "peanuts",
  tree_nut: "tree nuts",
  crustacean: "crustaceans",
  mollusc: "molluscs",
};

// Mirrors ARABIC_VALUES in backend/app/i18n.py; a test keeps them in step.
const ARABIC: Record<string, string> = {
  milk: "الألبان",
  egg: "البيض",
  fish: "السمك",
  crustacean: "القشريات",
  mollusc: "الرخويات",
  peanut: "الفول السوداني",
  tree_nut: "المكسرات الشجرية",
  gluten: "الجلوتين",
  soy: "الصويا",
  sesame: "السمسم",
  mustard: "الخردل",
  celery: "الكرفس",
  sulphites: "الكبريتيت",
  vegetarian: "نباتي",
  vegan: "نباتي صرف",
  pescatarian: "نباتي مع السمك",
  gluten_free: "خالٍ من الجلوتين",
  dairy_free: "خالٍ من الألبان",
  none: "بدون حار",
  mild: "خفيف",
  medium: "متوسط",
  hot: "حار",
  levantine: "شامي",
  gulf: "خليجي",
  indian: "هندي",
  mediterranean: "متوسطي",
  chicken: "الدجاج",
  meat: "اللحم",
  lamb: "لحم الغنم",
  beef: "لحم البقر",
  prawn: "الروبيان",
  mushroom: "الفطر",
  halloumi: "الحلومي",
  cheese: "الجبن",
  lentil: "العدس",
  hummus: "الحمص",
  falafel: "الفلافل",
  rice: "الأرز",
  mango: "المانجو",
  eggplant: "الباذنجان",
  garlic: "الثوم",
  onion: "البصل",
  coriander: "الكزبرة",
  cumin: "الكمون",
  olive: "الزيتون",
  curry: "الكاري",
  kabsa: "الكبسة",
  kunafa: "الكنافة",
  soup: "الشوربة",
  shawarma: "الشاورما",
  tomato: "الطماطم",
  lemon: "الليمون",
  mint: "النعناع",
  honey: "العسل",
  date: "التمر",
  saffron: "الزعفران",
  potato: "البطاطس",
  spinach: "السبانخ",
  nut: "المكسرات",
  almond: "اللوز",
  pistachio: "الفستق",
  cashew: "الكاجو",
  walnut: "الجوز",
};

export const ALLERGENS = [
  "milk", "egg", "fish", "crustacean", "mollusc", "peanut", "tree_nut",
  "gluten", "soy", "sesame", "mustard", "celery", "sulphites",
];

const SPICE_NAMES: Record<Lang, string[]> = {
  en: ["Not spicy", "Mild", "Medium", "Hot"],
  ar: ["غير حار", "خفيف", "متوسط", "حار"],
};

export const spiceName = (level: number, lang: Lang) => SPICE_NAMES[lang][level];

export function label(value: string, lang: Lang): string {
  if (lang === "ar") return ARABIC[value] ?? value.replace(/-/g, " ");
  return ENGLISH[value] ?? value.replace(/_/g, "-");
}

export const list = (values: string[], lang: Lang) =>
  values.map((value) => label(value, lang)).join(lang === "ar" ? "، " : ", ");

// A non-breaking space keeps the currency with its amount. Western digits in both languages.
export const price = (amount: number, lang: Lang) =>
  lang === "ar" ? `${amount} ر.س` : `SAR ${amount}`;

export const dishText = (item: MenuItem, lang: Lang) =>
  lang === "ar" && item.name_ar
    ? { name: item.name_ar, description: item.description_ar, ingredients: item.ingredients_ar }
    : { name: item.name, description: item.description, ingredients: item.ingredients };

export function preferenceText(
  preference: Pick<Preference, "category" | "value">,
  lang: Lang,
): string {
  const { category, value } = preference;
  const shown = label(value, lang);
  const ar = lang === "ar";
  switch (category) {
    case "allergy":
      return ar ? `حساسية من ${shown}` : `Allergic to ${shown}`;
    case "diet":
      return ar ? `النظام الغذائي: ${shown}` : `Follows a ${shown} diet`;
    case "like":
      return ar ? `تحب ${shown}` : `Likes ${value}`;
    case "dislike":
      return ar ? `تتجنب ${shown}` : `Avoids ${value}`;
    case "cuisine":
      return ar ? `تحب المطبخ ال${shown}` : `Enjoys ${value} food`;
    case "spice":
      return ar ? `الحرارة: ${shown}` : `Spice: ${value === "none" ? "none at all" : value}`;
    case "budget":
      return ar ? `حتى ${value} ر.س للطبق` : `Up to SAR ${value} per dish`;
    default:
      return `${ar ? "مفضل" : "Favourite"}: ${value.replace(/-/g, " ")}`;
  }
}

export function when(timestamp: string, lang: Lang): string {
  const date = new Date(timestamp.replace(" ", "T").replace(/\+00$/, "Z"));
  const locale = lang === "ar" ? "ar-SA-u-ca-gregory-nu-latn" : "en-GB";
  return Number.isNaN(date.getTime())
    ? ""
    : date.toLocaleString(locale, { dateStyle: "medium", timeStyle: "short" });
}
