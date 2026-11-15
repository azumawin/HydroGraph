// The shapes the backend sends (docs/json-shape.md), with nothing attached to a
// browser: no fetching, no EventSource. Modules that only need the types import
// them from here, so `npm test` can type-check them under Node.

export type Evaluation = "nominal" | "warning" | "critical" | "unspecified";

export type FindingSeverity = "nominal" | "warning" | "critical";

export type ConsciousnessLevel = "ALERT" | "CONFUSION" | "VOICE" | "PAIN" | "UNRESPONSIVE";

// Text readings are validated against the supported ACVPU states.
export type ReadingValue = number | boolean | ConsciousnessLevel;

export type TelemetryReading = {
  channel: string;
  value: ReadingValue;
  measured_at: string;
  evaluation: Evaluation;
};

export type TelemetryFinding = {
  id: string;
  status: FindingSeverity;
  triggers: string[];
  action: string;
  values: Record<string, unknown>;
};

export type ChannelDisplay = {
  unit: string;
  scale: number;
  offset: number;
};

// How a channel's values render before one has arrived: a number to scale and
// chart, a flag, or ACVPU text.
export type ChannelValueType = "number" | "boolean" | "enum";

export type ChannelInfo = {
  name: string;
  scope: "crew" | "environment";
  unit: string;
  value_type: ChannelValueType;
  display: ChannelDisplay;
  body_regions: string[];
  explanation: string;
};

export type FindingInfo = {
  name: string;
  channels: string[];
};

export type MissionEnvironment = {
  name: string;
  gravity_g: number;
  comm_delay_rt_s: number;
  baseline_dose_rate_usv_h: number;
  storm_shelter_available: boolean;
  day_length_h: number;
};

export type TelemetryDictionary = {
  environments: Record<string, MissionEnvironment>;
  channels: Record<string, ChannelInfo>;
  findings: Record<string, FindingInfo>;
};
