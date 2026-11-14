import { MathUtils, MeshBasicMaterial, Vector3 } from "three";
import { MarchingCubes } from "three/addons/objects/MarchingCubes.js";
import {
  BODY_MODEL_CORE,
  BODY_MODEL_PAIRED_SHAPES,
  BODY_MODEL_SURFACE,
  BODY_REGION_IDS,
  BODY_REGIONS,
} from "./ModelConstants.ts";
import type { BodyShape } from "./ModelConstants.ts";

export const createBodyGeometry = () => {
  const { RESOLUTION, MAX_TRIANGLES, HALF_EXTENTS, BLEND_RADIUS } = BODY_MODEL_SURFACE;
  const material = new MeshBasicMaterial();
  const surface = new MarchingCubes(RESOLUTION, material, false, false, MAX_TRIANGLES);
  const regionCells = new Uint8Array(RESOLUTION ** 3);
  const shapes: BodyShape[] = [...BODY_MODEL_CORE];

  for (const shape of BODY_MODEL_PAIRED_SHAPES) {
    shapes.push(
      {
        REGION: shape.LEFT_REGION,
        CENTER: shape.CENTER,
        RADII: shape.RADII,
        ROTATION_Z: shape.ROTATION_Z,
      },
      {
        REGION: shape.RIGHT_REGION,
        CENTER: [-shape.CENTER[0], shape.CENTER[1], shape.CENTER[2]],
        RADII: shape.RADII,
        ROTATION_Z: -(shape.ROTATION_Z ?? 0),
      },
    );
  }

  try {
    surface.isolation = 0;
    surface.field.fill(-BLEND_RADIUS);

    for (const shape of shapes) {
      const [centerX, centerY, centerZ] = shape.CENTER;
      const [radiusX, radiusY, radiusZ] = shape.RADII;
      const cosine = Math.cos(shape.ROTATION_Z ?? 0);
      const sine = Math.sin(shape.ROTATION_Z ?? 0);
      const minimumRadius = Math.min(...shape.RADII);
      const isHand =
        shape.REGION === BODY_REGIONS.LEFT_HAND || shape.REGION === BODY_REGIONS.RIGHT_HAND;
      const blendRadius = isHand ? BODY_MODEL_SURFACE.HAND_BLEND_RADIUS : BLEND_RADIUS;
      const supportScale = 1 + blendRadius / minimumRadius;
      const extentX = (Math.abs(cosine) * radiusX + Math.abs(sine) * radiusY) * supportScale;
      const extentY = (Math.abs(sine) * radiusX + Math.abs(cosine) * radiusY) * supportScale;
      const extentZ = radiusZ * supportScale;
      const regionIndex = BODY_REGION_IDS.indexOf(shape.REGION);
      const toCell = (coordinate: number, extent: number) =>
        MathUtils.clamp(
          Math.floor(((coordinate / extent + 1) * RESOLUTION) / 2),
          1,
          RESOLUTION - 2,
        );
      const minX = toCell(centerX - extentX, HALF_EXTENTS[0]);
      const maxX = toCell(centerX + extentX, HALF_EXTENTS[0]);
      const minY = toCell(centerY - extentY, HALF_EXTENTS[1]);
      const maxY = toCell(centerY + extentY, HALF_EXTENTS[1]);
      const minZ = toCell(centerZ - extentZ, HALF_EXTENTS[2]);
      const maxZ = toCell(centerZ + extentZ, HALF_EXTENTS[2]);

      for (let z = minZ; z <= maxZ; z += 1) {
        const localZ = (((z / RESOLUTION) * 2 - 1) * HALF_EXTENTS[2] - centerZ) / radiusZ;

        for (let y = minY; y <= maxY; y += 1) {
          const offsetY = ((y / RESOLUTION) * 2 - 1) * HALF_EXTENTS[1] - centerY;

          for (let x = minX; x <= maxX; x += 1) {
            const offsetX = ((x / RESOLUTION) * 2 - 1) * HALF_EXTENTS[0] - centerX;
            const localX = (cosine * offsetX + sine * offsetY) / radiusX;
            const localY = (-sine * offsetX + cosine * offsetY) / radiusY;
            const density =
              (1 - Math.sqrt(localX ** 2 + localY ** 2 + localZ ** 2)) * minimumRadius;
            const previousDensity = surface.getCell(x, y, z);
            const blend = Math.max(blendRadius - Math.abs(density - previousDensity), 0);

            if (density > previousDensity) {
              regionCells[z * RESOLUTION ** 2 + y * RESOLUTION + x] = regionIndex;
            }

            surface.setCell(
              x,
              y,
              z,
              Math.max(density, previousDensity) + blend ** 2 / (4 * blendRadius),
            );
          }
        }
      }
    }

    surface.update();

    if (surface.count === 0 || surface.count >= MAX_TRIANGLES * 3) {
      throw new Error("Body surface generation exceeded its geometry limits.");
    }

    const regionTriangles = BODY_REGION_IDS.map<number[]>(() => []);

    for (let vertex = 0; vertex < surface.count; vertex += 3) {
      const offset = vertex * 3;
      const triangleCenter = [0, 1, 2].map(
        (axis) =>
          (surface.positionArray[offset + axis] +
            surface.positionArray[offset + 3 + axis] +
            surface.positionArray[offset + 6 + axis]) /
          3,
      );
      const [x, y, z] = triangleCenter.map((coordinate) =>
        MathUtils.clamp(Math.round(((coordinate + 1) * RESOLUTION) / 2), 0, RESOLUTION - 1),
      );
      const regionIndex = regionCells[z * RESOLUTION ** 2 + y * RESOLUTION + x];
      regionTriangles[regionIndex].push(vertex, vertex + 1, vertex + 2);
    }

    surface.geometry.scale(...HALF_EXTENTS);
    surface.geometry.computeBoundingBox();
    const bounds = surface.geometry.boundingBox;

    if (bounds === null) {
      throw new Error("Body surface bounds are unavailable.");
    }

    const indices: number[] = [];
    const groups = regionTriangles.map((triangles, materialIndex) => {
      const start = indices.length;
      for (const index of triangles) indices.push(index);
      return { start, count: triangles.length, materialIndex };
    });

    return {
      positions: surface.positionArray.slice(0, surface.count * 3),
      normals: surface.normalArray.slice(0, surface.count * 3),
      indices: Uint32Array.from(indices),
      groups,
      size: bounds.getSize(new Vector3()),
      center: bounds.getCenter(new Vector3()),
    };
  } finally {
    surface.geometry.dispose();
    material.dispose();
  }
};
