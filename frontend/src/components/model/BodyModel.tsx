import { useThree } from "@react-three/fiber";
import { useEffect, useMemo } from "react";
import type { BufferGeometry } from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import {
  BODY_EVALUATION_PRIORITY,
  BODY_MODEL_THEME,
  BODY_REGION_IDS,
  BODY_SCAN_VIEW,
} from "./ModelConstants.ts";
import type { NumericVital } from "../../api/Service.ts";
import { createBodyGeometry } from "./createBodyGeometry.ts";

type BodyModelProps = {
  readings: readonly NumericVital[];
};

const BodyModel = ({ readings }: BodyModelProps) => {
  const viewportWidth = useThree((state) => state.viewport.width);
  const viewportHeight = useThree((state) => state.viewport.height);
  const camera = useThree((state) => state.camera);
  const canvas = useThree((state) => state.gl.domElement);
  const invalidate = useThree((state) => state.invalidate);

  const theme = getComputedStyle(canvas);
  const neutralColor = theme.getPropertyValue(BODY_MODEL_THEME.NEUTRAL).trim();
  const evaluationColors = {
    optimal: neutralColor,
    normal: neutralColor,
    unusual: theme.getPropertyValue(BODY_MODEL_THEME.UNUSUAL).trim(),
    critical: theme.getPropertyValue(BODY_MODEL_THEME.CRITICAL).trim(),
  };
  const regionEvaluations: Partial<Record<string, NumericVital["evaluation"]>> = {};

  for (const reading of readings) {
    for (const region of reading.body_regions) {
      const currentEvaluation = regionEvaluations[region];

      if (
        currentEvaluation === undefined ||
        BODY_EVALUATION_PRIORITY[reading.evaluation] > BODY_EVALUATION_PRIORITY[currentEvaluation]
      ) {
        regionEvaluations[region] = reading.evaluation;
      }
    }
  }

  const geometryData = useMemo(() => createBodyGeometry(), []);
  const modelScale =
    Math.min(
      viewportWidth / Math.hypot(geometryData.size.x, geometryData.size.z),
      viewportHeight / Math.hypot(geometryData.size.y, geometryData.size.z),
    ) * BODY_SCAN_VIEW.FRAME_FILL;

  useEffect(() => {
    const controls = new OrbitControls(camera, canvas);
    controls.enablePan = false;
    controls.enableZoom = false;
    controls.cursorStyle = "grab";
    controls.minPolarAngle = BODY_SCAN_VIEW.MIN_POLAR_ANGLE;
    controls.maxPolarAngle = BODY_SCAN_VIEW.MAX_POLAR_ANGLE;
    const handleControlsChange = () => invalidate();
    controls.addEventListener("change", handleControlsChange);
    controls.update();

    return () => {
      controls.removeEventListener("change", handleControlsChange);
      controls.dispose();
    };
  }, [camera, canvas, invalidate]);

  const handleGeometryUpdate = (geometry: BufferGeometry) => {
    geometry.clearGroups();
    for (const group of geometryData.groups) {
      geometry.addGroup(group.start, group.count, group.materialIndex);
    }
    geometry.computeBoundingBox();
    geometry.computeBoundingSphere();
  };

  return (
    <group scale={modelScale} rotation-y={BODY_SCAN_VIEW.MODEL_ROTATION_Y}>
      <mesh position={[-geometryData.center.x, -geometryData.center.y, -geometryData.center.z]}>
        <bufferGeometry onUpdate={handleGeometryUpdate}>
          <bufferAttribute attach="attributes-position" args={[geometryData.positions, 3]} />
          <bufferAttribute attach="attributes-normal" args={[geometryData.normals, 3]} />
          <bufferAttribute attach="index" args={[geometryData.indices, 1]} />
        </bufferGeometry>
        {BODY_REGION_IDS.map((region, materialIndex) => {
          const evaluation = regionEvaluations[region];
          const color = evaluation === undefined ? neutralColor : evaluationColors[evaluation];

          return (
            <meshStandardMaterial
              key={region}
              name={region}
              attach={`material-${materialIndex}`}
              color={color}
              roughness={BODY_SCAN_VIEW.MATERIAL_ROUGHNESS}
              metalness={BODY_SCAN_VIEW.MATERIAL_METALNESS}
            />
          );
        })}
      </mesh>
    </group>
  );
};

export default BodyModel;
