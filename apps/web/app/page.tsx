const services = [
  {
    name: "Reconciliation engine",
    detail: "Deterministic mortgage and escrow calculations",
  },
  {
    name: "Investigation service",
    detail: "Evidence-aware document processing and analysis",
  },
  {
    name: "Audit workspace",
    detail: "A clear path from payment change to source page",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen px-6 py-10 sm:px-10 lg:px-16">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-6xl flex-col justify-between">
        <nav className="flex items-center justify-between" aria-label="Primary navigation">
          <span className="font-semibold tracking-[-0.03em] text-slate-950">ServicerSwitch</span>
          <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800">
            Foundation online
          </span>
        </nav>

        <section className="py-20 sm:py-28">
          <p className="mb-5 text-sm font-semibold uppercase tracking-[0.18em] text-cyan-700">
            Mortgage transfer auditing
          </p>
          <h1 className="max-w-4xl text-5xl font-semibold tracking-[-0.055em] text-balance text-slate-950 sm:text-7xl">
            Trace every payment change back to the page that explains it.
          </h1>
          <p className="mt-7 max-w-2xl text-lg leading-8 text-slate-600">
            ServicerSwitch is being built around a deterministic financial core, a constrained
            investigator, and evidence that stays attached to every finding.
          </p>

          <div className="mt-12 grid gap-4 md:grid-cols-3">
            {services.map((service, index) => (
              <article
                className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-[0_18px_60px_-35px_rgba(15,23,42,0.35)]"
                key={service.name}
              >
                <span className="text-xs font-semibold text-cyan-700">0{index + 1}</span>
                <h2 className="mt-5 font-semibold text-slate-950">{service.name}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">{service.detail}</p>
              </article>
            ))}
          </div>
        </section>

        <footer className="flex flex-col gap-2 border-t border-slate-200 py-6 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <span>C1 service foundation</span>
          <span>Audit information, not legal advice.</span>
        </footer>
      </div>
    </main>
  );
}
