import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { scenarios } from "@/lib/demo-data";

import { PaymentDecomposition } from "./payment-decomposition";

describe("PaymentDecomposition", () => {
  it("shows the before, after, and deterministic monthly delta", () => {
    render(<PaymentDecomposition rows={scenarios[0].paymentRows} />);

    const taxRow = screen.getByRole("row", { name: /Property tax reserve/i });
    expect(within(taxRow).getByText("$962.67")).toBeInTheDocument();
    expect(within(taxRow).getByText("$1,013.77")).toBeInTheDocument();
    expect(within(taxRow).getByText("+$51.10")).toBeInTheDocument();

    const totalRow = screen.getByRole("row", { name: /Total monthly payment/i });
    expect(within(totalRow).getByText("$2,681.53")).toBeInTheDocument();
    expect(within(totalRow).getByText("$2,732.63")).toBeInTheDocument();
  });
});
