import { dishText, label, list, price, spiceName } from "../format";
import { useLanguage } from "../i18n";
import type { MenuItem } from "../types";
import Icon from "./Icons";

interface Props {
  items: MenuItem[];
  violations?: string[][];
}

export default function CompareTable({ items, violations }: Props) {
  const { lang, t } = useLanguage();
  const rows: [string, (item: MenuItem) => string][] = [
    [t.price, (item) => price(item.price, lang)],
    [t.spice, (item) => spiceName(item.spice_level, lang)],
    [
      t.allergens,
      (item) =>
        item.allergen_info_complete
          ? list(item.allergens, lang) || t.noneRecorded
          : t.incompleteInfo,
    ],
    [t.mayContainHead, (item) => list(item.may_contain, lang) || t.noneRecorded],
    [t.diets, (item) => list(item.diets, lang) || t.noneListed],
    [t.ingredients, (item) => dishText(item, lang).ingredients.join(lang === "ar" ? "، " : ", ")],
    [
      t.cuisine,
      (item) => {
        const name = label(item.cuisine, lang);
        return name.charAt(0).toUpperCase() + name.slice(1);
      },
    ],
    [t.available, (item) => (item.available ? t.yes : t.notToday)],
  ];
  const head = "bg-card sticky start-0 p-2 text-start align-top font-semibold sm:p-3";
  const cell = "min-w-20 p-2 align-top sm:min-w-24 sm:p-3";

  return (
    <div className="border-line bg-card rounded-panel overflow-x-auto border">
      <table className="w-full text-start text-[13px] tabular-nums sm:text-sm">
        <thead>
          <tr className="border-ink border-b">
            <td className={head} />
            {items.map((item) => (
              <th
                key={item.id}
                scope="col"
                className={`font-display text-sm font-semibold sm:text-base ${cell}`}
              >
                {dishText(item, lang).name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="[&_tr+tr>*]:border-line [&_tr+tr>*]:border-t">
          {violations && (
            <tr>
              <th scope="row" className={head}>
                {t.forYou}
              </th>
              {items.map((item, index) => {
                const problems = violations[index] ?? [];
                return (
                  <td key={item.id} className={cell}>
                    <span className={`flex gap-1.5 ${problems.length ? "text-alert" : "text-herb"}`}>
                      <Icon name={problems.length ? "warning" : "check"} className="mt-0.5" />
                      <bdi>{problems.join("; ") || t.fits}</bdi>
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
