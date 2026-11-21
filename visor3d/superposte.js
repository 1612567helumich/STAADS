// Visor 3D · Superposte 20-02 (PCP-20-02-14893-2CROX, Grupo Polesa)
// Geometría tomada del plano de ensamble y detalles, hojas 1/2 y 2/2. Unidades del plano en mm; escena en metros, Y hacia arriba.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const mm = (v) => v / 1000;
const $ = (id) => document.getElementById(id);
const stage = $('stage'), overlay = $('overlay'), tip = $('tip');
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

// ---------- Datos del plano (mm) ----------
const P = {
  s1: { y0: 0, y1: 10300, d0: 440, d1: 273.3 },      // primera sección, D.E. entre caras
  s2: { y0: 9700, y1: 20000, d0: 296.6, d1: 130 },   // segunda sección, entra 600 sobre la primera
  t: 4.76,
  placa: { b: 620, t: 44.45, r: 44, hueco: 308, barreno: 60, cb: 589 },
  ancla: { d: 50.8, L: 2000, rosca: 254, pl: 150, plt: 25.4, plOff: 50, sobre: 76 },
  grout: 60,                                          // separación placa-concreto (tuerca de nivelación)
  escalones: { y0: 3000, paso: 400, hasta: 20000 - 800 },
  tuercasEmp: [10000 - 1143, 10000 - 381, 10000 + 381, 10000 + 1143],
  canales: [20000 - 126, 20000 - 126 - 699],
  niple: 20000 - 610,
  registro: 458,
};
// Ángulo en planta de la normal de cada cara de referencia (0 = +X). Cara 1 al frente (+Z), 3 izquierda, 5 atrás, 7 derecha.
const CARA = { 1: Math.PI / 2, 3: Math.PI, 5: -Math.PI / 2, 7: 0 };

const dAt = (y) => { const s = y >= P.s2.y0 ? P.s2 : P.s1; return s.d0 + (s.d1 - s.d0) * (y - s.y0) / (s.y1 - s.y0); };
const aAt = (y) => mm(dAt(y) / 2);   // apotema exterior a la altura y (mm) → m
const fmt = (n) => Math.round(n).toLocaleString('es-MX').replace(/,/g, ' ');

const BOM = [
  [1, 1, 'Primera sección del poste 440×273×10 300×4.76', 'A572', 450],
  [2, 1, 'Segunda sección del poste 296×130×10 300×4.76', 'A572', 266],
  [3, 1, 'Tapa corona 4.76 × ø147', 'A572', 1],
  [4, 1, 'Placa base cuadrada 620×620×44', 'A36', 105],
  [5, 1, 'Contra para tapa 4.76, 25×120', 'A36', 1],
  [6, 1, 'Niple de tubo ø50.8×102 para cableado', 'A36', 1],
  [7, 2, 'Canal 6″×2.05″, 0.260 m de largo', 'A36', 8],
  [8, 1, 'Registro tipo Hubbell con tapa', 'A36', 2],
  [9, 47, 'Porta escalón tipo N01, 4.76×38.1', 'A36', 7],
  [10, 47, 'Escalón de tornillo 15.8×179', 'A36', 24],
  [11, 8, 'Tuerca para empotramiento ø25.4 HH', 'A325', 2],
];

// ---------- Render ----------
// Resolución: máximo 1.5× la densidad de la pantalla; si los cuadros salen lentos al mover, baja mientras se mueve
// y vuelve a la resolución completa al soltar.
const DPR_MAX = Math.min(window.devicePixelRatio || 1, 1.5);
let renderer;
try {
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
} catch (e) {
  overlay.textContent = 'Este navegador no pudo iniciar WebGL. Prueba en otro navegador o activa la aceleración por hardware.';
  throw e;
}
window.__poste = { renderer };
renderer.setPixelRatio(DPR_MAX);
renderer.setClearColor(0x000000, 0);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
stage.prepend(renderer.domElement);

const labelRenderer = new CSS2DRenderer();
Object.assign(labelRenderer.domElement.style, { position: 'absolute', inset: '0', pointerEvents: 'none' });
$('labels').appendChild(labelRenderer.domElement);

const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.55;
pmrem.dispose();
const sun = new THREE.DirectionalLight(0xfff4e6, 1.9); sun.position.set(6, 14, 9); scene.add(sun);
const fill = new THREE.DirectionalLight(0xdbe8ff, 0.6); fill.position.set(-8, 4, -6); scene.add(fill);
scene.add(new THREE.HemisphereLight(0xe8f0ff, 0x6b5a4e, 0.45));

const camera = new THREE.PerspectiveCamera(35, 1, 0.05, 200);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; controls.dampingFactor = 0.12;
controls.minDistance = 0.25; controls.maxDistance = 90;
controls.autoRotateSpeed = 0.9;
// Navegación tipo CAD: botón izquierdo gira, rueda presionada (o botón derecho) desplaza, rueda hace zoom hacia el cursor.
controls.mouseButtons = { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.PAN, RIGHT: THREE.MOUSE.PAN };
controls.zoomToCursor = true;
renderer.domElement.addEventListener('mousedown', (e) => { if (e.button === 1) e.preventDefault(); });   // sin autodesplazamiento del navegador

