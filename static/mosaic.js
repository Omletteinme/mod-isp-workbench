/* Animated 3D Bayer colour-filter-array rendered as violet halftone: an RGGB grid of
   photosites on a silicon plate, with a light signal sweeping across it. Plain WebGL2,
   no dependencies. Without WebGL2 the poster tile keeps its static dot field. */
(() => {
  const art = document.querySelector('.poster-art');
  const canvas = art && art.querySelector('.mosaic-canvas');
  const gl = canvas && canvas.getContext('webgl2', { alpha: true, antialias: false, premultipliedAlpha: true });
  if (!gl) return;

  const N = 14, PITCH = 1, TILE = 0.84, PLATE_TOP = 0.35, BASE_H = 0.22, WAVE_H = 1.15;
  // Halftone tone per filter: green photosites (twice as many) read heaviest, blue lightest.
  const TONE = { R: 0.62, G: 0.92, B: 0.42, plate: 0.16 };
  const RGGB = [TONE.R, TONE.G, TONE.G, TONE.B];

  const vs = `#version 300 es
  in vec3 a_pos; in vec3 a_normal;
  in vec3 a_off; in vec3 a_scale; in float a_tone; in float a_live;
  uniform float u_time, u_yaw, u_pitch, u_f, u_aspect, u_dist;
  uniform vec2 u_shift;
  out float v_lum;
  vec3 rot(vec3 p){
    float cy = cos(u_yaw), sy = sin(u_yaw), cp = cos(u_pitch), sp = sin(u_pitch);
    p = vec3(p.x*cy + p.z*sy, p.y, -p.x*sy + p.z*cy);
    return vec3(p.x, p.y*cp - p.z*sp, p.y*sp + p.z*cp);
  }
  void main(){
    float w = 0.5 + 0.5*sin(dot(a_off.xz, vec2(0.55, 0.35)) - u_time*1.4);
    w = w*w*w*a_live;
    vec3 s = a_scale; s.y += ${WAVE_H.toFixed(2)}*w;
    vec3 p = rot(a_off + a_pos*s);
    vec3 n = rot(a_normal);
    float diff = max(dot(n, normalize(vec3(-0.4, 0.8, 0.6))), 0.0);
    v_lum = clamp(a_tone*(0.40 + 0.75*diff) + w*0.38, 0.0, 1.0);
    p.z -= u_dist;
    float near = 1.0, far = 120.0, zc = -p.z;
    gl_Position = vec4(p.x*u_f/u_aspect + u_shift.x*zc, p.y*u_f + u_shift.y*zc, zc*(far+near)/(far-near) - 2.0*far*near/(far-near), zc);
  }`;
  // Screen-space halftone on a 45-degree dot grid; dot radius follows shaded luminance.
  const fs = `#version 300 es
  precision mediump float;
  in float v_lum; uniform float u_cell; out vec4 o;
  void main(){
    vec2 q = mat2(0.7071, -0.7071, 0.7071, 0.7071)*gl_FragCoord.xy/u_cell;
    float r = sqrt(clamp(v_lum, 0.0, 1.0))*0.66;
    float d = length(fract(q) - 0.5), aa = 1.2/u_cell;
    float a = 1.0 - smoothstep(r - aa, r + aa, d);
    if (a < 0.02) discard;
    vec3 col = mix(vec3(0.33, 0.22, 0.92), vec3(0.76, 0.70, 1.0), clamp((v_lum - 0.55)*2.2, 0.0, 1.0));
    o = vec4(col*a, a);
  }`;

  const shader = (type, src) => {
    const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  };
  let prog;
  try {
    prog = gl.createProgram();
    gl.attachShader(prog, shader(gl.VERTEX_SHADER, vs));
    gl.attachShader(prog, shader(gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
  } catch (e) { console.warn('Bayer mosaic disabled:', e.message); return; }
  gl.useProgram(prog);

  // Unit cube spanning x,z in [-.5,.5] and y in [0,1]; per-face normals.
  const pos = [], nor = [], idx = [];
  for (let a = 0; a < 3; a++) for (const sgn of [-1, 1]) {
    const u = (a + 1) % 3, v = (a + 2) % 3, base = pos.length / 3;
    for (const [du, dv] of [[-.5, -.5], [.5, -.5], [.5, .5], [-.5, .5]]) {
      const p = [0, 0, 0], n = [0, 0, 0];
      p[a] = sgn * .5; p[u] = du; p[v] = dv; p[1] += .5; n[a] = sgn;
      pos.push(...p); nor.push(...n);
    }
    idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
  }

  const STRIDE = 8; // offset(3) scale(3) tone(1) live(1)
  const inst = [];
  const add = (x, y, z, sx, sy, sz, tone, live) => inst.push(x, y, z, sx, sy, sz, tone, live);
  const extent = N * PITCH;
  add(0, 0, 0, extent + 1.2, PLATE_TOP, extent + 1.2, TONE.plate, 0);
  for (let i = 0; i < N; i++) for (let j = 0; j < N; j++)
    add((i - (N - 1) / 2) * PITCH, PLATE_TOP, (j - (N - 1) / 2) * PITCH, TILE, BASE_H, TILE, RGGB[(i % 2) + 2 * (j % 2)], 1);

  const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
  const buf = (data, Type, target = gl.ARRAY_BUFFER) => {
    const b = gl.createBuffer(); gl.bindBuffer(target, b); gl.bufferData(target, new Type(data), gl.STATIC_DRAW); return b;
  };
  const attr = (name, size, stride = 0, offset = 0, divisor = 0) => {
    const l = gl.getAttribLocation(prog, name);
    gl.enableVertexAttribArray(l); gl.vertexAttribPointer(l, size, gl.FLOAT, false, stride * 4, offset * 4); gl.vertexAttribDivisor(l, divisor);
  };
  buf(pos, Float32Array); attr('a_pos', 3);
  buf(nor, Float32Array); attr('a_normal', 3);
  buf(idx, Uint16Array, gl.ELEMENT_ARRAY_BUFFER);
  buf(inst, Float32Array);
  [['a_off', 3, 0], ['a_scale', 3, 3], ['a_tone', 1, 6], ['a_live', 1, 7]].forEach(([n, s, o]) => attr(n, s, STRIDE, o, 1));
  const count = inst.length / STRIDE;
  const U = Object.fromEntries(['u_time', 'u_yaw', 'u_pitch', 'u_f', 'u_aspect', 'u_dist', 'u_shift', 'u_cell'].map(n => [n, gl.getUniformLocation(prog, n)]));

  gl.enable(gl.DEPTH_TEST);
  gl.clearColor(0, 0, 0, 0);

  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let w = 1, h = 1, dpr = 1, tiltX = 0, tiltY = 0, curX = 0, curY = 0, running = false, visible = true, raf = 0;

  function resize() {
    dpr = Math.min(devicePixelRatio || 1, 2);
    const r = canvas.getBoundingClientRect();
    w = Math.max(1, Math.round(r.width * dpr)); h = Math.max(1, Math.round(r.height * dpr));
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
    gl.viewport(0, 0, w, h);
  }

  function draw(t) {
    resize();
    const aspect = w / h;
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.uniform1f(U.u_time, t);
    gl.uniform1f(U.u_yaw, 0.62 + 0.16 * Math.sin(t * 0.2) + curX);
    gl.uniform1f(U.u_pitch, 0.66 + 0.04 * Math.sin(t * 0.27) + curY);
    // Fit the grid into the upper part of the poster, above the text panel.
    gl.uniform1f(U.u_f, 2.4 * Math.min(1, aspect / 1.15));
    gl.uniform1f(U.u_aspect, aspect);
    gl.uniform1f(U.u_dist, 34);
    gl.uniform2f(U.u_shift, 0.02, 0.46);
    gl.uniform1f(U.u_cell, 6.5 * dpr);
    gl.drawElementsInstanced(gl.TRIANGLES, idx.length, gl.UNSIGNED_SHORT, 0, count);
  }

  const start = performance.now();
  function frame(now) {
    raf = 0;
    curX += (tiltX - curX) * 0.05; curY += (tiltY - curY) * 0.05;
    draw((now - start) / 1000);
    if (running && visible) raf = requestAnimationFrame(frame);
  }
  const kick = () => { if (!raf) raf = requestAnimationFrame(frame); };

  function sync() {
    running = !reduced.matches;
    if (running) kick(); else draw(1.6);
  }

  new ResizeObserver(() => { if (!running) draw(1.6); }).observe(canvas);
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible && running) kick(); }).observe(art);
  reduced.addEventListener('change', sync);
  const poster = art.closest('.t-poster') || art;
  poster.addEventListener('pointermove', e => {
    const r = poster.getBoundingClientRect();
    tiltX = ((e.clientX - r.left) / r.width - 0.5) * 0.3;
    tiltY = ((e.clientY - r.top) / r.height - 0.5) * -0.2;
  });
  sync();
})();
