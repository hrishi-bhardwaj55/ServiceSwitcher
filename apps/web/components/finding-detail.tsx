"use client";

import { useState } from "react";

import type { DemoScenario, Finding } from "@/lib/demo-data";

import { AppHeader } from "./app-header";
import { EvidenceViewer } from "./evidence-viewer";
import { ArrowLeftIcon, CheckIcon, CopyIcon, ExternalIcon, ShieldIcon } from "./icons";

export function FindingDetail({ scenario, finding, onBack }: { scenario: DemoScenario; finding: Finding; onBack: () => void }) {
  const [draft, setDraft] = useState(finding.actionDraft);
  const [copied, setCopied] = useState(false);

  const copyDraft = async () => {
    await navigator.clipboard?.writeText(draft);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  return (
    <main className="min-h-screen">
      <AppHeader compact />
      <div className="border-y border-slate-200 bg-white/70">
        <div className="mx-auto flex max-w-7xl items-center gap-2 px-5 py-3 text-xs text-slate-500 sm:px-8">
          <span>{scenario.caseId}</span><span>/</span><span>Findings</span><span>/</span><span className="font-semibold text-slate-800">{finding.type}</span>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 sm:py-10">
        <button className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-slate-950" onClick={onBack} type="button"><ArrowLeftIcon className="size-4" />Back to dashboard</button>

        <section className="mt-6 grid gap-6 rounded-[1.7rem] border border-slate-200 bg-white p-6 sm:p-8 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-red-100 px-3 py-1 text-xs font-bold text-red-800">{finding.severity} severity</span><span className="font-mono text-xs text-slate-400">{finding.type}</span></div>
            <h1 className="mt-4 max-w-4xl text-3xl font-semibold tracking-[-0.05em] text-balance text-slate-950 sm:text-5xl">{finding.title}</h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">{finding.explanation}</p>
          </div>
          <div className="grid min-w-[17rem] grid-cols-2 overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
            <div className="border-r border-slate-200 p-4"><p className="text-[0.66rem] font-bold uppercase tracking-[0.12em] text-slate-500">Difference</p><p className="mt-2 text-xl font-bold text-amber-700">{finding.difference}</p></div>
            <div className="p-4"><p className="text-[0.66rem] font-bold uppercase tracking-[0.12em] text-slate-500">Monthly</p><p className="mt-2 text-xl font-bold text-slate-950">{finding.monthlyImpact}</p></div>
          </div>
        </section>

        <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
          <div className="space-y-6">
            <EvidenceViewer evidence={finding.evidence} />

            <section className="rounded-[1.4rem] border border-slate-200 bg-white p-5 sm:p-6" aria-labelledby="guidance-heading">
              <p className="eyebrow">Relevant guidance</p>
              <h2 className="mt-1 text-xl font-semibold tracking-[-0.03em] text-slate-950" id="guidance-heading">Why this deserves review</h2>
              <div className="mt-5 divide-y divide-slate-200">
                {finding.guidance.map((item) => (
                  <article className="py-5 first:pt-0 last:pb-0" key={item.section}>
                    <div className="flex items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[0.12em] text-cyan-800">{item.section}</p><h3 className="mt-1 font-bold text-slate-950">{item.label}</h3></div><a aria-label={`Open ${item.label}`} className="grid size-9 shrink-0 place-items-center rounded-lg border border-slate-200 text-slate-600 hover:border-cyan-800 hover:text-cyan-800" href={item.url} rel="noreferrer" target="_blank"><ExternalIcon className="size-4" /></a></div>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{item.summary}</p>
                  </article>
                ))}
              </div>
            </section>
          </div>

          <aside>
            <section className="sticky top-6 overflow-hidden rounded-[1.4rem] border border-slate-200 bg-white">
              <div className="border-b border-slate-200 p-5"><p className="eyebrow">Next action</p><h2 className="mt-1 text-xl font-semibold tracking-[-0.03em] text-slate-950">Draft a servicer request</h2><p className="mt-2 text-sm leading-6 text-slate-500">Editable text based only on the cited values. Review before sending.</p></div>
              <div className="p-5">
                <label className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500" htmlFor="action-draft">Action draft</label>
                <textarea className="mt-2 min-h-64 w-full resize-y rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm leading-6 text-slate-700 outline-none transition focus:border-cyan-800 focus:ring-2 focus:ring-cyan-100" id="action-draft" onChange={(event) => setDraft(event.target.value)} value={draft} />
                <button className="primary-button mt-4 w-full justify-center" onClick={copyDraft} type="button">{copied ? <CheckIcon className="size-4" /> : <CopyIcon className="size-4" />}{copied ? "Copied" : "Copy draft"}</button>
                <p className="mt-4 flex items-start gap-2 text-xs leading-5 text-slate-500"><ShieldIcon className="mt-0.5 size-4 shrink-0 text-cyan-800" />No message is sent automatically. You stay in control.</p>
              </div>
            </section>
          </aside>
        </div>
      </div>
    </main>
  );
}
