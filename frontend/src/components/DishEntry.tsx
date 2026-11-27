import { label, price, SPICE_NAMES } from "../format";
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
  return (
    <span className="inline-flex items-center gap-1.5">
      <span aria-hidden="true" className="inline-flex gap-0.5">
        {[1, 2, 3].map((step) => (
          <span key={step} className={`h-3 w-1 ${step <= level ? "bg-ember" : "bg-line"}`} />
        ))}
      </span>
      {SPICE_NAMES[level]}
    </span>
  );
}

/** A dish as it would be set on a printed menu: name, leader, price, then the facts. */
export default function DishEntry({ item, actions, reasons, cautions = [], violations = [] }: Props) {
  const compared = actions.compared.some((c) => c.id === item.id);
  const favourite = actions.favourites.has(item.id);
  const diets = item.diets.filter((diet) => DIET_LABELS.includes(diet));
  const allergens = item.allergen_info_complete
    ? item.allergens.map(label).join(", ") || "none recorded"
    : "information incomplete, ask staff";

  return (
    <article className="flex min-w-0 flex-1 flex-col gap-1.5">
      <header className="flex items-baseline gap-2">
        <h3 className="font-display min-w-0 text-lg leading-snug font-semibold">{item.name}</h3>
        <span aria-hidden="true" className="border-line-strong min-w-4 flex-1 border-b border-dotted" />
        <p className="shrink-0 font-semibold tabular-nums">{price(item.price)}</p>
      </header>
      <p className="text-sm">{item.description}</p>
      <p className="text-muted flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px]">
        <Spice level={item.spice_level} />
        {diets.map((diet) => (
          <span key={diet} className="text-herb font-medium capitalize">
            {label(diet)}
          </span>
        ))}
      </p>
      <p className="text-muted text-[13px] leading-relaxed">{item.ingredients.join(", ")}</p>
      {/* Allergens are safety information, so they are set larger and darker than the rest. */}
      <p className="text-sm">
        <span className="font-semibold">Allergens:</span> {allergens}
        {item.may_contain.length > 0 && `; may contain ${item.may_contain.map(label).join(", ")}`}
      </p>

      {reasons && reasons.length > 0 && (
        <ul className="text-herb mt-0.5 space-y-0.5 text-[13px]" aria-label="Why this dish">
          {reasons.map((reason) => (
            <li key={reason} className="flex gap-1.5">
              <Icon name="check" className="mt-0.5 size-3.5" />
              {reason}
            </li>
          ))}
        </ul>
      )}
      {[...cautions, ...(violations.length ? [`Not for you: ${violations.join("; ")}`] : [])].map(
        (warning) => (
          <p key={warning} className="text-alert flex gap-1.5 text-sm font-medium">
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
          Compare<span className="sr-only"> {item.name}</span>
        </label>
        <button className="btn-text" disabled={favourite} onClick={() => actions.addFavourite(item)}>
          <Icon name="star" filled={favourite} />
          {favourite ? "Favourite" : "Save as favourite"}
          <span className="sr-only">: {item.name}</span>
        </button>
      </footer>
    </article>
  );
}
