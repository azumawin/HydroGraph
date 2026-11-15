import { formatInterval } from "../Constants.ts";
import type { ChannelSchedule } from "../utils/schedule.ts";

type ScheduleCellProps = {
  schedule: ChannelSchedule;
};

const ScheduleCell = ({ schedule }: ScheduleCellProps) => {
  if (schedule.state === "unscheduled") return null;

  const summary =
    schedule.state === "missing"
      ? "Never received"
      : schedule.state === "overdue"
        ? `Overdue ${formatInterval(schedule.overdueS)}`
        : `In ${formatInterval(schedule.dueInS)}`;

  return (
    <span className={`vitals-dashboard-schedule is-${schedule.state}`}>
      <span className="vitals-dashboard-schedule-summary">{summary}</span>
      <span className="vitals-dashboard-schedule-interval">
        Every {formatInterval(schedule.intervalS)}
      </span>
    </span>
  );
};

export default ScheduleCell;
