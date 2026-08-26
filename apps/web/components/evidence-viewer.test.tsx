import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { scenarios } from "@/lib/demo-data";

import { EvidenceViewer } from "./evidence-viewer";

describe("EvidenceViewer", () => {
  it("renders the cited PDF page and switches the highlighted source", () => {
    const evidence = scenarios[0].findings[0].evidence;
    render(<EvidenceViewer evidence={evidence} />);

    expect(screen.getByText("Page 1 · Annual Amount Due")).toBeInTheDocument();
    expect(screen.getByLabelText("Highlighted evidence: $11,552.00")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Annual escrow analysis" }));

    expect(screen.getByText("Page 1 · Projected Annual Property Tax")).toBeInTheDocument();
    expect(screen.getByLabelText("Highlighted evidence: $12,165.17")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open original PDF/i })).toHaveAttribute(
      "href",
      "/demo/case-0042-escrow-analysis.pdf",
    );
  });
});