// ---------- Materiales ----------
const MAT = {
  oxido: new THREE.MeshStandardMaterial({ color: 0x8e3a26, roughness: 0.58, metalness: 0.32, flatShading: true }),
  interior: new THREE.MeshStandardMaterial({ color: 0x5b4a42, roughness: 0.85, metalness: 0.15, flatShading: true }),
  oxidoAcc: new THREE.MeshStandardMaterial({ color: 0x86361f, roughness: 0.55, metalness: 0.3 }),
  galv: new THREE.MeshStandardMaterial({ color: 0xaab1b8, roughness: 0.34, metalness: 0.88 }),
  negro: new THREE.MeshStandardMaterial({ color: 0x3a3e43, roughness: 0.5, metalness: 0.75 }),
  rosca: new THREE.MeshStandardMaterial({ color: 0x5d6166, roughness: 0.85, metalness: 0.6, flatShading: true }),
  hueco: new THREE.MeshBasicMaterial({ color: 0x160a07 }),
  concreto: new THREE.MeshStandardMaterial({ color: 0x9c9a92, roughness: 1, metalness: 0, transparent: true, opacity: 0.15, depthWrite: false, side: THREE.DoubleSide }),
  ref: new THREE.MeshStandardMaterial({ color: 0x2f6497, roughness: 0.5, metalness: 0.2, transparent: true, opacity: 0.4, depthWrite: false }),
  hi: new THREE.MeshStandardMaterial({ color: 0xff9a4d, emissive: 0xd9480f, emissiveIntensity: 0.6, roughness: 0.5, metalness: 0.2 }),
  hiX: new THREE.MeshBasicMaterial({ color: 0xff8a3d, depthTest: false, transparent: true, opacity: 0.95 }),
};
const lineMat = new THREE.LineBasicMaterial({ color: 0x2f6497 });
const edgeMat = new THREE.LineBasicMaterial({ color: 0x8a8880, transparent: true, opacity: 0.5 });

// ---------- Geometrías compartidas (piezas repetidas, ya desplazadas a su lugar local) ----------
const at = (g, x = 0, y = 0, z = 0) => g.translate(x, y, z);
const rHex = (af) => af / 2 / Math.cos(Math.PI / 6);
const ANC = (() => {
  const A = P.ancla, yTop = mm(A.sobre), yBot = yTop - mm(A.L), yRos = yTop - mm(A.rosca);
  return { A, yTop, yBot, yRos, tp: mm(P.placa.t) };
})();
const G = {
  // Escalón: porta escalón soldado y tornillo ø16 × 203 con tuerca, disco y remate ø50
  porta: at(new THREE.BoxGeometry(mm(31), mm(60), mm(38)), mm(15.5)),
  escalon: mergeGeometries([
    at(new THREE.CylinderGeometry(mm(8), mm(8), mm(160), 14).rotateZ(Math.PI / 2), mm(111)),
    at(new THREE.CylinderGeometry(mm(13.8), mm(13.8), mm(14), 6).rotateZ(Math.PI / 2), mm(38)),
    at(new THREE.CylinderGeometry(mm(25), mm(25), mm(4), 28).rotateZ(Math.PI / 2), mm(191)),
    at(new THREE.SphereGeometry(mm(25), 28, 10, 0, Math.PI * 2, 0, Math.PI / 2).rotateZ(-Math.PI / 2).scale(0.4, 1, 1), mm(193)),
  ]),
  tuerca25: at(new THREE.CylinderGeometry(mm(23.8), mm(23.8), mm(25), 6).rotateZ(Math.PI / 2), mm(12.5)),
  barreno25: at(new THREE.CircleGeometry(mm(12.7), 18).rotateY(Math.PI / 2), mm(25.3)),
  ancla: at(new THREE.CylinderGeometry(mm(ANC.A.d / 2), mm(ANC.A.d / 2), ANC.yRos - ANC.yBot, 20), 0, (ANC.yRos + ANC.yBot) / 2),
  rosca: at(new THREE.CylinderGeometry(mm(ANC.A.d / 2) * 1.012, mm(ANC.A.d / 2) * 1.012, ANC.yTop - ANC.yRos, 20), 0, (ANC.yTop + ANC.yRos) / 2),
  tuercaNiv: at(new THREE.CylinderGeometry(rHex(mm(79.4)), rHex(mm(79.4)), mm(50.8), 6), 0, -ANC.tp - mm(25.4 + 0.5)),
  tuercaSup: at(new THREE.CylinderGeometry(rHex(mm(79.4)), rHex(mm(79.4)), mm(50.8), 6), 0, mm(25.4 + 0.3)),
  placaAncla: at(new THREE.BoxGeometry(mm(ANC.A.pl), mm(ANC.A.plt), mm(ANC.A.pl)), 0, ANC.yBot + mm(ANC.A.plOff + ANC.A.plt / 2)),
};
const SHARED = new Set(Object.values(G));

