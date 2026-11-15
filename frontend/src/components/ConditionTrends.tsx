import {
  FINDING_STATUS_LABELS,
  TRENDS,
  VITALS_EVALUATION_LABELS,
  VITALS_FORMAT,
} from "../Constants.ts";
import type { Evaluation } from "../api/Service.ts";
import { useNow } from "../hooks/useNow.ts";
import { useReadingHistory } from "../hooks/useReadingHistory.ts";
import { useTelemetryStore } from "../store/useTelemetryStore.ts";
import { worstEvaluation } from "./model/ModelConstants.ts";

type ConditionTrendsProps = {
  environmentName: string;
  periodId: string;
  onPeriodChange: (periodId: string) => void;
};

const ConditionTrends = ({ environmentName, periodId, onPeriodChange }: ConditionTrendsProps) => {
  const conditions = useTelemetryStore((state) => state.dictionary?.findings);
  const findings = useTelemetryStore((state) => state.findings);
  const historyState = useReadingHistory(TRENDS.HISTORY_LIMIT);
  const now = useNow(TRENDS.PERIODS[0].DURATION_MS / TRENDS.BUCKET_COUNT);

  const period = TRENDS.PERIODS.find((candidate) => candidate.ID === periodId) ?? TRENDS.PERIODS[0];
  const periodStart = now - period.DURATION_MS;
  const bucketMs = period.DURATION_MS / TRENDS.BUCKET_COUNT;
  const bucketStarts = Array.from(
    { length: TRENDS.BUCKET_COUNT },
    (_, index) => periodStart + index * bucketMs,
  );

  const conditionRows = Object.entries(conditions ?? {})
    .filter(([, condition]) => condition.channels.length > 0)
    .map(([conditionId, condition]) => {
      const buckets: (Evaluation | undefined)[] = bucketStarts.map(() => undefined);
      let readingCount = 0;
      let flaggedCount = 0;

      if (historyState.status === "ready") {
        for (const reading of historyState.readings) {
          const timestamp = Date.parse(reading.measured_at);
          if (!condition.channels.includes(reading.channel) || timestamp < periodStart) continue;
          const index = Math.min(
            Math.floor((timestamp - periodStart) / bucketMs),
            TRENDS.BUCKET_COUNT - 1,
          );
          buckets[index] = worstEvaluation([buckets[index], reading.evaluation]);
          readingCount += 1;
          if (reading.evaluation === "warning" || reading.evaluation === "critical") {
            flaggedCount += 1;
          }
        }
      }

      return {
        conditionId,
        name: condition.name,
        status: findings[conditionId]?.status,
        buckets,
        readingCount,
        flaggedShare: readingCount === 0 ? undefined : flaggedCount / readingCount,
      };
    });

  return (
    <div className="vitals-dashboard-trends">
      <div className="vitals-dashboard-trends-toolbar">
        <p className="vitals-dashboard-trends-context">Graded for {environmentName}</p>
        <div className="vitals-dashboard-trends-periods" role="group" aria-label="Period">
          {TRENDS.PERIODS.map((candidate) => (
            <button
              key={candidate.ID}
              type="button"
              aria-pressed={candidate.ID === period.ID}
              className={`vitals-dashboard-trends-period${candidate.ID === period.ID ? " is-active" : ""}`}
              onClick={() => onPeriodChange(candidate.ID)}
            >
              {candidate.LABEL}
            </button>
          ))}
        </div>
      </div>
      {historyState.status === "loading" && (
        <p className="vitals-dashboard-tab-message">Loading reading history…</p>
      )}
      {historyState.status === "error" && (
        <p className="vitals-dashboard-tab-message is-error" role="alert">
          {TRENDS.HISTORY_ERROR}
        </p>
      )}
      {historyState.status === "ready" && (
        <ul className="vitals-dashboard-trends-list">
          {conditionRows.map((row) => (
            <li className="vitals-dashboard-trends-row" key={row.conditionId}>
              <div className="vitals-dashboard-trends-heading">
                <h3 className="vitals-dashboard-trends-name">{row.name}</h3>
                <span
                  className={`vitals-dashboard-reading-status is-${row.status ?? "unmeasured"}`}
                >
                  {row.status === undefined
                    ? TRENDS.NOT_EVALUATED
                    : FINDING_STATUS_LABELS[row.status]}
                </span>
              </div>
              <div className="vitals-dashboard-trends-strip">
                {row.buckets.map((evaluation, index) => {
                  const bucketStart = bucketStarts[index];
                  const label =
                    evaluation === undefined
                      ? TRENDS.NO_READING
                      : VITALS_EVALUATION_LABELS[evaluation];
                  return (
                    <span
                      key={bucketStart}
                      className={`vitals-dashboard-trends-cell is-${evaluation ?? "empty"}`}
                      title={`${VITALS_FORMAT.MEASURED_AT.format(bucketStart)}: ${label}`}
                    />
                  );
                })}
              </div>
              <div className="vitals-dashboard-trends-axis">
                <span>{VITALS_FORMAT.MEASURED_AT.format(periodStart)}</span>
                <span>
                  {row.flaggedShare === undefined
                    ? "No readings in this period"
                    : `${Math.round(row.flaggedShare * 100)}% of ${row.readingCount} readings flagged`}
                </span>
                <span>Now</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default ConditionTrends;
