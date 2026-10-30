import React, {useMemo} from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, Easing, getInputProps} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import * as THREE from 'three';
import CFG from './slabs.json';

// 白い板の比べ（110）：ギガファクトリーの形（角を落とした長方形）の板が格子の床に落ちて並ぶ。
// 板の並び・落ちる時刻・カメラは slabs.json（手本のコマに合わせて tools/slab_fit.py で詰める）
// --props '{"slabs":{…}}' で丸ごと上書きして試す（tools/mg_opt.py --json）
const C = {...(CFG as any), ...((getInputProps() as any).slabs || {})};
export const SLAB_F0 = C.f0;
export const SLAB_3D_F0 = (C as any).f3d ?? 1646;  // 一枚絵（〜1651）の上に 1646〜1652 で溶かして出す（1652 で切り替えると余計なカットに数えられた・10/27 夕）
const SLAB_FADE: [number, number] = (C as any).fade ?? [1646, 1652];  // slabs.json の f3d・fade で前半も 3D にできる（10/28 夜）

const slabShape = () => {
  const w = C.slab.w, d = C.slab.d, c = C.slab.chamfer;
  const s = new THREE.Shape();
  s.moveTo(-w / 2 + c, -d / 2); s.lineTo(w / 2 - c, -d / 2); s.lineTo(w / 2, -d / 2 + c);
  s.lineTo(w / 2, d / 2 - c); s.lineTo(w / 2 - c, d / 2); s.lineTo(-w / 2 + c, d / 2);
  s.lineTo(-w / 2, d / 2 - c); s.lineTo(-w / 2, -d / 2 + c); s.closePath();
  return s;
};

const Scene: React.FC<{f: number}> = ({f}) => {
  const geo = useMemo(() => {
    const g = new THREE.ExtrudeGeometry(slabShape(), {depth: C.slab.h, bevelEnabled: false});
    g.rotateX(-Math.PI / 2);
    return g;
  }, []);
  const cam = C.cam.map((k: any) => k.f);
  const ip = (key: string) => interpolate(f, cam, C.cam.map((k: any) => k[key]), {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});
  return (
    <>
      <color attach="background" args={[C.bg]} />
      <fog attach="fog" args={[C.bg, C.fog[0], C.fog[1]]} />
      <perspectiveCamera />
      <ambientLight intensity={C.light.amb} />
      <spotLight position={C.light.spot} intensity={C.light.spotI} angle={C.light.spotA} penumbra={0.9} decay={0} castShadow target-position={[0, 0, 0]} />
      <directionalLight position={C.light.dir} intensity={C.light.dirI} />
      <mesh rotation-x={-Math.PI / 2} receiveShadow>
        <planeGeometry args={[400, 400]} />
        <meshStandardMaterial color={C.floor} roughness={0.35} metalness={0.2} />
      </mesh>
      <gridHelper args={[400, 400 / C.grid, C.gridColor, C.gridColor]} position={[0, 0.01, 0]} />
      {C.slabs.map((s: any, i: number) => {
        const y = s.land <= s.drop ? 0 : interpolate(f, [s.drop, s.land], [C.dropH, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.in(Easing.quad)});
        if (f < s.drop) return null;
        return (
          <mesh key={i} geometry={geo} position={[s.x, y, s.z]} castShadow receiveShadow>
            <meshStandardMaterial color={C.slabColor} roughness={0.6} />
          </mesh>
        );
      })}
      <CamRig pos={[ip('x'), ip('y'), ip('z')]} look={[ip('lx'), ip('ly'), ip('lz')]} fov={ip('fov')} />
    </>
  );
};

import {useThree} from '@react-three/fiber';
const CamRig: React.FC<{pos: number[]; look: number[]; fov: number}> = ({pos, look, fov}) => {
  const {camera} = useThree();
  const c = camera as THREE.PerspectiveCamera;
  c.position.set(pos[0], pos[1], pos[2]);
  c.fov = fov; c.updateProjectionMatrix();
  c.lookAt(look[0], look[1], look[2]);
  return null;
};

export const Slabs: React.FC = () => {
  const f = useCurrentFrame() + SLAB_F0;
  // 1枚だけの所（〜1643）は Codex の一枚絵（Green.tsx の s110）。3D は板が降り始める 1644 から
  if (f < SLAB_3D_F0) return null;
  return (
    <AbsoluteFill style={{opacity: interpolate(f, SLAB_FADE, [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
      <ThreeCanvas width={1280} height={720} shadows camera={{fov: 30, position: [0, 6, 18]}}>
        <Scene f={f} />
      </ThreeCanvas>
    </AbsoluteFill>
  );
};
