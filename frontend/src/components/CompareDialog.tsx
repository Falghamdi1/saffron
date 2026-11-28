import { useEffect, useRef, useState } from "react";
import type { Api } from "../api";
import { useLanguage } from "../i18n";
import type { MenuItem } from "../types";
import CompareTable from "./CompareTable";

interface Props {
  api: Api;
  items: MenuItem[];
  onClose: () => void;
}

export default function CompareDialog({ api, items, onClose }: Props) {
  const { t } = useLanguage();
  const dialog = useRef<HTMLDialogElement>(null);
  const [violations, setViolations] = useState<string[][]>();
  const [unchecked, setUnchecked] = useState(false);

  // Ask the server, so suitability reflects the diner's current requirements.
  useEffect(() => {
    api
      .menu()
      .then((menu) =>
        setViolations(items.map((item) => menu.find((e) => e.id === item.id)?.violations ?? [])),
      )
      .catch(() => setUnchecked(true));
  }, [api, items]);

  useEffect(() => {
    dialog.current?.showModal();
  }, []);

  return (
    <dialog
      ref={dialog}
      onClose={onClose}
      aria-labelledby="compare-title"
      className="bg-paper text-ink rounded-panel m-auto max-h-[85dvh] w-[min(52rem,96vw)] overscroll-contain p-2 backdrop:bg-black/50 sm:p-5"
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 id="compare-title" className="font-display text-xl font-semibold">
          {t.sideBySide}
        </h2>
        <button className="btn btn-quiet" onClick={() => dialog.current?.close()}>
          {t.close}
        </button>
      </div>
      {unchecked && (
        <p role="alert" className="text-alert mb-2 text-sm">
          {t.unchecked}
        </p>
      )}
      <CompareTable items={items} violations={violations} />
    </dialog>
  );
}
