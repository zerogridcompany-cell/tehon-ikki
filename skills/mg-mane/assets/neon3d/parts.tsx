// 物の部品：車（セダン）・札の板・白い人・映り込み・光の円すい・煙・粒の柱
import React, {useMemo, useContext} from 'react';
import * as THREE from 'three';
import {useThree} from '@react-three/fiber';
import {sedan, wheelOne, caliper, WXF, WXR, WR, PROF, Seg} from './geo';
import {Glow, ACCENT, MirCtx} from './three';
import type {Tx} from './labels';
type P3 = [number, number, number];
export const COL: Record<string, [string, string]> = {cyan: [ACCENT.cyan, ACCENT.cyanCore], red: [ACCENT.red, ACCENT.redCore], orange: [ACCENT.orange, ACCENT.orangeCore], yellow: [ACCENT.yellow, ACCENT.yellowCore], teal: [ACCENT.teal, ACCENT.tealCore], white: [ACCENT.white, ACCENT.whiteCore]};

const CAR = sedan(); const WL = wheelOne(1), WRt = wheelOne(-1), CL = caliper(1), CR = caliper(-1);
// 車の黒い中身（後ろの線を隠す）＝横の輪郭を押し出した形
const FILL = (() => {
  const s = new THREE.Shape(); const P = PROF.map(([x, y]) => [x * 0.985, 0.36 + (y - 0.36) * 0.98]);
  s.moveTo(P[0][0], P[0][1]); for (const p of P.slice(1)) s.lineTo(p[0], p[1]); s.closePath();
  const g = new THREE.ExtrudeGeometry(s, {depth: 1.76, bevelEnabled: false}); g.translate(0, 0, -0.88); return g;
})();
// 車：前＝＋x。spin＝車輪の回り（ラジアン）・fill＝黒で中を埋める
export const Car: React.FC<{pos?: P3; ry?: number; rx?: number; s?: number; op?: number; col?: string; spin?: number; fill?: number; w?: number; star?: number; draw?: number}> =
  ({pos = [0, 0, 0], ry = 0, rx = 0, s = 1, op = 1, col = 'cyan', spin = 0, fill = 0.92, w = 0.02, star = 1, draw = 1}) => {
  const mir = useContext(MirCtx);
  const [c, k] = COL[col];
  const fm = useMemo(() => new THREE.MeshBasicMaterial({color: '#000306', transparent: true, depthWrite: true, toneMapped: false}), []);
  if (op <= 0.002) return null;
  fm.opacity = fill * op * (mir ? 0.5 : 1); fm.depthWrite = !mir && op > 0.9;
  const wheel = (x: number, seg: Seg, cal: Seg) => <group position={[x, WR, 0]} rotation={[0, 0, -spin]}><Glow seg={seg} color={c} core={k} op={op} w={w} draw={draw} /><group rotation={[0, 0, spin]}><Glow seg={cal} color={ACCENT.red} core={ACCENT.redCore} op={op} w={w * 1.3} /></group></group>;
  return <group position={pos} rotation={[rx, ry, 0]} scale={s}>
    {fill > 0 && <mesh geometry={FILL} material={fm} renderOrder={mir ? -32 : -5}  />}
    <Glow seg={CAR.body} color={c} core={k} op={op} w={w} draw={draw} />
    <Glow seg={CAR.red} color={ACCENT.red} core={ACCENT.redCore} op={op} w={w * 1.2} />
    <Glow seg={CAR.lamp} color="#9fe6ff" core="#e8fbff" op={op * 0.8} w={w} halo={0.12} />
    {star > 0 && <Glow seg={CAR.star} color="#e0f6ff" core="#ffffff" op={op * star} w={w * 1.1} halo={0.12} />}
    {wheel(WXF, WL, CL)}{wheel(WXR, WL, CL)}{wheel(WXF, WRt, CR)}{wheel(WXR, WRt, CR)}
  </group>;
};

// 映り込み（床の下に逆さに・暗く）
export const Refl: React.FC<{children: React.ReactNode; y?: number}> = ({children, y = 0}) => <>
  {children}
  <MirCtx.Provider value={true}><group position={[0, y * 2, 0]} scale={[1, -1, 1]}>{children}</group></MirCtx.Provider>
</>;

