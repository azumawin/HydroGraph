import { Canvas } from "@react-three/fiber";
import { ChevronDown } from "lucide-react";
import { Component, Suspense, useId, useState } from "react";
import type { ReactNode } from "react";
import type { Evaluation } from "../api/Service.ts";
import { VITALS_METRICS } from "../Constants.ts";
import { BODY_SCAN_VIEW, worstEvaluation } from "./model/ModelConstants.ts";
import { useTelemetryStore } from "../store/useTelemetryStore.ts";
import BodyModel from "./model/BodyModel.tsx";
import BodyScanRegions from "./BodyScanRegions.tsx";
import BodyScanReadings from "./BodyScanReadings.tsx";
import "../assets/css/BodyScan.css";

class BodyScanErrorBoundary extends Component<{ children: ReactNode }, { hasModelError: boolean }> {
  state = { hasModelError: false };

  static getDerivedStateFromError() {
    return { hasModelError: true };
  }

  render() {
    if (this.state.hasModelError) {
      return (
        <p className="vitals-dashboard-body-scan-status" role="alert">
          Unable to display the 3D model. Reload the page to try again.
        </p>
      );
    }

    return this.props.children;
  }
}

const BodyScan = () => {
  const readings = useTelemetryStore((state) => state.readings);
  const channels = useTelemetryStore((state) => state.dictionary?.channels);
  const hasTelemetryError = useTelemetryStore((state) => state.hasTelemetryError);
  const [showReadings, setShowReadings] = useState(false);
  const readingsId = useId();
  const visibleVitalChannels = new Set<string>(
    Object.values(VITALS_METRICS).flatMap((metric) =>
      metric.SERIES.map((series) => series.CHANNEL),
    ),
  );
  const extraChannels = Object.entries(channels ?? {}).filter(
    ([channel]) => !visibleVitalChannels.has(channel),
  );
  const extraReadings = extraChannels.flatMap(([channel]) => readings[channel] ?? []);
  const criticalCount = extraReadings.filter((reading) => reading.evaluation === "critical").length;
  const warningCount = extraReadings.filter((reading) => reading.evaluation === "warning").length;

  // worst evaluation of the readings placed on each body region
  const regionEvaluations: Partial<Record<string, Evaluation>> = {};
  for (const reading of Object.values(readings)) {
    for (const region of channels?.[reading.channel]?.body_regions ?? []) {
      regionEvaluations[region] = worstEvaluation([regionEvaluations[region], reading.evaluation]);
    }
  }

  return (
    <section
      className="vitals-dashboard-panel vitals-dashboard-body-scan"
      aria-label="Biometric body scan"
    >
      <div className="vitals-dashboard-body-scan-header">
        {(criticalCount > 0 || warningCount > 0) && (
          <span className="vitals-dashboard-scan-alerts" aria-label="Additional reading alerts">
            {criticalCount > 0 && <span className="is-critical">{criticalCount} critical</span>}
            {warningCount > 0 && <span className="is-warning">{warningCount} warning</span>}
          </span>
        )}
        <button
          type="button"
          className="vitals-dashboard-scan-readings-toggle"
          title={`${extraReadings.length} of ${extraChannels.length} additional channels have readings`}
          aria-expanded={showReadings}
          aria-controls={readingsId}
          onClick={() => setShowReadings(!showReadings)}
        >
          Extra readings
          <span className="vitals-dashboard-scan-readings-count">
            {extraReadings.length}/{extraChannels.length}
          </span>
          <ChevronDown aria-hidden="true" />
        </button>
      </div>
      <div
        id={readingsId}
        hidden={!showReadings}
        className="vitals-dashboard-scan-readings-container"
      >
        {showReadings && (
          <BodyScanReadings
            channels={extraChannels}
            readings={readings}
            isLoading={channels === undefined && !hasTelemetryError}
            hasTelemetryError={hasTelemetryError}
          />
        )}
      </div>
      <div className="vitals-dashboard-body-scan-content" hidden={showReadings}>
        <div className="vitals-dashboard-panel-content vitals-dashboard-body-scan-viewer min-h-0 flex-1">
          <BodyScanErrorBoundary>
            <Suspense
              fallback={
                <p className="vitals-dashboard-body-scan-status" role="status">
                  Preparing body model…
                </p>
              }
            >
              <Canvas
                orthographic
                frameloop="demand"
                camera={{
                  position: BODY_SCAN_VIEW.CAMERA_POSITION,
                  zoom: BODY_SCAN_VIEW.CAMERA_ZOOM,
                }}
                fallback={
                  <p className="vitals-dashboard-body-scan-status" role="alert">
                    3D display is unavailable in this browser. Enable hardware acceleration or try
                    another browser.
                  </p>
                }
              >
                <ambientLight intensity={BODY_SCAN_VIEW.AMBIENT_INTENSITY} />
                <directionalLight
                  position={BODY_SCAN_VIEW.KEY_LIGHT_POSITION}
                  intensity={BODY_SCAN_VIEW.KEY_LIGHT_INTENSITY}
                />
                <directionalLight
                  position={BODY_SCAN_VIEW.FILL_LIGHT_POSITION}
                  intensity={BODY_SCAN_VIEW.FILL_LIGHT_INTENSITY}
                />
                <directionalLight
                  position={BODY_SCAN_VIEW.RIM_LIGHT_POSITION}
                  intensity={BODY_SCAN_VIEW.RIM_LIGHT_INTENSITY}
                />
                <BodyModel regionEvaluations={regionEvaluations} />
              </Canvas>
            </Suspense>
          </BodyScanErrorBoundary>
        </div>
        <BodyScanRegions regionEvaluations={regionEvaluations} />
      </div>
    </section>
  );
};

export default BodyScan;
