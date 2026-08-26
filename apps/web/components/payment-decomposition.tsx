import type { PaymentRow } from "@/lib/demo-data";

export function PaymentDecomposition({ rows }: { rows: PaymentRow[] }) {
  return (
    <section className="overflow-hidden rounded-[1.4rem] border border-slate-200 bg-white" aria-labelledby="payment-heading">
      <div className="flex items-start justify-between border-b border-slate-200 px-5 py-5 sm:px-6">
        <div>
          <p className="eyebrow">Deterministic calculation</p>
          <h2 className="mt-1 text-xl font-semibold tracking-[-0.03em] text-slate-950" id="payment-heading">
            Payment change decomposition
          </h2>
        </div>
        <span className="trust-chip">No AI arithmetic</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[36rem] border-collapse text-sm">
          <thead>
            <tr className="bg-slate-50 text-left text-xs uppercase tracking-[0.12em] text-slate-500">
              <th className="px-6 py-3 font-semibold">Component</th>
              <th className="px-4 py-3 text-right font-semibold">Before</th>
              <th className="px-4 py-3 text-right font-semibold">After</th>
              <th className="px-6 py-3 text-right font-semibold">Change</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                className={row.emphasized ? "bg-amber-50/70" : "border-t border-slate-100"}
                key={row.label}
              >
                <th className="px-6 py-4 text-left font-medium text-slate-800" scope="row">
                  {row.label}
                </th>
                <td className="px-4 py-4 text-right tabular-nums text-slate-600">{row.before}</td>
                <td className="px-4 py-4 text-right tabular-nums text-slate-950">{row.after}</td>
                <td
                  className={`px-6 py-4 text-right font-semibold tabular-nums ${
                    row.change.startsWith("+") ? "text-amber-700" : "text-slate-500"
                  }`}
                >
                  {row.change}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
