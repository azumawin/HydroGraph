import { useEffect, useRef, useState } from "react";
import { VITALS_BACKGROUND } from "../Constants.ts";

const PLASMA_VERTEX_SHADER = `#version 300 es
in vec2 aPosition;
void main() {
  gl_Position = vec4(aPosition, 0.0, 1.0);
}`;

const PLASMA_VOLUME_SHADER = `#version 300 es
precision highp float;
uniform vec2 uView;
uniform vec2 uScale;
uniform float uZoom;
uniform float uTime;
uniform float uTwist;
uniform float uWave;
uniform float uSharpness;
uniform float uDither;
out vec4 outColor;

float hash(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}

void main() {
  vec2 c = (gl_FragCoord.xy * uScale - 0.5 * uView) / uZoom;
  vec3 rd = normalize(vec3(c, uView.y));
  vec3 ro = vec3(0.0, 0.0, -4.0);
  float z = 0.0;
  float density = 0.0;
  float band = 0.0;
  for (int i = 0; i < 60; i++) {
    vec3 p = ro + rd * z;
    vec3 s = p;
    float d = p.y - uTime;
    p.x += uWave * (1.0 + p.y) * sin(d + p.x * 0.1) * cos(0.34 * d + p.x * 0.05);
    vec2 q = p.xz *= mat2(cos(p.y * uTwist + vec4(0.0, 11.0, 33.0, 0.0) - uTime));
    float shell = abs(sqrt(length(q * q)) - 0.25 * (5.0 + s.y)) / 3.0;
    float stepLength = shell + 0.0008;
    z += stepLength;
    float phase = s.y + p.z * 0.5 + s.z - length(s - p);
    float weight = (1.0 + sin(phase + 8.0)) * exp(-shell * uSharpness) * stepLength;
    density += weight;
    band += weight * (0.5 + 0.5 * sin(phase * 0.5 + 1.0));
  }
  vec2 encoded = sqrt(vec2(density, band) / (1.0 + vec2(density, band)));
  encoded += (vec2(hash(gl_FragCoord.xy), hash(gl_FragCoord.yx + 17.0)) - 0.5) * uDither;
  outColor = vec4(encoded, 0.0, 1.0);
}`;

const PLASMA_COMPOSITE_SHADER = `#version 300 es
precision highp float;
uniform sampler2D uVolume;
uniform vec2 uResolution;
uniform vec3 uColor;
uniform vec3 uHighlight;
uniform float uGain;
uniform float uShine;
uniform float uOpacity;
out vec4 outColor;

void main() {
  vec2 uv = gl_FragCoord.xy / uResolution;
  vec2 encoded = clamp(texture(uVolume, uv).rg, 0.0, 0.9995);
  encoded *= encoded;
  vec2 volume = encoded / (1.0 - encoded);
  float density = volume.r * uGain;
  float band = clamp(volume.g / max(volume.r, 0.00001), 0.0, 1.0);
  vec3 tint = mix(uColor, uHighlight, band * 0.35);
  vec3 hdr = tint * density + uHighlight * density * density * uShine;
  float peak = max(hdr.r, max(hdr.g, hdr.b));
  float level = 1.0 - exp(-peak);
  float hot = smoothstep(1.0, 3.0, peak);
  vec3 hue = hdr / max(peak, 0.0001);
  vec3 color = mix(hue * level, vec3(level), hot * 0.6);
  color = pow(color, vec3(1.0 / 2.2));
  color = clamp(color, 0.0, 1.0) * uOpacity;
  outColor = vec4(color, max(color.r, max(color.g, color.b)));
}`;

type PlasmaProgram = {
  program: WebGLProgram;
  uniforms: Record<string, WebGLUniformLocation | null>;
};

