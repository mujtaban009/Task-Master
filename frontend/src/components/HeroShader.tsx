import React, { useEffect, useRef, useState } from 'react';

// Flowing silk-like light ribbons (domain-warped noise) plus a sweeping clock dial.
// Rendered by one fragment shader, so the motion is continuous and costs no video download.
const FRAGMENT = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
uniform vec2 u_res;
uniform float u_time;
uniform vec2 u_mouse;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x),
             mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
}
float fbm(vec2 p) {
  float v = 0.0, a = 0.5;
  for (int i = 0; i < 5; i++) { v += a * noise(p); p = p * 2.02 + vec2(1.7, 9.2); a *= 0.5; }
  return v;
}

void main() {
  vec2 uv = gl_FragCoord.xy / u_res;
  float aspect = u_res.x / u_res.y;
  vec2 p = (gl_FragCoord.xy - 0.5 * u_res) / u_res.y;
  p += (u_mouse - 0.5) * 0.06;
  float t = u_time * 0.075;

  // Silk ribbons: thin bright iso-lines of a doubly domain-warped noise field
  vec2 q = vec2(fbm(p * 1.5 + vec2(0.0, t)), fbm(p * 1.5 + vec2(5.2, 1.3) - t));
  vec2 r = vec2(fbm(p * 1.5 + 3.0 * q + vec2(1.7, 9.2) + t * 1.2), fbm(p * 1.5 + 3.0 * q + vec2(8.3, 2.8) - t));
  float f = fbm(p * 1.3 + 3.0 * r);
  float ribbon = pow(1.0 - abs(sin(f * 13.0 + t * 5.0)), 7.0);
  float glow = smoothstep(0.25, 0.95, f);

  vec3 emerald = vec3(0.06, 0.73, 0.51);
  vec3 teal = vec3(0.08, 0.60, 0.68);
  vec3 violet = vec3(0.52, 0.34, 0.96);
  vec3 sky = vec3(0.22, 0.74, 0.97);
  vec3 col = vec3(0.007, 0.011, 0.02);
  col += mix(emerald, violet, smoothstep(0.2, 0.9, r.x)) * glow * 0.26;
  col += mix(teal, sky, r.y) * ribbon * (0.38 + 0.95 * glow);

  // Clock dial on the right (centered on narrow screens)
  float cx = aspect > 1.2 ? aspect * 0.24 : 0.0;
  float cy = aspect > 1.2 ? 0.02 : -0.3;
  float dialAmt = aspect > 1.2 ? 1.0 : 0.6;
  float R = min(0.34, aspect * 0.42);
  vec2 d = p - vec2(cx, cy);
  float rad = length(d);
  float ang = atan(d.y, d.x);
  float TAU = 6.2831853;

  float ring = smoothstep(0.004, 0.0, abs(rad - R));
  float ring2 = smoothstep(0.0025, 0.0, abs(rad - R * 0.78)) * 0.5;
  float n = ang / TAU * 60.0;
  float dist = abs(n - floor(n + 0.5));
  float major = step(mod(floor(n + 0.5), 5.0), 0.5);
  float tickIn = mix(0.93, 0.87, major);
  float ticks = smoothstep(0.1, 0.0, dist) * step(R * tickIn, rad) * step(rad, R * 0.97) * (0.45 + 0.55 * major);
  float dashed = step(0.5, fract((ang + u_time * 0.08) / TAU * 90.0)) * smoothstep(0.003, 0.0, abs(rad - R * 0.62)) * 0.45;

  // Sweeping second hand with a fading trail (one turn per minute, like a real second hand)
  float handAng = 1.5707963 - u_time * (TAU / 60.0);
  float behind = mod(ang - handAng, TAU);
  float trail = exp(-behind * 2.4) * step(rad, R * 0.97) * smoothstep(0.0, R * 0.5, rad);
  float hand = smoothstep(0.014, 0.0, min(behind, TAU - behind)) * step(rad, R * 0.97) * step(0.015, rad);
  float hub = smoothstep(0.014, 0.0, rad - 0.012);

  vec3 dialCol = vec3(0.55, 1.0, 0.85);
  col += dialAmt * dialCol * (ring * 0.55 + ring2 * 0.5 + ticks * 0.8 + dashed * 0.6);
  col += dialAmt * (emerald * trail * 0.4 + dialCol * hand * 0.9 + vec3(1.0) * hub * 0.9);

  // Keep the headline area dark, add vignette and grain
  col *= mix(0.45, 1.0, smoothstep(0.0, 0.65, uv.x * (aspect > 1.2 ? 1.0 : 1.6)));
  col *= 1.0 - 0.6 * dot(uv - 0.5, uv - 0.5) * 2.0;
  col += (hash(gl_FragCoord.xy + u_time) - 0.5) * 0.02;
  gl_FragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}`;

const VERTEX = 'attribute vec2 a; void main() { gl_Position = vec4(a, 0.0, 1.0); }';

function compile(gl: WebGLRenderingContext, type: number, src: string) {
  const s = gl.createShader(type)!;
  gl.shaderSource(s, src);
  gl.compileShader(s);
  return gl.getShaderParameter(s, gl.COMPILE_STATUS) ? s : null;
}

export const HeroShader: React.FC<{ className?: string }> = ({ className = '' }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current!;
    const gl = canvas.getContext('webgl', { antialias: false, alpha: false, powerPreference: 'low-power' });
    const vs = gl && compile(gl, gl.VERTEX_SHADER, VERTEX);
    const fs = gl && compile(gl, gl.FRAGMENT_SHADER, FRAGMENT);
    const prog = gl && vs && fs ? gl.createProgram() : null;
    if (!gl || !vs || !fs || !prog) {
      setFailed(true);
      return;
    }
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      setFailed(true);
      return;
    }
    gl.useProgram(prog);

    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, 'a');
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    const uRes = gl.getUniformLocation(prog, 'u_res');
    const uTime = gl.getUniformLocation(prog, 'u_time');
    const uMouse = gl.getUniformLocation(prog, 'u_mouse');

    const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let visible = true;
    let raf = 0;
    let mx = 0.5, my = 0.5, tx = 0.5, ty = 0.5;
    const start = performance.now();

    const resize = () => {
      // Render at 75% of CSS pixels: the effect is soft, and it keeps low-end GPUs smooth
      const scale = Math.min(window.devicePixelRatio || 1, 1.5) * 0.75;
      canvas.width = Math.min(1600, Math.round(canvas.clientWidth * scale));
      canvas.height = Math.round(canvas.clientHeight * (canvas.width / canvas.clientWidth));
      gl.viewport(0, 0, canvas.width, canvas.height);
    };
    const draw = (time: number) => {
      mx += (tx - mx) * 0.05;
      my += (ty - my) * 0.05;
      gl.uniform2f(uRes, canvas.width, canvas.height);
      gl.uniform1f(uTime, time);
      gl.uniform2f(uMouse, mx, my);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    };
    const loop = () => {
      if (visible) draw((performance.now() - start) / 1000 + 6);
      raf = requestAnimationFrame(loop);
    };
    const onPointer = (e: PointerEvent) => {
      tx = e.clientX / window.innerWidth;
      ty = 1 - e.clientY / window.innerHeight;
    };
    const onResize = () => {
      resize();
      if (still) draw(18);
    };

    resize();
    if (still) {
      draw(18);
    } else {
      raf = requestAnimationFrame(loop);
      window.addEventListener('pointermove', onPointer, { passive: true });
    }
    window.addEventListener('resize', onResize);
    // Stop drawing while the hero is scrolled out of view
    const io = new IntersectionObserver(([e]) => (visible = e.isIntersecting));
    io.observe(canvas);

    return () => {
      cancelAnimationFrame(raf);
      io.disconnect();
      window.removeEventListener('pointermove', onPointer);
      window.removeEventListener('resize', onResize);
      // No loseContext(): React's dev double-mount reuses this canvas and would find the context dead
    };
  }, []);

  if (failed) {
    return <div aria-hidden="true" className={`bg-[radial-gradient(ellipse_at_70%_40%,rgba(16,185,129,0.25),transparent_60%)] ${className}`} />;
  }
  return <canvas ref={canvasRef} aria-hidden="true" className={`h-full w-full ${className}`} />;
};
