import { dishText, label, list, price, spiceName } from "../format";
import { useLanguage } from "../i18n";
import type { MenuItem } from "../types";
import Icon from "./Icons";
import type { DishActions } from "./Workspace";

interface Props {
  item: MenuItem;
  actions: DishActions;
  reasons?: string[];
  cautions?: string[];
  violations?: string[];
}

const DIET_LABELS = ["vegan", "vegetarian", "gluten_free", "dairy_free"];

function Spice({ level }: { level: number }) {
  const { lang } = useLanguage();
  return (
    <span className="inline-flex items-center gap-1.5">
      <span aria-hidden="true" className="inline-flex gap-0.5">
        {[1, 2, 3].map((step) => (
          <span key={step} className={`h-3 w-1 ${step <= level ? "bg-ember" : "bg-line"}`} />
        ))}
      </span>
      {spiceName(level, lang)}
    </span>
  );
}

/** A dish as it would be set on a printed menu: name, leader, price, then the facts. */
export default function DishEntry({ item, actions, reasons, cautions = [], violations = [] }: Props) {
  const { lang, t } = useLanguage();
  const text = dishText(item, lang);
  const compared = actions.compared.some((c) => c.id === item.id);
  const favourite = actions.favourites.has(item.id);
  const diets = item.diets.filter((diet) => DIET_LABELS.includes(diet));
  const allergens = item.allergen_info_complete
    ? list(item.allergens, lang) || t.noneRecorded
    : t.incompleteAsk;

  return (
    <article className="flex min-w-0 flex-1 flex-col gap-1.5">
      <header className="flex items-baseline gap-2">
        <h3 className="font-display min-w-0 text-lg leading-snug font-semibold">{text.name}</h3>
        <span aria-hidden="true" className="border-line-strong min-w-4 flex-1 border-b border-dotted" />
        <p className="shrink-0 font-semibold tabular-nums">{price(item.price, lang)}</p>
      </header>
      <p className="text-sm">{text.description}</p>
      <p className="text-muted flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px]">
        <Spice level={item.spice_level} />
        {diets.map((diet) => (
          <span key={diet} className="text-herb font-medium capitalize">
            {label(diet, lang)}
          </span>
        ))}
      </p>
      <p className="text-muted text-[13px] leading-relaxed">
        {text.ingredients.join(lang === "ar" ? "، " : ", ")}
      </p>
      {/* Allergens are safety information, so they are set larger and darker than the rest. */}
      <p className="text-sm">
        <span className="font-semibold">{t.allergens}:</span> {allergens}
        {item.may_contain.length > 0 && `; ${t.mayContain} ${list(item.may_contain, lang)}`}
      </p>

      {reasons && reasons.length > 0 && (
        <ul dir="auto" className="text-herb mt-0.5 space-y-0.5 text-[13px]" aria-label={t.why}>
          {reasons.map((reason) => (
            <li key={reason} className="flex gap-1.5">
              <Icon name="check" className="mt-0.5 size-3.5" />
              {reason}
            </li>
          ))}
        </ul>
      )}
      {[...cautions, ...(violations.length ? [`${t.notForYou} ${violations.join("; ")}`] : [])].map(
        (warning) => (
          <p key={warning} dir="auto" className="text-alert flex gap-1.5 text-sm font-medium">
            <Icon name="warning" className="mt-0.5" />
            {warning}
          </p>
        ),
      )}

      <footer className="mt-auto flex gap-4">
        <label className="btn-text cursor-pointer">
          <input
            type="checkbox"
            className="size-4"
            checked={compared}
            onChange={() => actions.toggleCompare(item)}
          />
          {t.compare}
          <span className="sr-only"> {text.name}</span>
        </label>
        <button className="btn-text" disabled={favourite} onClick={() => actions.addFavourite(item)}>
          <Icon name="star" filled={favourite} />
          {favourite ? t.favourite : t.saveFavourite}
          <span className="sr-only">: {text.name}</span>
        </button>
      </footer>
    </article>
  );
}
