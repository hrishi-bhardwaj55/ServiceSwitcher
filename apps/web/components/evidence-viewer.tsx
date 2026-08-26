"use client";

import { useState } from "react";

import type { Evidence } from "@/lib/demo-data";

import { DocumentIcon, ExternalIcon } from "./icons";

export function EvidenceViewer({ evidence }: { evidence: Evidence[] }) {
  const [selectedId, setSelectedId] = useState(evidence[0]?.id ?? "");
  const selected = evidence.find((item) => item.id === selectedId) ?? evidence[0];

  if (!selected) {
    return null;
  }

  return (
    <section className="overflow-hidden rounded-[1.4rem] border border-slate-200 bg-white" aria-labelledby="evidence-heading">
      <div className="border-b border-slate-200 px-5 py-5 sm:px-6">
        <p className="eyebrow">Source document</p>
        <div className="mt-1 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold tracking-[-0.03em] text-slate-950" id="evidence-heading">
            Evidence viewer
          </h2>
          <a
            className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-800 hover:text-cyan-950"
            href={selected.sourceUrl}
            rel="noreferrer"
            target="_blank"
          >
            Open original PDF
            <ExternalIcon className="size-4" />
          </a>
        </div>
        <div className="mt-4 flex gap-2 overflow-x-auto pb-1" role="tablist" aria-label="Evidence documents">
          {evidence.map((item) => (
            <button
              aria-selected={selected.id === item.id}
              className={`shrink-0 rounded-full border px-3 py-2 text-left text-xs font-semibold transition ${
                selected.id === item.id
                  ? "border-cyan-800 bg-cyan-950 text-white"
                  : "border-slate-200 bg-white text-slate-600 hover:border-slate-400"
              }`}
              key={item.id}
              onClick={() => setSelectedId(item.id)}
              role="tab"
              type="button"
            >
              {item.document}
            </button>
          ))}
        </div>
      </div>

      <div className="grid bg-[#ebe8df] lg:grid-cols-[minmax(0,1fr)_16rem]">
        <div className="p-4 sm:p-6">
          <div className="relative mx-auto max-w-[42rem] overflow-hidden rounded-sm bg-white shadow-[0_18px_55px_-26px_rgba(15,23,42,0.55)]">
            {/* This PNG is rendered from the checked-in source PDF at 2x resolution. */}
            <img
              alt={`${selected.document}, page ${selected.page}`}
              className="block h-auto w-full"
              src={selected.imageUrl}
            />
            <span
              aria-label={`Highlighted evidence: ${selected.value}`}
              className="evidence-highlight"
              style={{
                height: `${selected.highlight.height}%`,
                left: `${selected.highlight.left}%`,
                top: `${selected.highlight.top}%`,
                width: `${selected.highlight.width}%`,
              }}
            />
          </div>
        </div>
        <aside className="border-t border-slate-300/70 bg-white p-5 lg:border-l lg:border-t-0">
          <span className="inline-flex size-9 items-center justify-center rounded-lg bg-cyan-50 text-cyan-800">
            <DocumentIcon className="size-5" />
          </span>
          <p className="mt-5 text-xs font-semibold uppercase tracking-[0.13em] text-slate-500">
            Page {selected.page} · {selected.field}
          </p>
          <p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-slate-950">{selected.value}</p>
          <p className="mt-4 text-sm leading-6 text-slate-600">
            The highlighted rectangle comes from the extractor&apos;s page-level bounding box, not a model-generated citation.
          </p>
        </aside>
      </div>
    </section>
  );
}
