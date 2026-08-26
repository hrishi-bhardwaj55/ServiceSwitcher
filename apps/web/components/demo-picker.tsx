"use client";

import type { ChangeEvent } from "react";

import type { DemoScenario } from "@/lib/demo-data";

import { AppHeader } from "./app-header";
import { ArrowRightIcon, CheckIcon, LockIcon, ShieldIcon, UploadIcon } from "./icons";

type DemoPickerProps = {
  scenarios: DemoScenario[];
  selected: DemoScenario;
  files: File[];
  fileError: string;
  onSelect: (scenario: DemoScenario) => void;
  onFiles: (files: File[]) => void;
  onStart: () => void;
};

export function DemoPicker({
  scenarios,
  selected,
  files,
  fileError,
  onSelect,
  onFiles,
  onStart,
}: DemoPickerProps) {
  const handleFiles = (event: ChangeEvent<HTMLInputElement>) => {
    onFiles(Array.from(event.target.files ?? []));
  };

  return (
    <main className="min-h-screen">
      <AppHeader />
      <div className="mx-auto grid w-full max-w-7xl gap-12 px-5 pb-16 pt-8 sm:px-8 lg:grid-cols-[minmax(0,1.35fr)_minmax(20rem,0.65fr)] lg:pt-14">
        <section>
          <div className="max-w-3xl">
            <p className="eyebrow">Mortgage servicing transfer auditor</p>
            <h1 className="mt-4 max-w-3xl text-5xl font-semibold tracking-[-0.06em] text-balance text-slate-950 sm:text-6xl lg:text-[4.7rem] lg:leading-[0.98]">
              Find the line item behind a payment change.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
              Compare the old servicer, new servicer, escrow analysis, transfer notice, and tax bill—then trace every finding to its source page.
            </p>
          </div>

          <div className="mt-10">
            <div className="flex items-end justify-between gap-5">
              <div>
                <p className="text-sm font-bold text-slate-950">Choose a pre-built audit</p>
                <p className="mt-1 text-sm text-slate-500">Each scenario uses the measured 300-case corpus.</p>
              </div>
              <span className="hidden text-xs font-semibold text-slate-500 sm:block">Four paths · one minute</span>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2" role="radiogroup" aria-label="Demo scenarios">
              {scenarios.map((scenario) => {
                const active = scenario.id === selected.id && files.length === 0;
                return (
                  <button
                    aria-checked={active}
                    className={`group relative rounded-[1.25rem] border p-5 text-left transition duration-200 ${
                      active
                        ? "border-cyan-900 bg-cyan-950 text-white shadow-[0_22px_55px_-32px_rgba(8,51,68,0.8)]"
                        : "border-slate-200 bg-white hover:-translate-y-0.5 hover:border-slate-400"
                    }`}
                    key={scenario.id}
                    onClick={() => onSelect(scenario)}
                    role="radio"
                    type="button"
                  >
                    <span className={`text-[0.68rem] font-bold uppercase tracking-[0.15em] ${active ? "text-cyan-200" : "text-cyan-800"}`}>
                      {scenario.eyebrow}
                    </span>
                    <span className="mt-2 flex items-start justify-between gap-3">
                      <span>
                        <span className={`block text-base font-bold ${active ? "text-white" : "text-slate-950"}`}>
                          {scenario.title}
                        </span>
                        <span className={`mt-1.5 block text-sm leading-5 ${active ? "text-cyan-100/80" : "text-slate-500"}`}>
                          {scenario.description}
                        </span>
                      </span>
                      <span className={`grid size-6 shrink-0 place-items-center rounded-full border ${active ? "border-cyan-300 bg-cyan-200 text-cyan-950" : "border-slate-300 text-transparent"}`}>
                        <CheckIcon className="size-3.5" />
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="my-7 flex items-center gap-4 text-xs font-semibold uppercase tracking-[0.13em] text-slate-400">
            <span className="h-px flex-1 bg-slate-200" />
            or bring your own
            <span className="h-px flex-1 bg-slate-200" />
          </div>

          <label className={`block cursor-pointer rounded-[1.25rem] border border-dashed p-5 transition ${files.length ? "border-cyan-700 bg-cyan-50" : "border-slate-300 bg-white hover:border-cyan-700 hover:bg-cyan-50/40"}`} htmlFor="audit-upload">
            <input
              accept="application/pdf,.pdf"
              className="sr-only"
              id="audit-upload"
              multiple
              onChange={handleFiles}
              type="file"
            />
            <span className="flex items-center gap-4">
              <span className="grid size-11 shrink-0 place-items-center rounded-xl border border-slate-200 bg-white text-cyan-900 shadow-sm">
                <UploadIcon className="size-5" />
              </span>
              <span>
                <span className="block text-sm font-bold text-slate-950">
                  {files.length ? `${files.length} PDF${files.length === 1 ? "" : "s"} selected` : "Choose up to five PDF documents"}
                </span>
                <span className="mt-1 block text-xs leading-5 text-slate-500">
                  Processed in memory for this session and never stored. PDF only, 10 MB each.
                </span>
              </span>
            </span>
            {files.length > 0 && (
              <span className="mt-4 flex flex-wrap gap-2">
                {files.map((file) => (
                  <span className="max-w-full truncate rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-600" key={`${file.name}-${file.size}`}>
                    {file.name}
                  </span>
                ))}
              </span>
            )}
          </label>
          {fileError && <p className="mt-2 text-sm font-semibold text-red-700" role="alert">{fileError}</p>}

          <div className="mt-6 flex flex-col gap-4 sm:flex-row sm:items-center">
            <button className="primary-button group" onClick={onStart} type="button">
              Start audit
              <ArrowRightIcon className="size-4 transition-transform group-hover:translate-x-0.5" />
            </button>
            <p className="flex items-center gap-2 text-xs leading-5 text-slate-500">
              <LockIcon className="size-4 text-emerald-700" />
              Audit information only—not legal advice.
            </p>
          </div>
        </section>

        <aside className="lg:pt-8">
          <div className="sticky top-8 overflow-hidden rounded-[1.7rem] border border-slate-200 bg-slate-950 text-white shadow-[0_30px_80px_-44px_rgba(15,23,42,0.85)]">
            <div className="border-b border-white/10 p-6 sm:p-7">
              <span className="grid size-11 place-items-center rounded-xl bg-white/10 text-cyan-200">
                <ShieldIcon className="size-6" />
              </span>
              <p className="mt-6 text-xs font-bold uppercase tracking-[0.16em] text-cyan-300">Why the result is defensible</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em]">Math first. Model second. Evidence always.</h2>
            </div>
            <ol className="divide-y divide-white/10">
              {[
                ["01", "Deterministic reconciliation", "Money and payment math never rely on a language model."],
                ["02", "Bounded investigation", "Eight audit-scoped tools; no arbitrary SQL, files, or URLs."],
                ["03", "Page-level provenance", "Each claim names the document, page, field, and value."],
              ].map(([number, title, detail]) => (
                <li className="grid grid-cols-[2.25rem_1fr] gap-3 p-6 sm:p-7" key={number}>
                  <span className="font-mono text-xs font-bold text-cyan-300">{number}</span>
                  <span>
                    <span className="block text-sm font-bold text-white">{title}</span>
                    <span className="mt-1 block text-sm leading-6 text-slate-400">{detail}</span>
                  </span>
                </li>
              ))}
            </ol>
            <div className="grid grid-cols-3 border-t border-white/10 bg-white/[0.04] px-6 py-5 text-center">
              <div><strong className="block text-lg">100%</strong><span className="text-[0.65rem] text-slate-400">finding F1</span></div>
              <div className="border-x border-white/10"><strong className="block text-lg">0%</strong><span className="text-[0.65rem] text-slate-400">clean FPR</span></div>
              <div><strong className="block text-lg">0/12</strong><span className="text-[0.65rem] text-slate-400">injections</span></div>
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}
