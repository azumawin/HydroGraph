import { useThree } from "@react-three/fiber";
import { useEffect, useMemo } from "react";
import type { BufferGeometry } from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { Evaluation } from "../../api/Service.ts";
import { BODY_MODEL_THEME, BODY_REGION_IDS, BODY_SCAN_VIEW } from "./ModelConstants.ts";
import { createBodyGeometry } from "./createBodyGeometry.ts";

type BodyModelProps = {
  regionEvaluations: Partial<Record<string, Evaluation>>;
};

const BodyModel = ({ regionEvaluations }: BodyModelProps) => {
  const viewportWidth = useThree((state) => state.viewport.width);
  const viewportHeight = useThree((state) => state.viewport.height);
  const camera = useThree((state) => state.camera);
  const canvas = useThree((state) => state.gl.domElement);
  const invalidate = useThree((state) => state.invalidate);

  const theme = getComputedStyle(canvas);
  // Green is the body's default: it reads healthy until something is flagged,
  // and only a warning or a critical reading paints over it. A part no channel
  // measures, and a reading the specs set no cutoff for, both stay green; the
  // legend beside the model is where "No reading" is still spelled out.
  const defaultColor = theme.getPropertyValue(BODY_MODEL_THEME.NOMINAL).trim();
  const evaluationColors = {
    nominal: defaultColor,
    unspecified: defaultColor,
    warning: theme.getPropertyValue(BODY_MODEL_THEME.WARNING).trim(),
    critical: theme.getPropertyValue(BODY_MODEL_THEME.CRITICAL).trim(),
  };
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
          const color = evaluation === undefined ? defaultColor : evaluationColors[evaluation];

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
