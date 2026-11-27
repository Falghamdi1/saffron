import { label, price, SPICE_NAMES } from "../format";
import type { MenuItem } from "../types";

interface Props {
  items: MenuItem[];
  violations?: string[][];
}

export default function CompareTable({ items, violations }: Props) {
  const rows: [string, (item: MenuItem, index: number) => string][] = [
    ["Price", (item) => price(item.price)],
    ["Spice", (item) => SPICE_NAMES[item.spice_level]],
    ["Cuisine", (item) => item.cuisine],
    ["Ingredients", (item) => item.ingredients.join(", ")],
    [
      "Allergens",
      (item) =>
        item.allergen_info_complete
          ? item.allergens.map(label).join(", ") || "none recorded"
          : "incomplete",
    ],
    ["May contain", (item) => item.may_contain.map(label).join(", ") || "none recorded"],
    ["Diets", (item) => item.diets.map(label).join(", ") || "none listed"],
    ["Available", (item) => (item.available ? "Yes" : "Not today")],
  ];
  if (violations) {
    rows.push(["For you", (_, index) => violations[index].join("; ") || "Fits your requirements"]);
  }

  return (
    <div className="border-line bg-card overflow-x-auto rounded-2xl border">
      <table className="w-full min-w-max text-left text-sm">
        <thead>
          <tr>
            <th className="p-3" />
            {items.map((item) => (
              <th key={item.id} className="font-display max-w-48 p-3 text-base font-semibold">
                {item.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(([heading, value]) => (
            <tr key={heading} className="border-line border-t align-top">
              <th scope="row" className="eyebrow p-3">
                {heading}
              </th>
              {items.map((item, index) => (
                <td key={item.id} className="max-w-48 p-3 whitespace-normal">
                  {value(item, index)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