const box = (x, y, z, mat) => new THREE.Mesh(new THREE.BoxGeometry(x, y, z), mat);
const cylY = (r, h, mat, seg = 24) => new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, seg), mat);
const hexY = (af, h, mat) => cylY(rHex(af), h, mat, 6);

// Tubo cónico poligonal: N caras, diámetros entre caras, espesor t. Normales planas por cara.
function tuboPoligonal(N, s, t) {
  const ext = [], inn = [];   // grupo 0: exterior pintado · grupo 1: interior y cantos (se ven en el corte)
  const k = 1 / Math.cos(Math.PI / N);
  const ang = (j) => (j + 0.5) * 2 * Math.PI / N;
  const y0 = mm(s.y0), y1 = mm(s.y1);
  const ro0 = mm(s.d0 / 2) * k, ro1 = mm(s.d1 / 2) * k, ri0 = mm(s.d0 / 2 - t) * k, ri1 = mm(s.d1 / 2 - t) * k;
  const p = (r, a, y) => [r * Math.cos(a), y, r * Math.sin(a)];
  const tri = (arr, a, b, c) => arr.push(...a, ...b, ...c);
  for (let j = 0; j < N; j++) {
    const A = ang(j), B = ang(j + 1);
    const ob0 = p(ro0, A, y0), ob1 = p(ro0, B, y0), ot0 = p(ro1, A, y1), ot1 = p(ro1, B, y1);
    const ib0 = p(ri0, A, y0), ib1 = p(ri0, B, y0), it0 = p(ri1, A, y1), it1 = p(ri1, B, y1);
    tri(ext, ob0, ot1, ob1); tri(ext, ob0, ot0, ot1);   // cara exterior
    tri(inn, ib0, ib1, it1); tri(inn, ib0, it1, it0);   // cara interior
    tri(inn, ob0, ob1, ib1); tri(inn, ob0, ib1, ib0);   // canto inferior
    tri(inn, ot0, it1, ot1); tri(inn, ot0, it0, it1);   // canto superior
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute([...ext, ...inn], 3));
  g.addGroup(0, ext.length / 3, 0);
  g.addGroup(ext.length / 3, inn.length / 3, 1);
  g.computeVertexNormals();
  return g;
}

function placaBaseGeo() {
  const { b, r, hueco, barreno, cb, t } = P.placa;
  const h = mm(b / 2), R = mm(r);
  const s = new THREE.Shape();
  s.moveTo(-h + R, -h);
  s.lineTo(h - R, -h); s.absarc(h - R, -h + R, R, -Math.PI / 2, 0, false);
  s.lineTo(h, h - R); s.absarc(h - R, h - R, R, 0, Math.PI / 2, false);
  s.lineTo(-h + R, h); s.absarc(-h + R, h - R, R, Math.PI / 2, Math.PI, false);
  s.lineTo(-h, -h + R); s.absarc(-h + R, -h + R, R, Math.PI, Math.PI * 1.5, false);
  const hole = (x, y, d) => { const q = new THREE.Path(); q.absarc(x, y, mm(d / 2), 0, Math.PI * 2, true); s.holes.push(q); };
  hole(0, 0, hueco);
  const e = mm(cb / 2) * Math.SQRT1_2;
  for (const [x, y] of [[e, e], [-e, e], [-e, -e], [e, -e]]) hole(x, y, barreno);
  const g = new THREE.ExtrudeGeometry(s, { depth: mm(t), bevelEnabled: false, curveSegments: 28 });
  g.rotateX(-Math.PI / 2).translate(0, -mm(t), 0);
  return g;
}

function almaCanalGeo() {
  const w = mm(130), h = mm(76);
  const s = new THREE.Shape();
  s.moveTo(-w, -h); s.lineTo(w, -h); s.lineTo(w, h); s.lineTo(-w, h); s.closePath();
  for (const cx of [mm(-84), mm(84)]) {   // galuces 22 × 38 a 168 c/c
    const q = new THREE.Path();
    q.absarc(cx, mm(8), mm(11), 0, Math.PI, false);
    q.absarc(cx, mm(-8), mm(11), Math.PI, Math.PI * 2, false);
    q.closePath(); s.holes.push(q);
  }
  return new THREE.ExtrudeGeometry(s, { depth: mm(5.1), bevelEnabled: false, curveSegments: 12 }).rotateY(Math.PI / 2);
}

// ---------- Escena ----------
const groups = {};
let pickables = [];
let sides = 12;
const labels = [];
const dummy = new THREE.Object3D();

