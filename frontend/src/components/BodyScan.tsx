import { Canvas } from "@react-three/fiber";
import { ScanLine } from "lucide-react";
import { Component, Suspense } from "react";
import type { ReactNode } from "react";
import type { Evaluation } from "../api/Service.ts";
import { BODY_SCAN_VIEW, worstEvaluation } from "./model/ModelConstants.ts";
import { useTelemetryStore } from "../store/useTelemetryStore.ts";
import BodyModel from "./model/BodyModel.tsx";
import BodyScanRegions from "./BodyScanRegions.tsx";
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
      aria-labelledby="vitals-dashboard-body-scan-title"
    >
      <header className="vitals-dashboard-panel-header">
        <ScanLine className="vitals-dashboard-icon" />
        <h2 id="vitals-dashboard-body-scan-title" className="vitals-dashboard-panel-title m-0">
          Biometric body scan
        </h2>
      </header>
      <div className="vitals-dashboard-body-scan-content">
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
                role="img"
                aria-label={BODY_SCAN_VIEW.ARIA_LABEL}
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
