import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "./page";

describe("Home", () => {
  it("renders the service foundation and its three trust layers", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", {
        name: "Trace every payment change back to the page that explains it.",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Reconciliation engine")).toBeInTheDocument();
    expect(screen.getByText("Investigation service")).toBeInTheDocument();
    expect(screen.getByText("Audit workspace")).toBeInTheDocument();
    expect(screen.getByText("Foundation online")).toBeInTheDocument();
  });
});