function tag(m, fig, name, extra = '') { m.userData = { fig, name, extra }; pickables.push(m); return m; }
// Posición y giro sobre una cara a la altura y (mm): el eje local +X apunta hacia fuera de la cara.
function onFace(cara, yMM) { const th = CARA[cara], a = aAt(yMM); return [Math.cos(th) * a, mm(yMM), Math.sin(th) * a, -th]; }
function enCara(obj, cara, yMM) { const [x, y, z, ry] = onFace(cara, yMM); obj.position.set(x, y, z); obj.rotation.y = ry; return obj; }
// Pieza repetida en una sola llamada de dibujo. items: nombre y dato de cada copia, para identificarla con el cursor.
function instanced(geo, mat, places, fig = null, items = null) {
  const im = new THREE.InstancedMesh(geo, mat, places.length);
  places.forEach(([x, y, z, ry = 0], i) => { dummy.position.set(x, y, z); dummy.rotation.set(0, ry, 0); dummy.updateMatrix(); im.setMatrixAt(i, dummy.matrix); });
  im.instanceMatrix.needsUpdate = true;
  im.computeBoundingSphere(); im.computeBoundingBox();
  if (fig != null) { im.userData = { fig, items }; pickables.push(im); }
  return im;
}

// win: [mín, máx] de distancia de la cámara en que se muestra; by 'self' mide a la etiqueta, 'target' al punto de giro.
function label(html, pos, { cls = '', win = [0, Infinity], by = 'self', gate = null, anchor = [0.5, 0.5] } = {}) {
  const el = document.createElement('div');
  el.className = 'lbl ' + cls; el.innerHTML = html;
  const o = new CSS2DObject(el);
  o.position.set(...pos); o.center.set(...anchor);
  o.userData = { win, by, gate };
  groups.dim.add(o); labels.push(o);
  return o;
}
function cota(x, z, y0, y1, html, { side = -1, win = [0, Infinity] } = {}) {
  const tk = 0.07, pts = [x, y0, z, x, y1, z, x - tk, y0, z, x + tk, y0, z, x - tk, y1, z, x + tk, y1, z];
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
  const l = new THREE.LineSegments(g, lineMat); l.userData = { win, by: 'target' }; groups.dim.add(l);
  label(html, [x + side * 0.06, (y0 + y1) / 2, z], { cls: 'dim', win, by: 'target', anchor: [side < 0 ? 1 : 0, 0.5] });
}

function disposeGroup(g) {
  g.traverse((o) => {
    if (o.isInstancedMesh) o.dispose();
    if (o.geometry && !SHARED.has(o.geometry)) o.geometry.dispose();
  });
  for (const c of [...g.children]) g.remove(c);
}

