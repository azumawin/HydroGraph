import { BODY_SCAN_REGION_GROUPS, VITALS_EVALUATION_LABELS } from "../Constants.ts";
import type { Evaluation } from "../api/Service.ts";
import { worstEvaluation } from "./model/ModelConstants.ts";

type BodyScanRegionsProps = {
  regionEvaluations: Partial<Record<string, Evaluation>>;
};

const BodyScanRegions = ({ regionEvaluations }: BodyScanRegionsProps) => {
  return (
    <ul className="vitals-dashboard-body-regions" aria-label="Evaluations by body region">
      {BODY_SCAN_REGION_GROUPS.map((group) => {
        const evaluation = worstEvaluation(
          group.REGIONS.map((region) => regionEvaluations[region]),
        );

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
