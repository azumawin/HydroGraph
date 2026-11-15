// The y-axis window, tick positions and tick labels for one vital's history.
//
// Fitting the axis to the data alone misreads a steady vital twice over. A
// resting SpO2 drifts about 0.01 % over two minutes: an axis fitted to that
// draws sensor noise as a full-height slope, and every tick inside so narrow a
// window rounds to the same number, so the labels read "98 98 98" beside a line
// that appears to be falling. Widening the window to the vital's own minimum
// span keeps a flat signal flat, and deriving the label precision from the tick
// step means two ticks can never print the same number.
//
// The ticks are returned rather than left to the chart library, so the labels
// the test checks are the labels that render.

export type ChartAxis = {
  domain: [number, number];
  ticks: number[];
  formatTick: (value: number) => string;
};

export const vitalChartAxis = (values: number[], minSpan: number, tickCount: number): ChartAxis => {
  const low = Math.min(...values);
  const high = Math.max(...values);
  const centre = (low + high) / 2;
  const span = Math.max(high - low, minSpan);
  const step = span / (tickCount - 1);
  const decimals = Math.min(3, Math.max(0, Math.ceil(-Math.log10(step))));
  const format = new Intl.NumberFormat(undefined, { maximumFractionDigits: decimals });
  const start = centre - span / 2;

  return {
    domain: [start, start + span],
    ticks: Array.from({ length: tickCount }, (_unused, index) => start + index * step),
    formatTick: format.format.bind(format),
  };
};
