import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("App", () => {
  it("shows the product name", () => {
    render(<App checkHealth={() => new Promise(() => {})} />);
    expect(screen.getByRole("heading", { name: "Smart-AP-Suite" })).toBeInTheDocument();
    expect(screen.getByTestId("api-health")).toHaveTextContent("checking");
  });

  it("shows the API health when the check finishes", async () => {
    render(<App checkHealth={() => Promise.resolve("ok")} />);
    expect(await screen.findByText("ok")).toBeInTheDocument();
  });

  it("ignores a result that arrives after unmount", async () => {
    let resolve: (value: "ok") => void = () => {};
    const { unmount } = render(<App checkHealth={() => new Promise((r) => (resolve = r))} />);
    unmount();
    resolve("ok");
    await Promise.resolve();
  });
});