function build() {
  for (const k of ['poste', 'acc', 'cim', 'cru', 'dim']) {
    if (!groups[k]) { groups[k] = new THREE.Group(); scene.add(groups[k]); } else disposeGroup(groups[k]);
  }
  for (const l of labels) l.element.remove();
  labels.length = 0; pickables = [];
  const { poste, acc, cim, cru } = groups;

  // Fuste: dos secciones, la segunda abraza 600 mm a la primera
  poste.add(tag(new THREE.Mesh(tuboPoligonal(sides, P.s1, P.t), [MAT.oxido, MAT.interior]), 1, 'Primera sección', '440 → 273.3 · 10 300 · cal. 4.76'));
  poste.add(tag(new THREE.Mesh(tuboPoligonal(sides, P.s2, P.t), [MAT.oxido, MAT.interior]), 2, 'Segunda sección', '296.6 → 130 · 10 300 · cal. 4.76'));

  poste.add(tag(new THREE.Mesh(placaBaseGeo(), MAT.oxidoAcc), 4, 'Placa base', '620 × 620 × 44.45 · 4 barrenos ø60 · hueco ø308'));

  const tapa = tag(cylY(mm(73.5), mm(4.76), MAT.oxidoAcc, 48), 3, 'Tapa corona', 'ø147 × 4.76 · barreno ø16');
  tapa.position.y = mm(20000 + 2.38); poste.add(tapa);
  const tornillo = tag(hexY(mm(24), mm(10), MAT.galv), 3, 'Tornillo de tapa', 'a la contra con machuelo');
  tornillo.position.y = mm(20000 + 4.76 + 5); poste.add(tornillo);
  const contra = tag(box(mm(120), mm(4.76), mm(25), MAT.oxidoAcc), 5, 'Contra para tapa', '4.76 × 25 × 120, soldada por dentro');
  contra.position.y = mm(20000 - 13 - 2.4); poste.add(contra);

  // Escalones: cada 400 mm alternados en caras 3 y 7, de 3 000 hasta 800 mm de la corona
  {
    const places = [], esc = [], porta = [];
    let n = 0;
    for (let y = P.escalones.y0; y <= P.escalones.hasta; y += P.escalones.paso) {
      n++;
      const cara = n % 2 ? 7 : 3, extra = `h = ${fmt(y)} mm · cara ${cara}`;
      places.push(onFace(cara, y));
      esc.push({ name: `Escalón ${n}`, extra });
      porta.push({ name: `Porta escalón ${n}`, extra });
    }
    acc.add(instanced(G.porta, MAT.oxidoAcc, places, 9, porta), instanced(G.escalon, MAT.galv, places, 10, esc));
    $('spec-esc').innerHTML = `${n} <small>@ 400 alt.</small>`;
  }

  // Tuercas de empotramiento: 4 niveles × caras 3 y 7
  {
    const places = [], items = [];
    for (const y of P.tuercasEmp) for (const cara of [3, 7]) {
      places.push(onFace(cara, y));
      items.push({ name: 'Tuerca de empotramiento ø25.4', extra: `h = ${fmt(y)} mm · cara ${cara}` });
    }
    acc.add(instanced(G.tuerca25, MAT.galv, places, 11, items), instanced(G.barreno25, MAT.hueco, places));
  }

  // Registro Hubbell en cara 3
  {
    const g = new THREE.Group(), ex = `centro a ${P.registro} mm · cara 3`;
    const marco = tag(box(mm(12), mm(190), mm(112), MAT.oxidoAcc), 8, 'Registro Hubbell', ex); marco.position.x = mm(6);
    const tapaR = tag(box(mm(5), mm(160), mm(84), MAT.oxidoAcc), 8, 'Registro Hubbell (tapa)', ex); tapaR.position.x = mm(14.5);
    g.add(marco, tapaR);
    for (const yy of [-62, 62]) { const t = tag(hexY(mm(11), mm(4), MAT.galv), 8, 'Registro Hubbell', ex); t.rotation.z = Math.PI / 2; t.position.set(mm(19), mm(yy), 0); g.add(t); }
    acc.add(enCara(g, 3, P.registro));
  }

  // Canales 6" en cara 1 para la cruceta (galuces a 699 c/c)
  const alma = almaCanalGeo();
  P.canales.forEach((y, i) => {
    const g = new THREE.Group(), ex = `${i ? 'inferior' : 'superior'} · eje a ${fmt(20000 - y)} mm de la corona · cara 1`;
    const w = tag(new THREE.Mesh(alma, MAT.oxidoAcc), 7, 'Canal 6″ × 260', ex); w.position.x = mm(27 - 5.1);
    g.add(w);
    for (const s of [-1, 1]) { const f = tag(box(mm(52), mm(8.7), mm(260), MAT.oxidoAcc), 7, 'Canal 6″ × 260', ex); f.position.set(mm(1), s * mm(76 - 4.35), 0); g.add(f); }
    acc.add(enCara(g, 1, y));
  });

  // Niple para cableado en cara 7
  {
    const g = new THREE.Group(), ex = 'ø50.8 × 102 · cara 7 · altura aproximada';
    const tubo = tag(new THREE.Mesh(new THREE.CylinderGeometry(mm(25.4), mm(25.4), mm(51), 28, 1, true).rotateZ(Math.PI / 2), MAT.oxidoAcc), 6, 'Niple para cableado', ex);
    tubo.position.x = mm(25.5);
    const fondo = new THREE.Mesh(new THREE.CircleGeometry(mm(21), 24).rotateY(Math.PI / 2), MAT.hueco); fondo.position.x = mm(8);
    g.add(tubo, fondo); acc.add(enCara(g, 7, P.niple));
  }

  // Anclas, tuercas 2H y dado (cimentación)
  {
    const e = mm(P.placa.cb / 2) * Math.SQRT1_2;
    const esquinas = [[e, 0, e], [-e, 0, e], [-e, 0, -e], [e, 0, -e]];
    const cuatro = (name, extra) => esquinas.map(() => ({ name, extra }));
    const exA = 'redondo A36 ø50.8 × 2 000 · rosca 254 · PL 150×150×25.4';
    cim.add(
      instanced(G.ancla, MAT.negro, esquinas, 'A', cuatro('Ancla', exA)),
      instanced(G.rosca, MAT.rosca, esquinas, 'A', cuatro('Ancla (zona roscada)', exA)),
      instanced(G.tuercaNiv, MAT.negro, esquinas, 'A', cuatro('Tuerca 2H de nivelación', 'ø2″')),
      instanced(G.tuercaSup, MAT.negro, esquinas, 'A', cuatro('Tuerca 2H superior', 'ø2″')),
      instanced(G.placaAncla, MAT.negro, esquinas, 'A', cuatro('Placa de ancla', '150 × 150 × 25.4')),
    );
    const yC = -ANC.tp - mm(P.grout), hD = 2.3;
    const dado = tag(new THREE.Mesh(new THREE.BoxGeometry(1, hD, 1), MAT.concreto), 'D', 'Dado de concreto', 'referencia, sin cotas en el plano');
    dado.position.y = yC - hD / 2; dado.renderOrder = 2;
    const aristas = new THREE.LineSegments(new THREE.EdgesGeometry(dado.geometry), edgeMat); aristas.position.copy(dado.position);
    cim.add(dado, aristas);
  }

  // Cruceta de referencia (3 000 × 800) atornillada a los canales, en una sola pieza de dibujo
  {
    const T = 0.076, W = 3.0, yT = 20, yB = 19.2;
    const zP = aAt(P.canales[1]) + mm(27) + mm(6), zF = zP + 0.006 + T / 2;
    const partes = [at(new THREE.BoxGeometry(0.22, 0.95, 0.012), 0, 19.525, zP)];
    for (const y of [yT - T / 2, yB + T / 2]) partes.push(at(new THREE.BoxGeometry(W, T, T), 0, y, zF));
    for (const x of [-W / 2 + T / 2, -0.75, 0, 0.75, W / 2 - T / 2]) partes.push(at(new THREE.BoxGeometry(T, 0.8 - 2 * T, T), x, (yT + yB) / 2, zF));
    cru.add(tag(new THREE.Mesh(mergeGeometries(partes), MAT.ref), 'R', 'Cruceta 3 000 × 800 con placa de montaje', 'referencia: no está en la lista de materiales'));
    for (const g of partes) g.dispose();
  }

  // Cotas y etiquetas
  const lejos = [9, Infinity];   // cotas generales: solo con la vista abierta
  cota(-0.95, 0, 0, 20, '<b>Total</b>20 000', { win: lejos });
  cota(-0.62, 0, 0, 10.3, '<b>Sección 1</b>10 300', { win: lejos });
  cota(-0.48, 0, 9.7, 20, '<b>Sección 2</b>10 300', { win: lejos });
  cota(0.42, 0, 9.7, 10.3, '<b>Empotramiento</b>600', { side: 1 });
  cota(0.55, 0, 0, 3, '<b>1er escalón</b>3 000', { side: 1, win: [4, 30] });
  label('<b>Corona</b>ø130', [-0.16, 20.12, 0], { anchor: [1, 0.5] });
  label('<b>Base</b>ø440', [-0.3, 0.16, 0], { anchor: [1, 0.5] });
  label('<b>Placa base</b>620 × 620 × 44.45', [0.36, -0.02, 0.36], { anchor: [0, 0.5], win: [0, 7] });
  label('<b>Registro Hubbell</b>a 458', [-0.32, 0.46, 0], { anchor: [1, 0.5], win: [0, 6], gate: 'acc' });
  label('<b>Niple</b>ø50.8 × 102', [0.2, mm(P.niple), 0], { anchor: [0, 0.5], win: [0, 5], gate: 'acc' });
  label('<b>Canales C6</b>699 c/c', [0.2, 19.53, 0.12], { anchor: [0, 0.5], win: [0, 5], gate: 'acc' });
  label('<b>Tuercas de empotre</b>8 × ø25.4 HH', [0.25, 11.15, 0], { anchor: [0, 0.5], win: [0, 6], gate: 'acc' });
  label('<b>Anclas</b>4 × ø50.8 × 2 000 · 2H', [0.42, -0.95, 0.3], { anchor: [0, 0.5], win: [0, 9], gate: 'cim' });
  label('<b>Dado</b>referencia', [-0.52, -1.6, 0.5], { cls: 'ref', anchor: [1, 0.5], win: [0, 9], gate: 'cim' });
  label('<b>Cruceta</b>3 000 × 800 · ref.', [0.9, 20.14, 0.15], { cls: 'ref', anchor: [0.5, 1], win: [0, 14], gate: 'cru' });
  for (const c of [1, 3, 5, 7]) {
    const th = CARA[c], r = 0.36;
    label(`<b>Cara</b>${c}`, [Math.cos(th) * r, 1.25, Math.sin(th) * r], { win: [0, 4.5] });
  }

  applyLayers(); applyTheme();
  if (sel != null) { const s = sel; sel = null; select(s, false); }
  dirty = true;
}