const createPlasmaProgram = (gl: WebGL2RenderingContext, fragmentSource: string): PlasmaProgram => {
  const vertexShader = gl.createShader(gl.VERTEX_SHADER);
  const fragmentShader = gl.createShader(gl.FRAGMENT_SHADER);
  const program = gl.createProgram();
  let hasLinked = false;

  try {
    if (vertexShader === null || fragmentShader === null || program === null) {
      throw new Error("Unable to allocate the plasma shader program.");
    }

    gl.shaderSource(vertexShader, PLASMA_VERTEX_SHADER);
    gl.shaderSource(fragmentShader, fragmentSource);
    gl.compileShader(vertexShader);
    gl.compileShader(fragmentShader);
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.bindAttribLocation(program, 0, "aPosition");
    gl.linkProgram(program);

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      throw new Error(
        `Unable to link plasma shaders: ${gl.getProgramInfoLog(program)} ${gl.getShaderInfoLog(vertexShader)} ${gl.getShaderInfoLog(fragmentShader)}`,
      );
    }

    const uniforms: PlasmaProgram["uniforms"] = {};
    const uniformCount: number = gl.getProgramParameter(program, gl.ACTIVE_UNIFORMS);

    for (let uniformIndex = 0; uniformIndex < uniformCount; uniformIndex++) {
      const uniform = gl.getActiveUniform(program, uniformIndex);
      if (uniform !== null) {
        uniforms[uniform.name] = gl.getUniformLocation(program, uniform.name);
      }
    }

    hasLinked = true;
    return { program, uniforms };
  } finally {
    gl.deleteShader(vertexShader);
    gl.deleteShader(fragmentShader);
    if (!hasLinked) gl.deleteProgram(program);
  }
};

type VitalsDashboardBackgroundProps = {
  environmentId: string | null;
};

