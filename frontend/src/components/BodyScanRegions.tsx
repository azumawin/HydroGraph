import type { NumericVital } from "../api/Service.ts";
import { BODY_SCAN_REGION_GROUPS, VITALS_EVALUATION_LABELS } from "../Constants.ts";
import { BODY_EVALUATION_PRIORITY } from "./model/ModelConstants.ts";

type BodyScanRegionsProps = {
  readings: NumericVital[];
};

const BodyScanRegions = ({ readings }: BodyScanRegionsProps) => {
  return (
    <ul className="vitals-dashboard-body-regions" aria-label="Evaluations by body region">
      {BODY_SCAN_REGION_GROUPS.map((group) => {
        const regionReadings = readings.filter((reading) =>
          reading.body_regions.some((region) => group.REGIONS.includes(region)),
        );
        const evaluatedReading = regionReadings.toSorted(
          (first, second) =>
            BODY_EVALUATION_PRIORITY[second.evaluation] -
            BODY_EVALUATION_PRIORITY[first.evaluation],
        )[0];
        const evaluation = evaluatedReading?.evaluation;

        return (
          <li className="vitals-dashboard-body-region" key={group.LABEL}>
            <span className="vitals-dashboard-body-region-name">{group.LABEL}</span>
            <span
              className={`vitals-dashboard-body-region-status is-${evaluation ?? "unmeasured"}`}
            >
              <span className="vitals-dashboard-body-region-dot" />
              {evaluation === undefined ? "No reading" : VITALS_EVALUATION_LABELS[evaluation]}
            </span>
          </li>
        );
      })}
    </ul>
  );
};

export default BodyScanRegions;
