import { useEffect, useRef } from "react";
import type { MenuItem } from "../types";
import CompareTable from "./CompareTable";

export default function CompareDialog({ items, onClose }: { items: MenuItem[]; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    dialog.current?.showModal();
  }, []);

  return (
    <dialog
      ref={dialog}
      onClose={onClose}
      aria-label="Dish comparison"
      className="bg-paper text-ink m-auto max-h-[85dvh] w-[min(56rem,94vw)] rounded-2xl p-4 backdrop:bg-black/50"
    >
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-display text-xl">Side by side</h2>
        <button className="btn btn-quiet" onClick={() => dialog.current?.close()}>
          Close
        </button>
      </div>
      <CompareTable items={items} />
    </dialog>
  );
}
