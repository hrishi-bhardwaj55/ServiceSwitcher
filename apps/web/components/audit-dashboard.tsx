"use client";

import type { DemoScenario, Finding } from "@/lib/demo-data";

import { AppHeader } from "./app-header";
import { AlertIcon, ArrowLeftIcon, ArrowRightIcon, CheckIcon, DocumentIcon, ShieldIcon } from "./icons";
import { PaymentDecomposition } from "./payment-decomposition";

const severityStyle = {
  High: "bg-red-100 text-red-800",
  Medium: "bg-amber-100 text-amber-800",
  Low: "bg-slate-100 text-slate-700",
};

export function AuditDashboard({
  scenario,
  customFiles,
  onOpenFinding,
  onRestart,
}: {
  scenario: DemoScenario;
  customFiles: File[];
  onOpenFinding: (finding: Finding) => void;
  onRestart: () => void;
}) {
  const custom = customFiles.length > 0;
  const clear = scenario.findings.length === 0;

  return (
    <main className="min-h-screen">
      <AppHeader compact />
      <div className="border-y border-slate-200 bg-white/70">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-3 text-xs sm:px-8">
          <div className="flex min-w-0 items-center gap-2 text-slate-500">
            <span>Audits</span><span>/</span>
            <span className="truncate font-semibold text-slate-800">{custom ? "Local upload preview" : scenario.caseId}</span>
          </div>
          <span className="flex items-center gap-1.5 font-semibold text-emerald-700"><CheckIcon className="size-4" />Audit complete</span>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 sm:py-10">
        <button className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-slate-950" onClick={onRestart} type="button">
          <ArrowLeftIcon className="size-4" />New audit
        </button>

        <section className="mt-6 overflow-hidden rounded-[1.7rem] bg-cyan-950 text-white shadow-[0_28px_70px_-42px_rgba(8,51,68,0.8)]">
          <div className="grid lg:grid-cols-[1fr_auto]">
            <div className="p-6 sm:p-8 lg:p-10">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full px-3 py-1 text-xs font-bold ${clear ? "bg-emerald-300 text-emerald-950" : "bg-red-200 text-red-950"}`}>
                  {scenario.status === "Finding" ? "Review recommended" : scenario.status}
                </span>
                <span className="text-xs font-semibold text-cyan-200">{custom ? `${customFiles.length} local PDFs` : `${scenario.caseId} · ${scenario.accountId}`}</span>
              </div>
              <h1 className="mt-5 max-w-3xl text-3xl font-semibold tracking-[-0.05em] text-balance sm:text-5xl">
                {clear ? "No unsupported servicing discrepancy found." : scenario.findings[0]?.title}
              </h1>
              <p className="mt-4 max-w-2xl text-base leading-7 text-cyan-50/70">{scenario.note}</p>
              {custom && (
                <p className="mt-4 rounded-xl border border-amber-300/25 bg-amber-200/10 px-4 py-3 text-sm text-amber-100">
                  Custom files remain local in this UI preview. The displayed result uses the selected measured scenario and is not an analysis of your upload.
                </p>
              )}
            </div>
            <div className="grid min-w-[20rem] grid-cols-2 border-t border-white/10 bg-white/[0.045] lg:border-l lg:border-t-0">
              <Metric label="Potential impact" value={scenario.totalImpact} />
              <Metric label="Monthly change" value={scenario.monthlyChange} />
              <Metric label="High severity" value={String(scenario.highSeverity)} />
              <Metric label="Documents checked" value={String(custom ? customFiles.length : scenario.documents)} />
            </div>
          </div>
        </section>

        <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="space-y-6">
            <PaymentDecomposition rows={scenario.paymentRows} />

            <section className="rounded-[1.4rem] border border-slate-200 bg-white p-5 sm:p-6" aria-labelledby="findings-heading">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="eyebrow">Audit result</p>
                  <h2 className="mt-1 text-xl font-semibold tracking-[-0.03em] text-slate-950" id="findings-heading">Findings</h2>
                </div>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">{scenario.findings.length}</span>
              </div>

              {scenario.findings.length ? (
                <div className="mt-5 space-y-3">
                  {scenario.findings.map((finding) => (
                    <button className="group grid w-full gap-4 rounded-2xl border border-slate-200 p-4 text-left transition hover:border-cyan-800 hover:shadow-sm sm:grid-cols-[auto_1fr_auto] sm:items-center" key={finding.id} onClick={() => onOpenFinding(finding)} type="button">
                      <span className="grid size-11 place-items-center rounded-xl bg-red-50 text-red-700"><AlertIcon className="size-5" /></span>
                      <span>
                        <span className="flex flex-wrap items-center gap-2">
                          <span className={`rounded-full px-2.5 py-1 text-[0.68rem] font-bold ${severityStyle[finding.severity]}`}>{finding.severity}</span>
                          <span className="font-mono text-[0.66rem] text-slate-400">{finding.type}</span>
                        </span>
                        <span className="mt-2 block font-bold text-slate-950">{finding.title}</span>
                        <span className="mt-1 block text-sm leading-6 text-slate-500">{finding.summary}</span>
                      </span>
                      <span className="flex items-center justify-between gap-5 sm:block sm:text-right">
                        <span className="block text-lg font-bold text-amber-700">{finding.monthlyImpact}</span>
                        <span className="mt-2 inline-flex items-center gap-1 text-xs font-bold text-cyan-800">Open evidence <ArrowRightIcon className="size-3.5 transition-transform group-hover:translate-x-0.5" /></span>
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="mt-5 flex gap-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
                  <span className="grid size-10 shrink-0 place-items-center rounded-full bg-emerald-200 text-emerald-800"><CheckIcon className="size-5" /></span>
                  <div><p className="font-bold text-emerald-950">No discrepancy findings</p><p className="mt-1 text-sm leading-6 text-emerald-800">Balances and payment components reconcile within the deterministic tolerance.</p></div>
                </div>
              )}
            </section>
          </div>

          <aside className="space-y-5">
            <section className="rounded-[1.4rem] border border-slate-200 bg-white p-5">
              <p className="eyebrow">Trust record</p>
              <h2 className="mt-1 text-lg font-semibold tracking-[-0.03em] text-slate-950">What ran</h2>
              <ol className="mt-5 space-y-4">
                {[
                  [ShieldIcon, "Deterministic engine", "5 checks completed"],
                  [DocumentIcon, "Evidence validation", `${scenario.documents} documents cited`],
                  [CheckIcon, "Bounded investigator", "Within cost and tool limits"],
                ].map(([Icon, label, detail]) => {
                  const ItemIcon = Icon as typeof ShieldIcon;
                  return <li className="flex gap-3" key={String(label)}><span className="grid size-8 shrink-0 place-items-center rounded-lg bg-slate-100 text-slate-700"><ItemIcon className="size-4" /></span><span><span className="block text-sm font-bold text-slate-800">{String(label)}</span><span className="mt-0.5 block text-xs text-slate-500">{String(detail)}</span></span></li>;
                })}
              </ol>
            </section>
            <section className="rounded-[1.4rem] bg-amber-50 p-5 ring-1 ring-inset ring-amber-200">
              <p className="text-xs font-bold uppercase tracking-[0.13em] text-amber-800">Scope</p>
              <p className="mt-3 text-sm leading-6 text-amber-950">This audit flags account evidence for review. It is not a legal conclusion or a replacement for your servicer&apos;s records.</p>
            </section>
          </aside>
        </div>
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="border-b border-r border-white/10 p-5 sm:p-6"><p className="text-[0.68rem] font-bold uppercase tracking-[0.13em] text-cyan-200/60">{label}</p><p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-white">{value}</p></div>;
}
