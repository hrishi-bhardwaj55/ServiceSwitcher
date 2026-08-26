export type Severity = "High" | "Medium" | "Low";

export type Evidence = {
  id: string;
  document: string;
  page: number;
  field: string;
  value: string;
  sourceUrl: string;
  imageUrl: string;
  highlight: { left: number; top: number; width: number; height: number };
};

export type Finding = {
  id: string;
  type: string;
  title: string;
  severity: Severity;
  summary: string;
  actualValue: string;
  servicerValue: string;
  difference: string;
  monthlyImpact: string;
  explanation: string;
  evidence: Evidence[];
  guidance: { label: string; section: string; url: string; summary: string }[];
  actionDraft: string;
};

export type PaymentRow = {
  label: string;
  before: string;
  after: string;
  change: string;
  emphasized?: boolean;
};

export type DemoScenario = {
  id: "clean" | "tax" | "escrow" | "reassessment";
  eyebrow: string;
  title: string;
  description: string;
  caseId: string;
  accountId: string;
  status: "Clear" | "Finding" | "Explained";
  totalImpact: string;
  monthlyChange: string;
  highSeverity: number;
  documents: number;
  paymentRows: PaymentRow[];
  findings: Finding[];
  note: string;
};

const taxEvidence: Evidence[] = [
  {
    id: "tax-bill",
    document: "2025 property tax bill",
    page: 1,
    field: "Annual Amount Due",
    value: "$11,552.00",
    sourceUrl: "/demo/case-0042-property-tax-bill.pdf",
    imageUrl: "/demo/case-0042-property-tax-bill-page-1.png",
    highlight: { left: 82.7, top: 25.8, width: 9.3, height: 2.2 },
  },
  {
    id: "escrow-analysis",
    document: "Annual escrow analysis",
    page: 1,
    field: "Projected Annual Property Tax",
    value: "$12,165.17",
    sourceUrl: "/demo/case-0042-escrow-analysis.pdf",
    imageUrl: "/demo/case-0042-escrow-analysis-page-1.png",
    highlight: { left: 82.7, top: 28.9, width: 9.3, height: 2.2 },
  },
];

const taxFinding: Finding = {
  id: "finding-tax-projection",
  type: "PROPERTY_TAX_PROJECTION_MISMATCH",
  title: "Tax projection is $613.17 above the county bill",
  severity: "High",
  summary:
    "The new servicer used $12,165.17 for annual property tax while the issued bill shows $11,552.00.",
  actualValue: "$11,552.00",
  servicerValue: "$12,165.17",
  difference: "+$613.17",
  monthlyImpact: "+$51.10 / month",
  explanation:
    "The property tax bill and escrow analysis refer to the same 2025 obligation, but the servicer projection is higher. Spreading the $613.17 difference over twelve months explains the entire $51.10 payment increase.",
  evidence: taxEvidence,
  guidance: [
    {
      label: "Regulation X escrow statements",
      section: "12 CFR § 1024.17",
      url: "https://www.consumerfinance.gov/rules-policy/regulations/1024/17/",
      summary:
        "Escrow analyses must use the servicer's expected disbursements and provide an account statement showing the basis for payment changes.",
    },
    {
      label: "Servicing transfer policies",
      section: "CFPB Bulletin 2014-01",
      url: "https://files.consumerfinance.gov/f/201408_cfpb_bulletin_mortgage-servicing-transfer.pdf",
      summary:
        "Transfer controls should preserve accurate account information and prevent consumer harm from data mismatches.",
    },
  ],
  actionDraft:
    "I am requesting a written review of the annual property-tax projection used in my escrow analysis. The county tax bill lists $11,552.00, while the analysis uses $12,165.17—a difference of $613.17, or $51.10 per month. Please reconcile these figures, correct the payment if appropriate, and provide the calculation used.",
};

const taxRows: PaymentRow[] = [
  { label: "Principal & interest", before: "$1,395.95", after: "$1,395.95", change: "$0.00" },
  {
    label: "Property tax reserve",
    before: "$962.67",
    after: "$1,013.77",
    change: "+$51.10",
    emphasized: true,
  },
  { label: "Insurance reserve", before: "$322.91", after: "$322.91", change: "$0.00" },
  { label: "Shortage installment", before: "$0.00", after: "$0.00", change: "$0.00" },
  {
    label: "Total monthly payment",
    before: "$2,681.53",
    after: "$2,732.63",
    change: "+$51.10",
    emphasized: true,
  },
];

