import type { Preference } from "./types";

const ALLERGEN_LABELS: Record<string, string> = {
  milk: "dairy",
  peanut: "peanuts",
  tree_nut: "tree nuts",
  crustacean: "crustaceans",
  mollusc: "molluscs",
};

export const ALLERGENS = [
  "milk", "egg", "fish", "crustacean", "mollusc", "peanut", "tree_nut",
  "gluten", "soy", "sesame", "mustard", "celery", "sulphites",
];

export const SPICE_NAMES = ["Not spicy", "Mild", "Medium", "Hot"];

export const label = (value: string) => ALLERGEN_LABELS[value] ?? value.replace(/_/g, "-");

export const price = (amount: number) => `SAR ${amount}`;

export function preferenceText(preference: Pick<Preference, "category" | "value">): string {
  const { category, value } = preference;
  switch (category) {
    case "allergy":
      return `Allergic to ${label(value)}`;
    case "diet":
      return `Follows a ${label(value)} diet`;
    case "like":
      return `Likes ${value}`;
    case "dislike":
      return `Avoids ${value}`;
    case "cuisine":
      return `Enjoys ${value} food`;
    case "spice":
      return `Spice: ${value === "none" ? "none at all" : value}`;
    case "budget":
      return `Up to SAR ${value} per dish`;
    default:
      return `Favourite: ${value.replace(/-/g, " ")}`;
  }
}

export function when(timestamp: string): string {
  const date = new Date(timestamp.replace(" ", "T").replace(/\+00$/, "Z"));
  return Number.isNaN(date.getTime())
    ? ""
    : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}