// 札の板（three の面に絵を貼る）。bb＝カメラに向ける
export const Board: React.FC<{tx: Tx; pos: P3; h: number; op?: number; bb?: boolean; rot?: number[]; s?: number; add?: boolean}> = ({tx, pos, h, op = 1, bb = false, rot, s = 1, add = false}) => {
  const {camera} = useThree(); const mir = useContext(MirCtx);
  const mat = useMemo(() => new THREE.MeshBasicMaterial({transparent: true, depthWrite: false, toneMapped: false, side: THREE.DoubleSide}), []);
  if (op <= 0.002) return null;
  mat.map = tx.t; mat.opacity = Math.min(1, op) * (mir ? 0.3 : 1); mat.blending = add ? THREE.AdditiveBlending : THREE.NormalBlending; mat.needsUpdate = mat.userData.m !== tx.t; mat.userData.m = tx.t;
  const w = h * tx.w / tx.h;
  const q = bb ? camera.quaternion.clone() : new THREE.Quaternion().setFromEuler(new THREE.Euler(...((rot || [0, 0, 0]) as [number, number, number])));
  if (!mir && op > 0.5 && (window as any).__cutcheck) {
    const cs = [[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]].map(([x, y]) => new THREE.Vector3(x * w * s, y * h * s, 0).applyQuaternion(q).add(new THREE.Vector3(...pos)).project(camera));
    const inn = cs.filter((v) => Math.abs(v.x) <= 1 && Math.abs(v.y) <= 1 && v.z < 1).length;
    if (inn > 0 && inn < 4) console.log('DBG CUT ' + (tx.k || '?') + ' x' + cs.map((v) => v.x.toFixed(2)).join(','));
  }
  return <mesh position={pos} quaternion={q} scale={[w * s, h * s, 1]} material={mat} renderOrder={mir ? -28 : 10}><planeGeometry args={[1, 1]} /></mesh>;
};

// 白い人（体＝回した形・頭＝球）。phone＝手を上げてスマホ（光る）
const BODY = new THREE.LatheGeometry([[0, 0], [0.34, 0], [0.36, 0.05], [0.37, 0.7], [0.35, 0.86], [0.29, 0.97], [0.18, 1.03], [0.0, 1.05]].map(([x, y]) => new THREE.Vector2(x, y)), 40);
const HEAD = new THREE.SphereGeometry(0.26, 40, 24);
const ARM = new THREE.CapsuleGeometry(0.07, 0.5, 6, 12);
export const Person: React.FC<{pos?: P3; ry?: number; s?: number; op?: number; arm?: number; flash?: number}> = ({pos = [0, 0, 0], ry = 0, s = 1, op = 1, arm = 0, flash = 0}) => {
  const mir = useContext(MirCtx);
  const mb = useMemo(() => new THREE.MeshStandardMaterial({color: '#d8dada', emissive: '#8a8e8e', emissiveIntensity: 0.55, roughness: 0.5, metalness: 0, transparent: true}), []);
  const mf = useMemo(() => new THREE.MeshBasicMaterial({color: '#ffffff', transparent: true, toneMapped: false}), []);
  if (op <= 0.002) return null;
  mb.opacity = op * (mir ? 0.3 : 1); mb.depthWrite = op > 0.98 && !mir; mf.opacity = flash * op;
  return <group position={pos} rotation={[0, ry, 0]} scale={s * 0.7}>
    <mesh geometry={BODY} material={mb} /><mesh geometry={HEAD} material={mb} position={[0, 1.37, 0]} />
    {arm > 0 && <group position={[0.22, 0.95, 0.05]} rotation={[0, 0, -0.35 * arm]}><mesh geometry={ARM} material={mb} position={[0, 0.3 * arm, 0]} />
      {flash > 0 && <mesh material={mf} position={[0, 0.65 * arm, 0.05]}><sphereGeometry args={[0.09 + 0.12 * flash, 16, 12]} /></mesh>}</group>}
  </group>;
};

// 光の円すい（スポットライト・半分透ける灰色）
export const Cone: React.FC<{pos: P3; h: number; r: number; op?: number}> = ({pos, h, r, op = 1}) => {
  const m = useMemo(() => new THREE.MeshBasicMaterial({color: '#c8cccc', transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, toneMapped: false}), []);
  if (op <= 0.002) return null; m.opacity = 0.22 * op;
  return <mesh position={[pos[0], pos[1] + h / 2, pos[2]]} material={m}><coneGeometry args={[r, h, 40, 1, true]} /></mesh>;
};

