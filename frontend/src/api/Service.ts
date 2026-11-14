import { VITALS_HISTORY } from "../Constants.ts";

export type NumericVital = {
  channel: string;
  value: number;
  unit: string;
  evaluation: "optimal" | "normal" | "unusual" | "critical";
  measured_at: string;
  name: string;
  body_regions: string[];
  explanation: string;
};

export type HeartRate = NumericVital;

export type BloodPressure = NumericVital;

export type VitalsHistoryRequest = {
  from: string;
  to: string;
};

export type VitalsHistoryPoint = Pick<NumericVital, "channel" | "value" | "unit"> & {
  timestamp: string;
};

export type Mood = {
  id: string;
  label: string;
  value: string;
  measure_at: string;
};

export const postVitalsHistory = async (
  request: VitalsHistoryRequest,
): Promise<VitalsHistoryPoint[]> => {
  const fromTimestamp = Date.parse(request.from);
  const toTimestamp = Date.parse(request.to);

  if (
    !Number.isFinite(fromTimestamp) ||
    !Number.isFinite(toTimestamp) ||
    fromTimestamp >= toTimestamp
  ) {
    throw new RangeError(VITALS_HISTORY.INVALID_RANGE_MESSAGE);
  }

  const mockSeries = [
    {
      channel: "heart_rate",
      unit: "bpm",
      values: [
        68, 66, 65, 64, 63, 65, 69, 74, 78, 82, 76, 73, 71, 75, 79, 84, 80, 76, 73, 71, 74, 73, 70,
        71, 72,
      ],
    },
    {
      channel: "bp_systolic",
      unit: "mmHg",
      values: [
        162, 160, 158, 159, 157, 160, 164, 168, 172, 175, 171, 168, 170, 167, 173, 175, 172, 178,
        176, 179, 177, 181, 178, 179, 180,
      ],
    },
    {
      channel: "bp_diastolic",
      unit: "mmHg",
      values: [
        98, 96, 95, 96, 94, 97, 99, 101, 104, 106, 103, 100, 102, 101, 104, 103, 106, 105, 108, 107,
        109, 108, 109, 108, 110,
      ],
    },
    {
      channel: "blood_sugar",
      unit: "mg/dL",
      values: [
        94, 92, 90, 89, 88, 90, 95, 112, 106, 99, 94, 91, 94, 98, 115, 108, 101, 96, 93, 97, 110,
        103, 99, 96, 95,
      ],
    },
    {
      channel: "body_temperature",
      unit: "°C",
      values: [
        36.8, 36.7, 36.6, 36.6, 36.5, 36.6, 36.8, 36.9, 37, 37.1, 37, 37.1, 37.2, 37.1, 37.3, 37.5,
        37.4, 37.7, 37.8, 37.7, 38, 38.1, 38, 38.1, 38.2,
      ],
    },
    {
      channel: "daily_sleep_hours",
      unit: "hours",
      values: [0, 1, 2, 3, 4, 5, 6, 7, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8],
    },
  ];
  const mockEndTimestamp =
    Math.floor(Date.now() / VITALS_HISTORY.MOCK_INTERVAL_MS) * VITALS_HISTORY.MOCK_INTERVAL_MS;
  const response: VitalsHistoryPoint[] = mockSeries.flatMap((series) =>
    series.values.map((value, pointIndex) => ({
      channel: series.channel,
      value,
      unit: series.unit,
      timestamp: new Date(
        mockEndTimestamp -
          (series.values.length - 1 - pointIndex) * VITALS_HISTORY.MOCK_INTERVAL_MS,
      ).toISOString(),
    })),
  );

  return response
    .filter((point) => {
      const pointTimestamp = Date.parse(point.timestamp);
      return pointTimestamp >= fromTimestamp && pointTimestamp < toTimestamp;
    })
    .sort(
      (previousPoint, nextPoint) =>
        Date.parse(previousPoint.timestamp) - Date.parse(nextPoint.timestamp),
    );
};

export const getHeartRate = async (): Promise<HeartRate[]> => [
  {
    channel: "heart_rate",
    value: 72,
    unit: "bpm",
    evaluation: "normal",
    measured_at: "2026-11-14T00:00:00.000Z",
    name: "Heart rate",
    body_regions: ["heart"],
    explanation: "Heart rate measures the number of heartbeats per minute.",
  },
];

export const getBloodPressure = async (): Promise<BloodPressure[]> => [
  {
    channel: "bp_systolic",
    value: 180,
    unit: "mmHg",
    evaluation: "critical",
    measured_at: "2026-11-08T07:12:00Z",
    name: "Blood pressure (systolic)",
    body_regions: ["heart", "chest"],
    explanation: "Systolic blood pressure measures pressure when the heart contracts.",
  },
  {
    channel: "bp_diastolic",
    value: 110,
    unit: "mmHg",
    evaluation: "unusual",
    measured_at: "2026-11-08T07:12:00Z",
    name: "Blood pressure (diastolic)",
    body_regions: ["heart", "chest"],
    explanation: "Diastolic blood pressure measures pressure when the heart relaxes between beats.",
  },
];

export const getBloodSugar = async (): Promise<NumericVital[]> => [
  {
    channel: "blood_sugar",
    value: 95,
    unit: "mg/dL",
    evaluation: "normal",
    measured_at: "2026-11-14T00:00:00.000Z",
    name: "Blood sugar",
    body_regions: [],
    explanation: "Blood sugar measures the concentration of glucose in the blood.",
  },
];

export const getBodyTemperature = async (): Promise<NumericVital[]> => [
  {
    channel: "body_temperature",
    value: 38.2,
    unit: "°C",
    evaluation: "unusual",
    measured_at: "2026-11-14T00:00:00.000Z",
    name: "Body temperature",
    body_regions: ["head", "neck"],
    explanation: "Body temperature measures how warm the body is.",
  },
];

export const getDailySleepHours = async (): Promise<NumericVital[]> => [
  {
    channel: "daily_sleep_hours",
    value: 8,
    unit: "hours",
    evaluation: "normal",
    measured_at: "2026-11-14T00:00:00.000Z",
    name: "Daily sleep",
    body_regions: [],
    explanation: "Daily sleep records the amount of time spent asleep.",
  },
];

export const getMood = async (): Promise<Mood[]> => {
  const response = [
    {
      metric_id: "mood",
      metric_label: "Mood",
      metric_value: "Good",
      measure_at: "2026-11-14T00:00:00.000Z",
    },
  ];

  return response.map((mood) => ({
    id: mood.metric_id,
    label: mood.metric_label,
    value: mood.metric_value,
    measure_at: mood.measure_at,
  }));
};