// ---------- Capas, tema, selección ----------
const tg = { acc: $('tg-acc'), cim: $('tg-cim'), cru: $('tg-cru'), cot: $('tg-cot'), cor: $('tg-cor'), giro: $('tg-giro') };
const corte = new THREE.Plane(new THREE.Vector3(0, 0, -1), 0);   // quita la mitad frontal (z > 0)
function applyLayers() {
  groups.acc.visible = tg.acc.checked; groups.cim.visible = tg.cim.checked; groups.cru.visible = tg.cru.checked;
  groups.dim.visible = tg.cot.checked;
  renderer.clippingPlanes = tg.cor.checked ? [corte] : [];
  controls.autoRotate = tg.giro.checked;
  dirty = true;
}
for (const el of Object.values(tg)) el.addEventListener('change', applyLayers);

let grid = null;
function applyTheme() {
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim() || '#888';
  const ref = new THREE.Color(css('--ref'));
  lineMat.color.copy(ref); MAT.ref.color.copy(ref);
  if (grid) { scene.remove(grid); grid.geometry.dispose(); grid.material.dispose(); }
  grid = new THREE.GridHelper(16, 32, new THREE.Color(css('--muted')), new THREE.Color(css('--line')));
  grid.position.y = -mm(P.placa.t) - mm(P.grout) - 0.0005;
  grid.material.transparent = true; grid.material.opacity = 0.75; grid.material.depthWrite = false;
  scene.add(grid);
  dirty = true;
}
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyTheme);
new MutationObserver(applyTheme).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

