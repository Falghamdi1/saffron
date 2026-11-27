import { label, price, SPICE_NAMES } from "../format";
import type { MenuItem } from "../types";
import Icon from "./Icons";

interface Props {
  items: MenuItem[];
  violations?: string[][];
}

export default function CompareTable({ items, violations }: Props) {
  const rows: [string, (item: MenuItem) => string][] = [
    ["Price", (item) => price(item.price)],
    ["Spice", (item) => SPICE_NAMES[item.spice_level]],
    [
      "Allergens",
      (item) =>
        item.allergen_info_complete
          ? item.allergens.map(label).join(", ") || "none recorded"
          : "information incomplete",
    ],
    ["May contain", (item) => item.may_contain.map(label).join(", ") || "none recorded"],
    ["Diets", (item) => item.diets.map(label).join(", ") || "none listed"],
    ["Ingredients", (item) => item.ingredients.join(", ")],
    ["Cuisine", (item) => item.cuisine.charAt(0).toUpperCase() + item.cuisine.slice(1)],
    ["Available", (item) => (item.available ? "Yes" : "Not today")],
  ];
  const head = "bg-card sticky left-0 p-2 text-left align-top font-semibold sm:p-3";
  const cell = "min-w-20 p-2 align-top sm:min-w-24 sm:p-3";

  return (
    <div className="border-line bg-card rounded-panel overflow-x-auto border">
      <table className="w-full text-left text-[13px] tabular-nums sm:text-sm">
        <thead>
          <tr className="border-ink border-b">
            <td className={head} />
            {items.map((item) => (
              <th
                key={item.id}
                scope="col"
                className={`font-display text-sm font-semibold sm:text-base ${cell}`}
              >
                {item.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="[&_tr+tr>*]:border-line [&_tr+tr>*]:border-t">
          {violations && (
            <tr>
              <th scope="row" className={head}>
                For you
              </th>
              {items.map((item, index) => {
                const problems = violations[index] ?? [];
                return (
                  <td key={item.id} className={cell}>
                    <span className={`flex gap-1.5 ${problems.length ? "text-alert" : "text-herb"}`}>
                      <Icon name={problems.length ? "warning" : "check"} className="mt-0.5" />
                      {problems.join("; ") || "Fits your requirements"}
                    </span>
                  </td>
                );
              })}
            </tr>
          )}
          {rows.map(([heading, value]) => (
            <tr key={heading}>
              <th scope="row" className={head}>
                {heading}
              </th>
              {items.map((item) => (
                <td key={item.id} className={cell}>
                  {value(item)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
