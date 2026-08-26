import { ShieldIcon } from "./icons";

export function AppHeader({ compact = false, inverted = false }: { compact?: boolean; inverted?: boolean }) {
  return (
    <header className={`mx-auto flex w-full max-w-7xl items-center justify-between ${compact ? "px-5 py-4 sm:px-8" : "px-5 py-6 sm:px-8"}`}>
      <div className="flex items-center gap-3">
        <span className="grid size-10 place-items-center rounded-xl bg-cyan-950 text-white shadow-sm">
          <ShieldIcon className="size-5" />
        </span>
        <div>
          <p className={`text-base font-bold tracking-[-0.035em] ${inverted ? "text-white" : "text-slate-950"}`}>ServicerSwitch</p>
          <p className={`text-[0.66rem] font-semibold uppercase tracking-[0.17em] ${inverted ? "text-slate-400" : "text-slate-500"}`}>
            Evidence-led audits
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className="hidden rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 sm:inline-flex">
          300-case evaluated
        </span>
        <span className="rounded-full bg-emerald-100 px-3 py-1.5 text-xs font-bold text-emerald-800">
          Demo ready
        </span>
      </div>
    </header>
  );
}
