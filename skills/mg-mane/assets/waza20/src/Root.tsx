// 20 の技（mg-mane assets/waza20）：1つずつの Composition（W01_Particles …・1080x1920・30fps・2.5秒）＋ All20（20本を順に・左上に番号と名前）
import React from 'react';
import {Ekonte} from './ekonte/Ekonte';
import ekonteProps from './ekonte/props.json';
import {AbsoluteFill, Composition, Sequence} from 'remotion';
import {WAZA} from './waza';

export const SEC = 75;   // 1つ 2.5 秒
const HEAD = 150;   // 上の帯（番号と名前）。技の絵はその下の 1080x1770 に描く＝札が絵を隠さん
const Label: React.FC<{n: number; name: string; ja: string}> = ({n, name, ja}) => (
  <div style={{position: 'absolute', left: 0, top: 0, width: 1080, height: HEAD, background: '#0e0e12', display: 'flex', alignItems: 'center', gap: 22, paddingLeft: 40, boxSizing: 'border-box', fontFamily: 'system-ui, -apple-system, Helvetica, sans-serif', zIndex: 50}}>
    <div style={{width: 84, height: 84, borderRadius: 42, background: '#e5484d', border: '4px solid #fff', color: '#fff', fontWeight: 800, fontSize: 40, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0}}>{n}</div>
    <div style={{color: '#fff'}}>
      <div style={{fontWeight: 800, fontSize: 50, lineHeight: 1.05}}>{name}</div>
      <div style={{fontWeight: 600, fontSize: 28, opacity: 0.8, marginTop: 6}}>{ja}</div>
    </div>
  </div>
);
const All20: React.FC = () => (
  <AbsoluteFill style={{background: '#000'}}>
    {WAZA.map((w, i) => (
      <Sequence key={w.id} from={i * SEC} durationInFrames={SEC}>
        <div style={{position: 'absolute', left: 0, top: HEAD, width: 1080, height: 1920 - HEAD, overflow: 'hidden'}}><w.C width={1080} height={1920 - HEAD} /></div>
        <Label n={w.n} name={w.name} ja={w.ja} />
      </Sequence>
    ))}
  </AbsoluteFill>
);
export const RemotionRoot: React.FC = () => (
  <>
    {WAZA.map((w) => <Composition key={w.id} id={w.id} component={w.C} durationInFrames={SEC} fps={30} width={1080} height={1920} />)}
    <Composition id="All20" component={All20} durationInFrames={SEC * WAZA.length} fps={30} width={1080} height={1920} />
        <Composition id="Ekonte" component={Ekonte as any} durationInFrames={Math.max(1, Math.ceil((ekonteProps as any).dur*(ekonteProps as any).fps))} fps={(ekonteProps as any).fps} width={(ekonteProps as any).width} height={(ekonteProps as any).height} defaultProps={ekonteProps as any} />
</>
);