const bomBody = $('bom');
bomBody.innerHTML = BOM.map(([f, c, d, a, p]) =>
  `<tr tabindex="0" data-fig="${f}"><td class="fig">${f}</td><td class="n">${c}</td><td>${d}</td><td>${a}</td><td class="n">${p}</td></tr>`).join('');
const FIG_NAME = Object.fromEntries(BOM.map(([f, , d]) => [f, d]));

let sel = null;
function select(fig, fly) {
  for (const m of pickables) if (m.userData.orig) { m.material = m.userData.orig; m.userData.orig = null; m.renderOrder = 0; }
  if (fig == null || fig === sel) { sel = null; markRows(); dirty = true; return; }
  sel = fig;
  if ([6, 7, 8, 9, 10, 11].includes(fig) && !tg.acc.checked) { tg.acc.checked = true; applyLayers(); }
  if ((fig === 'A' || fig === 'D') && !tg.cim.checked) { tg.cim.checked = true; applyLayers(); }
  const hits = pickables.filter((m) => m.userData.fig === fig);
  for (const m of hits) { m.userData.orig = m.material; m.material = fig === 5 ? MAT.hiX : MAT.hi; if (fig === 5) m.renderOrder = 10; }
  markRows();
  if (fly && hits.length) {
    const b = new THREE.Box3(); for (const m of hits) b.expandByObject(m);
    const c = b.getCenter(new THREE.Vector3()), s = b.getSize(new THREE.Vector3());
    const dir = camera.position.clone().sub(controls.target).normalize();
    if (Math.abs(dir.y) > 0.95) dir.set(1, 0.3, 1.4).normalize();
    flyTo(c, dir, Math.max(s.y, 0.5) * 1.25, Math.max(s.x, s.z, 0.5) * 1.5);
  }
  dirty = true;
}
function markRows() { for (const tr of bomBody.rows) tr.classList.toggle('on', String(sel) === tr.dataset.fig); }
bomBody.addEventListener('click', (e) => { const tr = e.target.closest('tr'); if (tr) select(Number(tr.dataset.fig), true); });
bomBody.addEventListener('keydown', (e) => { if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('tr')) { e.preventDefault(); select(Number(e.target.dataset.fig), true); } });

// ---------- Vistas ----------
const VIEWS = {
  todo: { t: [0, 9.0, 0], d: [1, 0.28, 1.45], h: 25.5, w: 4 },
  corona: { t: [0, 19.6, 0.15], d: [1.15, 0.42, 1.5], h: 1.9, w: 3.7 },
  empotre: { t: [0, 10.0, 0], d: [0.6, 0.15, 1.4], h: 3.2, w: 1.2 },
  base: { t: [0, 0.32, 0], d: [-1.0, 0.55, 1.4], h: 1.6, w: 1.6 },
  planta: { t: [0, 17.6, 0], d: [0, 1, 0.0001], h: 3.8, w: 3.8 },
  anclas: { t: [0, -0.85, 0], d: [1.1, 0.25, 1.4], h: 2.7, w: 1.4 },
};
let tw = null;
function fitDist(h, w) {
  const t = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
  return Math.max(h / 2 / t, w / 2 / (t * camera.aspect));
}
function flyTo(target, dir, h, w) {
  const tt = target.clone(), tp = target.clone().add(dir.clone().normalize().multiplyScalar(fitDist(h, w)));
  if (reduceMotion) { controls.target.copy(tt); camera.position.copy(tp); controls.update(); dirty = true; return; }
  tw = { t0: performance.now(), ft: controls.target.clone(), fp: camera.position.clone(), tt, tp };
}
function view(name, instant = false) {
  const v = VIEWS[name];
  if (name === 'anclas' && !tg.cim.checked) { tg.cim.checked = true; applyLayers(); }
  const t = new THREE.Vector3(...v.t), d = new THREE.Vector3(...v.d);
  if (instant) { controls.target.copy(t); camera.position.copy(t.clone().add(d.normalize().multiplyScalar(fitDist(v.h, v.w)))); controls.update(); }
  else flyTo(t, d, v.h, v.w);
  for (const b of document.querySelectorAll('#views .btn')) b.setAttribute('aria-pressed', String(b.dataset.view === name));
}
$('views').addEventListener('click', (e) => { const b = e.target.closest('[data-view]'); if (b) view(b.dataset.view); });
controls.addEventListener('start', () => {
  tw = null;
  for (const b of document.querySelectorAll('#views .btn')) b.setAttribute('aria-pressed', 'false');
});

// Lados del polígono
for (const nSides of [12, 8]) {
  $('lados-' + nSides).addEventListener('click', () => {
    if (sides === nSides) return;
    sides = nSides;
    $('lados-12').setAttribute('aria-pressed', String(sides === 12));
    $('lados-8').setAttribute('aria-pressed', String(sides === 8));
    $('spec-lados').textContent = `${sides} lados`;
    build();
  });
}

