"use client";

import type { DemoScenario } from "@/lib/demo-data";
import { auditSteps } from "@/lib/demo-data";

import { AppHeader } from "./app-header";
import { CheckIcon, DocumentIcon, ShieldIcon } from "./icons";

export function ProcessingTimeline({
  scenario,
  activeStep,
  files,
  onSkip,
}: {
  scenario: DemoScenario;
  activeStep: number;
  files: File[];
  onSkip: () => void;
}) {
  const progress = Math.min(100, Math.round(((activeStep + 1) / auditSteps.length) * 100));

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <AppHeader compact inverted />
      <div className="mx-auto grid min-h-[calc(100vh-5rem)] max-w-6xl items-center gap-12 px-5 py-10 sm:px-8 lg:grid-cols-[0.72fr_1.28fr]">
        <section>
          <p className="text-xs font-bold uppercase tracking-[0.17em] text-cyan-300">Audit in progress</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-[-0.055em] text-balance sm:text-5xl">
            Building an evidence trail, not a chain of thought.
          </h1>
          <p className="mt-5 max-w-lg text-base leading-7 text-slate-400">
            You see the workflow and source checks. Private model reasoning is never exposed.
          </p>

          <div className="mt-8 rounded-2xl border border-white/10 bg-white/[0.045] p-5">
            <div className="flex items-center gap-3">
              <span className="grid size-10 place-items-center rounded-xl bg-cyan-300/10 text-cyan-300">
                <DocumentIcon className="size-5" />
              </span>
              <div>
                <p className="text-sm font-bold">{files.length ? "Custom upload" : scenario.title}</p>
                <p className="text-xs text-slate-400">
                  {files.length ? `${files.length} local PDFs` : `${scenario.caseId} · ${scenario.accountId}`}
                </p>
              </div>
            </div>
            <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-white/10" aria-label={`${progress}% complete`} role="progressbar" aria-valuemax={100} aria-valuemin={0} aria-valuenow={progress}>
              <div className="h-full rounded-full bg-cyan-300 transition-[width] duration-500" style={{ width: `${progress}%` }} />
            </div>
            <div className="mt-2 flex justify-between text-[0.68rem] font-semibold text-slate-500">
              <span>{progress}% complete</span>
              <span>7 bounded stages</span>
            </div>
          </div>

          <button className="mt-6 text-sm font-semibold text-slate-400 underline decoration-slate-600 underline-offset-4 hover:text-white" onClick={onSkip} type="button">
            View completed demo now
          </button>
        </section>

        <section className="relative overflow-hidden rounded-[1.7rem] border border-white/10 bg-white/[0.045] p-5 sm:p-7" aria-label="Audit workflow status">
          <div className="pointer-events-none absolute -right-20 -top-20 size-72 rounded-full bg-cyan-400/10 blur-3xl" />
          <ol className="relative space-y-2">
            {auditSteps.map((step, index) => {
              const complete = index < activeStep;
              const active = index === activeStep;
              return (
                <li className={`grid grid-cols-[2.5rem_1fr_auto] items-center gap-3 rounded-xl border px-3 py-3.5 transition ${active ? "border-cyan-300/40 bg-cyan-300/10" : "border-transparent"}`} key={step.label}>
                  <span className={`grid size-8 place-items-center rounded-full text-xs font-bold ${complete ? "bg-emerald-400 text-emerald-950" : active ? "bg-cyan-300 text-cyan-950" : "bg-white/10 text-slate-500"}`}>
                    {complete ? <CheckIcon className="size-4" /> : index + 1}
                  </span>
                  <span>
                    <span className={`block text-sm font-bold ${complete || active ? "text-white" : "text-slate-500"}`}>{step.label}</span>
                    <span className={`mt-0.5 block text-xs ${active ? "text-cyan-100/70" : "text-slate-500"}`}>{step.detail}</span>
                  </span>
                  {active && <span className="flex items-center gap-1.5 text-[0.68rem] font-bold uppercase tracking-[0.12em] text-cyan-300"><span className="processing-dot" />Running</span>}
                  {complete && <span className="text-[0.68rem] font-bold uppercase tracking-[0.12em] text-emerald-300">Done</span>}
                </li>
              );
            })}
          </ol>
          <p className="relative mt-5 flex items-center gap-2 border-t border-white/10 pt-5 text-xs text-slate-500">
            <ShieldIcon className="size-4 text-cyan-300" />
            Documents stay untrusted throughout the workflow.
          </p>
        </section>
      </div>
    </main>
  );
}
