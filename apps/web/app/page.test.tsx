import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "./page";

describe("ServicerSwitch demo path", () => {
  it("walks from scenario picker through processing, dashboard, and evidence detail", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", {
        name: "Find the line item behind a payment change.",
      }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Start audit/i }));

    expect(
      screen.getByRole("heading", {
        name: "Building an evidence trail, not a chain of thought.",
      }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "View completed demo now" }));

    expect(
      screen.getByRole("heading", {
        name: "Tax projection is $613.17 above the county bill",
      }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Open evidence/i }));

    expect(screen.getByRole("heading", { name: "Evidence viewer" })).toBeInTheDocument();
    expect(screen.getByAltText("2025 property tax bill, page 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Highlighted evidence: $11,552.00")).toBeInTheDocument();
  });

  it("rejects more than five uploaded PDFs without starting an audit", () => {
    render(<Home />);
    const files = Array.from(
      { length: 6 },
      (_, index) => new File(["pdf"], `document-${index}.pdf`, { type: "application/pdf" }),
    );

    fireEvent.change(screen.getByLabelText(/Choose up to five PDF documents/i), {
      target: { files },
    });

    expect(screen.getByRole("alert")).toHaveTextContent("no more than five PDFs");
  });
});