// 面（半分透ける板）
export const Plate: React.FC<{pos: P3; size: [number, number]; col: string; op?: number; rot?: number[]; add?: boolean}> = ({pos, size, col, op = 1, rot = [0, 0, 0], add = false}) => {
  const m = useMemo(() => new THREE.MeshBasicMaterial({transparent: true, depthWrite: false, side: THREE.DoubleSide, toneMapped: false}), []);
  if (op <= 0.002) return null; m.color.set(col); m.opacity = op; m.blending = add ? THREE.AdditiveBlending : THREE.NormalBlending;
  return <mesh position={pos} rotation={rot as any} material={m}><planeGeometry args={size} /></mesh>;
};

// 白い煙（ぼけた球のかたまり）。u＝0〜1 の広がり
export const Smoke: React.FC<{pos: P3; u: number; seed?: number; dir?: number}> = ({pos, u, seed = 5, dir = -1}) => {
  const m = useMemo(() => new THREE.MeshBasicMaterial({color: '#e8ecec', transparent: true, depthWrite: false, toneMapped: false}), []);
  const P = useMemo(() => { let s = seed; const r = () => ((s = (s * 16807) % 2147483647) / 2147483647); return Array.from({length: 26}, () => [r(), r(), r(), r()]); }, [seed]);
  if (u <= 0) return null; m.opacity = 0.85 * Math.min(1, u * 3) * (1 - Math.max(0, u - 0.85) / 0.15);
  return <group position={pos}>{P.map(([a, b, c, d], i) => { const k = Math.min(1, u * 1.4 - i / 40); if (k <= 0) return null; return <mesh key={i} material={m} position={[dir * (0.2 + a * 2.6 * k), 0.15 + b * 1.1 * k, (c - 0.5) * 1.2]} scale={0.25 + d * 0.45 * k}><icosahedronGeometry args={[1, 1]} /></mesh>; })}</group>;
};

// 四角い粒の柱（ソフトだけ＝下から上へ流れる）
export const Pixels: React.FC<{pos: P3; t: number; op?: number; col?: string; n?: number; spread?: number; h?: number}> = ({pos, t, op = 1, col = ACCENT.teal, n = 160, spread = 1.6, h = 6}) => {
  const m = useMemo(() => new THREE.MeshBasicMaterial({transparent: true, depthWrite: false, toneMapped: false, blending: THREE.AdditiveBlending}), []);
  const P = useMemo(() => { let s = 11; const r = () => ((s = (s * 16807) % 2147483647) / 2147483647); return Array.from({length: n}, () => [r(), r(), r()]); }, [n]);
  if (op <= 0.002) return null; m.color.set(col); m.opacity = op;
  return <group position={pos}>{P.map(([a, b, c], i) => { const y = ((b + t * 1.1) % 1); const rr = 0.15 + y * spread; const th = a * Math.PI * 2; return <mesh key={i} material={m} position={[Math.cos(th) * rr * c, y * h, Math.sin(th) * rr * c]} scale={0.05 + 0.03 * c}><planeGeometry args={[1, 1]} /></mesh>; })}</group>;
};

// 床の輪（u＝広がり）
export const RingFx: React.FC<{pos: P3; u: number; r0?: number; r1?: number; col?: string; sy?: number}> = ({pos, u, r0 = 1, r1 = 3, col = 'cyan', sy = 1}) => {
  if (u <= 0 || u >= 1) return null; const [c, k] = COL[col]; const r = r0 + (r1 - r0) * (1 - Math.pow(1 - u, 2.2)); const op = Math.min(1, u * 3) * Math.pow(1 - u, 1.2);
  return <group position={pos} scale={[r, 1, r * sy]}><Glow seg={RING1} color={c} core={k} op={op} w={0.04} halo={0.3} /></group>;
};
const RING1: Seg = (() => { const a: Seg = []; const n = 96; for (let i = 0; i < n; i++) { const t0 = i / n * Math.PI * 2, t1 = (i + 1) / n * Math.PI * 2; a.push(Math.cos(t0), 0, Math.sin(t0), Math.cos(t1), 0, Math.sin(t1)); } return a; })();
export {RING1};
