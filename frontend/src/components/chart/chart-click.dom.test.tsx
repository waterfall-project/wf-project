// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { roomForCharts } from "@/test/chart-room";

import { Chart, dataId } from "./chart";

/** The handlers the chart registered on its instance, by event. */
const registered = vi.hoisted(() => ({ handlers: new Map<string, (event: unknown) => void>() }));

// The instance is the real one; only the registration of a handler is recorded, since the
// simulated document paints nothing a pointer could reach.
vi.mock("echarts/core", async (actual) => {
  const echarts = await actual<typeof import("echarts/core")>();
  return {
    ...echarts,
    init: (...args: Parameters<typeof echarts.init>) => {
      const instance = echarts.init(...args);
      const on = instance.on.bind(instance) as (...rest: unknown[]) => unknown;
      Object.assign(instance, {
        on: (name: string, handler: (event: unknown) => void) => {
          registered.handlers.set(name, handler);
          return on(name, handler);
        },
      });
      return instance;
    },
  };
});

roomForCharts();

describe("the click on a point of a chart", () => {
  it("hands the identifier of the data item reached to the handler of the caller, and nothing for an item without one", () => {
    const onPoint = vi.fn();
    render(
      <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
        <Chart
          title="Points"
          description="Two points."
          option={() => ({ xAxis: {}, yAxis: {}, series: [{ type: "scatter", data: [[1, 2]] }] })}
          onPoint={onPoint}
        >
          <p>Values</p>
        </Chart>
      </NextIntlClientProvider>,
    );
    const click = registered.handlers.get("click");
    click?.({ data: { id: "risk-1", value: [1, 2] } });
    click?.({ data: [1, 2] });
    click?.({ data: { id: 3 } });
    expect(onPoint).toHaveBeenCalledExactlyOnceWith("risk-1");
  });

  it("reads an identifier only from an object that holds a text", () => {
    expect([dataId({ id: "a" }), dataId({ id: 1 }), dataId(null), dataId("a")]).toEqual([
      "a",
      undefined,
      undefined,
      undefined,
    ]);
  });
});