const VitalsDashboardBackground = ({ environmentId }: VitalsDashboardBackgroundProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const environmentIdRef = useRef(environmentId);
  const requestFrameRef = useRef<(() => void) | null>(null);
  const [hasBackgroundError, setHasBackgroundError] = useState(false);

  useEffect(() => {
    environmentIdRef.current = environmentId;
    // with reduced motion nothing else redraws, so repaint in the new colours
    requestFrameRef.current?.();
  }, [environmentId]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (canvas === null) return;

    const gl = canvas.getContext("webgl2", {
      alpha: true,
      premultipliedAlpha: true,
      antialias: false,
      depth: false,
      stencil: false,
    });

    if (gl === null) {
      setHasBackgroundError(true);
      return;
    }

    const programs: WebGLProgram[] = [];
    const buffer = gl.createBuffer();
    const vertexArray = gl.createVertexArray();
    const texture = gl.createTexture();
    const framebuffer = gl.createFramebuffer();
    let animationFrameId = 0;
    let lastFrameTime = 0;
    let elapsedSeconds = 0;
    let hasStopped = false;
    let resizeObserver: ResizeObserver | undefined;
    // with reduced motion the plasma is drawn once, still, and only redrawn on
    // resize or an environment change
    const reducedMotion = window.matchMedia(VITALS_BACKGROUND.REDUCED_MOTION_QUERY);

    const requestFrame = () => {
      if (hasStopped || document.hidden) return;
      cancelAnimationFrame(animationFrameId);
      animationFrameId = requestAnimationFrame(handleFrameRender);
    };

    const handleMotionChange = () => {
      lastFrameTime = 0;
      requestFrame();
    };

    const handleBackgroundDispose = () => {
      hasStopped = true;
      requestFrameRef.current = null;
      cancelAnimationFrame(animationFrameId);
      resizeObserver?.disconnect();
      reducedMotion.removeEventListener("change", handleMotionChange);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      canvas.removeEventListener("webglcontextlost", handleContextLost);
      gl.deleteBuffer(buffer);
      gl.deleteVertexArray(vertexArray);
      gl.deleteTexture(texture);
      gl.deleteFramebuffer(framebuffer);
      for (const program of programs) gl.deleteProgram(program);
    };

    const handleContextLost = () => {
      handleBackgroundDispose();
      setHasBackgroundError(true);
    };

    const handleVisibilityChange = () => {
      cancelAnimationFrame(animationFrameId);
      lastFrameTime = 0;
      if (!document.hidden && !hasStopped) {
        animationFrameId = requestAnimationFrame(handleFrameRender);
      }
    };

    let handleFrameRender: FrameRequestCallback;

    try {
      if (buffer === null || vertexArray === null || texture === null || framebuffer === null) {
        throw new Error("Unable to allocate the plasma rendering resources.");
      }

      const volume = createPlasmaProgram(gl, PLASMA_VOLUME_SHADER);
      programs.push(volume.program);
      const composite = createPlasmaProgram(gl, PLASMA_COMPOSITE_SHADER);
      programs.push(composite.program);
      const hasFloatTargets = gl.getExtension("EXT_color_buffer_float") !== null;
      const colorProbe = document.createElement("canvas").getContext("2d");

      // the environment class on the dashboard root redefines the theme token
      // so the colour is read again whenever the environment changes
      const readThemeColors = () => {
        const color = getComputedStyle(canvas)
          .getPropertyValue(VITALS_BACKGROUND.COLOR_TOKEN)
          .trim();

        if (colorProbe === null || !CSS.supports("color", color)) {
          throw new Error("Unable to read the plasma theme color.");
        }

        colorProbe.clearRect(0, 0, 1, 1);
        colorProbe.fillStyle = color;
        colorProbe.fillRect(0, 0, 1, 1);
        const [red, green, blue] = colorProbe.getImageData(0, 0, 1, 1).data;
        const base = [red, green, blue].map((channel) => Math.pow(channel / 255, 2.2));
        return { base, highlight: base.map((channel) => channel + (1 - channel) * 0.85) };
      };

      let themeColors = readThemeColors();
      let colorEnvironmentId = environmentIdRef.current;
      const view = { width: 1, height: 1, volumeWidth: 1, volumeHeight: 1 };

      gl.bindVertexArray(vertexArray);
      gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
      gl.enableVertexAttribArray(0);
      gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

      handleFrameRender = (now) => {
        if (hasStopped || document.hidden) return;

        if (environmentIdRef.current !== colorEnvironmentId) {
          colorEnvironmentId = environmentIdRef.current;
          try {
            themeColors = readThemeColors();
          } catch (error) {
            handleBackgroundDispose();
            console.error(VITALS_BACKGROUND.FALLBACK_MESSAGE, error);
            setHasBackgroundError(true);
            return;
          }
        }

        const deltaSeconds =
          lastFrameTime === 0
            ? 0
            : Math.min(VITALS_BACKGROUND.MAX_FRAME_DELTA_SECONDS, (now - lastFrameTime) / 1000);
        lastFrameTime = now;
        elapsedSeconds += deltaSeconds * VITALS_BACKGROUND.SPEED;

        gl.bindVertexArray(vertexArray);
        gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer);
        gl.viewport(0, 0, view.volumeWidth, view.volumeHeight);
        gl.useProgram(volume.program);
        gl.uniform2f(volume.uniforms.uView, view.width, view.height);
        gl.uniform2f(
          volume.uniforms.uScale,
          view.width / view.volumeWidth,
          view.height / view.volumeHeight,
        );
        gl.uniform1f(volume.uniforms.uZoom, VITALS_BACKGROUND.SCALE);
        gl.uniform1f(volume.uniforms.uTime, elapsedSeconds * 0.4);
        gl.uniform1f(volume.uniforms.uTwist, VITALS_BACKGROUND.TWIST);
        gl.uniform1f(volume.uniforms.uWave, VITALS_BACKGROUND.WAVE * 0.4);
        gl.uniform1f(volume.uniforms.uSharpness, 100 - VITALS_BACKGROUND.SOFTNESS * 90);
        gl.uniform1f(volume.uniforms.uDither, hasFloatTargets ? 0 : 1 / 255);
        gl.drawArrays(gl.TRIANGLES, 0, 3);

        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        gl.viewport(0, 0, canvas.width, canvas.height);
        gl.useProgram(composite.program);
        gl.uniform2f(composite.uniforms.uResolution, canvas.width, canvas.height);
        gl.uniform3fv(composite.uniforms.uColor, themeColors.base);
        gl.uniform3fv(composite.uniforms.uHighlight, themeColors.highlight);
        gl.uniform1f(composite.uniforms.uGain, VITALS_BACKGROUND.BRIGHTNESS * 4.8);
        gl.uniform1f(composite.uniforms.uShine, VITALS_BACKGROUND.SHINE * 0.025);
        gl.uniform1f(composite.uniforms.uOpacity, VITALS_BACKGROUND.OPACITY);
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, texture);
        gl.uniform1i(composite.uniforms.uVolume, 0);
        gl.drawArrays(gl.TRIANGLES, 0, 3);
        if (!reducedMotion.matches) animationFrameId = requestAnimationFrame(handleFrameRender);
      };

      const handleBackgroundResize = () => {
        if (hasStopped) return;

        try {
          view.width = Math.max(1, canvas.clientWidth);
          view.height = Math.max(1, canvas.clientHeight);
          const pixelRatio = Math.min(window.devicePixelRatio, VITALS_BACKGROUND.MAX_PIXEL_RATIO);
          const volumeScale = Math.min(
            VITALS_BACKGROUND.QUALITY,
            Math.sqrt(VITALS_BACKGROUND.MAX_VOLUME_PIXELS / (view.width * view.height)),
          );
          canvas.width = Math.max(1, Math.round(view.width * pixelRatio));
          canvas.height = Math.max(1, Math.round(view.height * pixelRatio));
          view.volumeWidth = Math.max(1, Math.round(view.width * volumeScale));
          view.volumeHeight = Math.max(1, Math.round(view.height * volumeScale));

          gl.bindTexture(gl.TEXTURE_2D, texture);
          gl.texImage2D(
            gl.TEXTURE_2D,
            0,
            hasFloatTargets ? gl.RGBA16F : gl.RGBA,
            view.volumeWidth,
            view.volumeHeight,
            0,
            gl.RGBA,
            hasFloatTargets ? gl.HALF_FLOAT : gl.UNSIGNED_BYTE,
            null,
          );
          gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer);
          gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);

          if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) !== gl.FRAMEBUFFER_COMPLETE) {
            throw new Error("Unable to initialize the plasma framebuffer.");
          }
          // resizing clears the canvas; a still background needs repainting
          requestFrame();
        } catch (error) {
          handleBackgroundDispose();
          console.error(VITALS_BACKGROUND.FALLBACK_MESSAGE, error);
          setHasBackgroundError(true);
        }
      };

      resizeObserver = new ResizeObserver(handleBackgroundResize);
      resizeObserver.observe(canvas);
      reducedMotion.addEventListener("change", handleMotionChange);
      document.addEventListener("visibilitychange", handleVisibilityChange);
      canvas.addEventListener("webglcontextlost", handleContextLost);
      handleBackgroundResize();
      requestFrameRef.current = requestFrame;
    } catch (error) {
      handleBackgroundDispose();
      console.error(VITALS_BACKGROUND.FALLBACK_MESSAGE, error);
      setHasBackgroundError(true);
    }

    return handleBackgroundDispose;
  }, []);

  return (
    <>
      <div className="vitals-dashboard-background" aria-hidden="true">
        <canvas
          ref={canvasRef}
          className="vitals-dashboard-background-canvas"
          hidden={hasBackgroundError}
        />
      </div>
      {hasBackgroundError && (
        <p className="vitals-dashboard-background-status" role="status">
          {VITALS_BACKGROUND.FALLBACK_MESSAGE}
        </p>
      )}
    </>
  );
};

export default VitalsDashboardBackground;
