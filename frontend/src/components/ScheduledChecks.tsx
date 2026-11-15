import { MEASUREMENTS, SCHEDULE, formatInterval } from "../Constants.ts";
import { useNow } from "../hooks/useNow.ts";
import { useTelemetryStore } from "../store/useTelemetryStore.ts";
import { channelSchedule } from "../utils/schedule.ts";

const ScheduledChecks = () => {
  const channels = useTelemetryStore((state) => state.dictionary?.channels);
  const readings = useTelemetryStore((state) => state.readings);
  const now = useNow(MEASUREMENTS.NOW_REFRESH_MS);

  const schedules = Object.entries(channels ?? {}).map(([channelId, channel]) => ({
    channelId,
    name: channel.name,
    schedule: channelSchedule(channel, readings[channelId], now),
  }));
  const lateChecks = schedules.flatMap(({ channelId, name, schedule }) =>
    schedule.state === "overdue" || schedule.state === "missing"
      ? [
          {
            channelId,
            name,
            detail:
              schedule.state === "missing"
                ? `Never received, expected every ${formatInterval(schedule.intervalS)}`
                : `Overdue ${formatInterval(schedule.overdueS)}, expected every ${formatInterval(schedule.intervalS)}`,
          },
        ]
      : [],
  );
  const upcomingChecks = schedules
    .flatMap(({ channelId, name, schedule }) =>
      schedule.state === "due" &&
      schedule.intervalS >= SCHEDULE.UPCOMING_MIN_INTERVAL_S &&
      schedule.dueInS <= SCHEDULE.UPCOMING_WINDOW_S
        ? [{ channelId, name, dueInS: schedule.dueInS }]
        : [],
    )
    .toSorted((first, second) => first.dueInS - second.dueInS);

  return (
    <section className="vitals-dashboard-checks" aria-label="Scheduled checks">
      <h3 className="vitals-dashboard-checks-title">Checks</h3>
      {lateChecks.length === 0 && upcomingChecks.length === 0 && (
        <p className="vitals-dashboard-checks-empty">Every scheduled measurement is on time.</p>
      )}
      <ul className="vitals-dashboard-checks-list">
        {lateChecks.map((check) => (
          <li className="vitals-dashboard-checks-item is-late" key={check.channelId}>
            <span className="vitals-dashboard-checks-name">{check.name}</span>
            <span className="vitals-dashboard-checks-detail">{check.detail}</span>
          </li>
        ))}
        {upcomingChecks.map((check) => (
          <li className="vitals-dashboard-checks-item" key={check.channelId}>
            <span className="vitals-dashboard-checks-name">{check.name}</span>
            <span className="vitals-dashboard-checks-detail">
              Due in {formatInterval(check.dueInS)}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
};

export default ScheduledChecks;