const flatRows = (total: string): PaymentRow[] => [
  { label: "Principal & interest", before: "$1,642.20", after: "$1,642.20", change: "$0.00" },
  { label: "Property tax reserve", before: "$488.00", after: "$488.00", change: "$0.00" },
  { label: "Insurance reserve", before: "$176.40", after: "$176.40", change: "$0.00" },
  { label: "Shortage installment", before: "$0.00", after: "$0.00", change: "$0.00" },
  { label: "Total monthly payment", before: total, after: total, change: "$0.00", emphasized: true },
];

export const scenarios: DemoScenario[] = [
  {
    id: "tax",
    eyebrow: "Payment increased",
    title: "Tax projection error",
    description: "A county tax bill and the new servicer's projection do not agree.",
    caseId: "CASE-0042",
    accountId: "SS-0042",
    status: "Finding",
    totalImpact: "$613.17",
    monthlyChange: "+$51.10",
    highSeverity: 1,
    documents: 5,
    paymentRows: taxRows,
    findings: [taxFinding],
    note: "One high-confidence discrepancy explains 100% of the payment increase.",
  },
  {
    id: "escrow",
    eyebrow: "Transfer continuity",
    title: "Escrow balance mismatch",
    description: "The opening balance does not match the prior servicer's final balance.",
    caseId: "CASE-0001",
    accountId: "SS-0001",
    status: "Finding",
    totalImpact: "$420.00",
    monthlyChange: "$0.00",
    highSeverity: 1,
    documents: 5,
    paymentRows: flatRows("$2,306.60"),
    findings: [
      {
        ...taxFinding,
        id: "finding-escrow-balance",
        type: "ESCROW_BALANCE_MISMATCH",
        title: "Opening escrow balance is $420.00 short",
        summary:
          "The receiving servicer's opening balance is lower than the final balance transferred by the prior servicer.",
        actualValue: "$4,280.00",
        servicerValue: "$3,860.00",
        difference: "-$420.00",
        monthlyImpact: "$0.00 / month",
        explanation:
          "No transfer adjustment or disbursement accounts for the $420.00 difference between the two consecutive statements.",
        actionDraft:
          "Please provide a transaction-level reconciliation of the $420.00 difference between the prior servicer's final escrow balance and the opening balance on my new account.",
      },
    ],
    note: "The payment is unchanged, but transferred escrow funds are not fully accounted for.",
  },
  {
    id: "clean",
    eyebrow: "No anomaly",
    title: "Clean transfer",
    description: "Balances, projections, and payment components reconcile across the transfer.",
    caseId: "CASE-0201",
    accountId: "SS-0201",
    status: "Clear",
    totalImpact: "$0.00",
    monthlyChange: "$0.00",
    highSeverity: 0,
    documents: 5,
    paymentRows: flatRows("$2,306.60"),
    findings: [],
    note: "All deterministic checks passed and no unsupported discrepancy was reported.",
  },
  {
    id: "reassessment",
    eyebrow: "Legitimate change",
    title: "Documented reassessment",
    description: "A tax increase is fully supported by the county's reassessment notice.",
    caseId: "CASE-0261",
    accountId: "SS-0261",
    status: "Explained",
    totalImpact: "$0.00 unexplained",
    monthlyChange: "+$38.25",
    highSeverity: 0,
    documents: 5,
    paymentRows: taxRows.map((row) =>
      row.label === "Property tax reserve" || row.label === "Total monthly payment"
        ? { ...row, change: "+$38.25" }
        : row,
    ),
    findings: [],
    note: "The increase is supported by the issued tax notice and needs no dispute.",
  },
];

export const auditSteps = [
  { label: "Load documents", detail: "Bind five PDFs to this audit and account" },
  { label: "Classify", detail: "Identify statement, notice, analysis, and tax bill" },
  { label: "Extract & validate", detail: "Read typed values with page-level provenance" },
  { label: "Reconcile", detail: "Run deterministic escrow and payment checks" },
  { label: "Investigate", detail: "Retrieve guidance and inspect ambiguous evidence" },
  { label: "Validate evidence", detail: "Require a document, page, field, and value" },
  { label: "Assess risk & report", detail: "Calculate impact and prepare the audit" },
];
