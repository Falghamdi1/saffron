import { label, price, SPICE_NAMES } from "../format";
import type { MenuItem } from "../types";
import type { DishActions } from "./Workspace";

interface Props {
  item: MenuItem;
  actions: DishActions;
  reasons?: string[];
  cautions?: string[];
  violations?: string[];
}

const DIET_LABELS = ["vegan", "vegetarian", "gluten_free", "dairy_free"];

export function Spice({ level }: { level: number }) {
  return (
    <span className="flex items-center gap-1" title={SPICE_NAMES[level]}>
      <span aria-hidden className="flex gap-0.5">
        {[1, 2, 3].map((step) => (
          <span
            key={step}
            className={`h-2.5 w-1.5 rounded-full ${step <= level ? "bg-ember" : "bg-line"}`}
          />
        ))}
      </span>
      {SPICE_NAMES[level]}
    </span>
  );
}

export default function DishCard({ item, actions, reasons, cautions = [], violations = [] }: Props) {
  const compared = actions.compared.some((c) => c.id === item.id);
  const favourite = actions.favourites.has(item.id);
  const diets = item.diets.filter((diet) => DIET_LABELS.includes(diet));

  return (
    <article
      className={`bg-card flex flex-col gap-2 rounded-2xl border p-4 ${
        violations.length ? "border-alert/40" : "border-line"
      }`}
    >
      <header className="flex items-baseline justify-between gap-3">
        <h3 className="font-display text-lg leading-snug">{item.name}</h3>
        <p className="text-pine shrink-0 font-semibold">{price(item.price)}</p>
      </header>
      <div className="text-muted flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
        <Spice level={item.spice_level} />
        {diets.map((diet) => (
          <span key={diet} className="text-herb font-medium capitalize">
            {label(diet)}
          </span>
        ))}
      </div>
      <p className="text-sm">{item.description}</p>
      <dl className="text-xs leading-relaxed">
        <div>
          <dt className="inline font-semibold">Ingredients: </dt>
          <dd className="text-muted inline">{item.ingredients.join(", ")}</dd>
        </div>
        <div>
          <dt className="inline font-semibold">Allergens: </dt>
          <dd className="text-muted inline">
            {item.allergen_info_complete
              ? item.allergens.map(label).join(", ") || "none recorded"
              : "information incomplete, ask staff"}
            {item.may_contain.length > 0 && ` · may contain ${item.may_contain.map(label).join(", ")}`}
          </dd>
        </div>
      </dl>

      {reasons && reasons.length > 0 && (
        <div className="bg-herb-soft rounded-xl px-3 py-2">
          <p className="eyebrow text-herb">Why this dish</p>
          <ul className="mt-0.5 text-xs">
            {reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      )}
      {[...cautions, ...(violations.length ? [`Not for you: ${violations.join("; ")}`] : [])].map(
        (warning) => (
          <p key={warning} className="bg-alert-soft text-alert rounded-xl px-3 py-2 text-xs">
            {warning}
          </p>
        ),
      )}

      <footer className="mt-auto flex gap-2 pt-1 text-xs">
        <button
          className="btn btn-quiet px-3 py-1.5 text-xs"
          aria-pressed={compared}
          onClick={() => actions.toggleCompare(item)}
        >
          {compared ? "Added to compare" : "Compare"}
        </button>
        <button
          className="btn btn-quiet px-3 py-1.5 text-xs"
          disabled={favourite}
          onClick={() => actions.addFavourite(item)}
        >
          {favourite ? "★ Favourite" : "☆ Save favourite"}
        </button>
      </footer>
    </article>
  );
}