// ---------- Identificar piezas ----------
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
let stageRect = stage.getBoundingClientRect();
const shown = (o) => { for (; o; o = o.parent) if (!o.visible) return false; return true; };
function pick(ev) {
  const x = ev.clientX - stageRect.left, y = ev.clientY - stageRect.top;
  ndc.set((x / stageRect.width) * 2 - 1, -(y / stageRect.height) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  const hit = ray.intersectObjects(pickables, false).find((h) => shown(h.object) && !(tg.cor.checked && h.point.z > 0));
  return hit ? { obj: hit.object, inst: hit.instanceId, x, y } : null;
}
let tipKey = null;
function showTip(h) {
  if (!h) { if (!tip.hidden) tip.hidden = true; tipKey = null; return; }
  const u = h.obj.userData, it = u.items ? u.items[h.inst] : u;
  const key = h.obj.id + ':' + (h.inst ?? '');
  if (key !== tipKey) {
    tipKey = key;
    const fig = typeof u.fig === 'number' ? `Fig. ${u.fig} · ` : '';
    tip.innerHTML = `${it.name}<small>${fig}${it.extra || FIG_NAME[u.fig] || ''}</small>`;
  }
  tip.style.transform = `translate(${Math.min(h.x, stageRect.width - 270) + 12}px, ${h.y + 12}px)`;
  tip.hidden = false;
}
let hoverEv = null, hoverAt = 0, downAt = null;
renderer.domElement.addEventListener('pointermove', (e) => { if (e.pointerType === 'mouse' && !e.buttons) hoverEv = e; else hoverEv = null; });
renderer.domElement.addEventListener('pointerleave', () => { hoverEv = null; showTip(null); });
renderer.domElement.addEventListener('pointerdown', (e) => { downAt = [e.clientX, e.clientY]; showTip(null); });
renderer.domElement.addEventListener('pointerup', (e) => {
  if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 5) return;
  const h = pick(e);
  showTip(h);
  select(h ? h.obj.userData.fig : null, false);
});

// ---------- Bucle: dibuja solo cuando algo cambia ----------
let dirty = true, moving = false, lastRender = 0, slow = 0, dprMove = DPR_MAX;
const resize = () => {
  stageRect = stage.getBoundingClientRect();
  const w = stageRect.width, h = stageRect.height;
  if (!w || !h) return;
  renderer.setSize(w, h); labelRenderer.setSize(w, h);
  camera.aspect = w / h; camera.updateProjectionMatrix(); dirty = true;
};
new ResizeObserver(resize).observe(stage);

const ease = (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
const tmp = new THREE.Vector3();
function draw() {
  // Planos de recorte cercano/lejano según el zoom: buena precisión de profundidad sin búfer logarítmico.
  const d = camera.position.distanceTo(controls.target);
  const near = THREE.MathUtils.clamp(d * 0.004, 0.004, 0.3), far = d * 3 + 60;
  if (Math.abs(camera.near - near) > near * 0.2 || Math.abs(camera.far - far) > far * 0.2) {
    camera.near = near; camera.far = far; camera.updateProjectionMatrix();
  }
  for (const o of groups.dim.children) {
    const u = o.userData;
    if (!u.win) continue;
    const dd = u.by === 'self' ? camera.position.distanceTo(o.getWorldPosition(tmp)) : d;
    o.visible = (u.gate ? groups[u.gate].visible : true) && dd >= u.win[0] && dd < u.win[1];
  }
  renderer.render(scene, camera);
  labelRenderer.render(scene, camera);
}
function loop(now) {
  requestAnimationFrame(loop);
  if (tw) {
    const k = Math.min(1, (now - tw.t0) / 900), e = ease(k);
    controls.target.lerpVectors(tw.ft, tw.tt, e); camera.position.lerpVectors(tw.fp, tw.tp, e);
    if (k === 1) tw = null;
    dirty = true;
  }
  if (controls.update()) dirty = true;
  if (hoverEv && !moving && now - hoverAt > 50) { hoverAt = now; showTip(pick(hoverEv)); hoverEv = null; }
  if (!dirty) {
    if (moving && now - lastRender > 250) {   // terminó el movimiento: un cuadro nítido
      moving = false; slow = 0;
      if (renderer.getPixelRatio() !== DPR_MAX) { renderer.setPixelRatio(DPR_MAX); draw(); }
    }
    return;
  }
  dirty = false;
  if (!moving) {
    moving = true;
    if (renderer.getPixelRatio() !== dprMove) renderer.setPixelRatio(dprMove);
  } else {
    if (now - lastRender > 30) slow++; else if (slow > 0) slow--;
    if (slow >= 8 && dprMove > 0.75) { dprMove = Math.max(0.75, dprMove - 0.25); renderer.setPixelRatio(dprMove); slow = 0; }
  }
  lastRender = now;
  draw();
}

build();
resize();
view('todo', true);
requestAnimationFrame(loop);
overlay.hidden = true;
