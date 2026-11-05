// waza3d の見本 5 本（1920x1080・30fps・3 秒）。部品は props で色・字・絵を替える。
import React from 'react';
import {Composition} from 'remotion';
import {T01_ZoomThroughScreen, t01Defaults} from './T01_ZoomThroughScreen';
import {T02_GlassCardsCursor, t02Defaults} from './T02_GlassCardsCursor';
import {T03_FloatingUI, t03Defaults} from './T03_FloatingUI';
import {T04_IsoDecompose, t04Defaults} from './T04_IsoDecompose';
import {T05_IconCloud, t05Defaults} from './T05_IconCloud';
const W = 1920, H = 1080, FPS = 30, D = 90;
const list: {id: string; C: React.FC<any>; props: any}[] = [
  {id: 'T01', C: T01_ZoomThroughScreen, props: t01Defaults},
  {id: 'T02', C: T02_GlassCardsCursor, props: t02Defaults},
  {id: 'T03', C: T03_FloatingUI, props: t03Defaults},
  {id: 'T04', C: T04_IsoDecompose, props: t04Defaults},
  {id: 'T05', C: T05_IconCloud, props: t05Defaults},
];
export const Root: React.FC = () => (
  <>
    {list.map(({id, C, props}) => (
      <Composition key={id} id={id} component={C} durationInFrames={D} fps={FPS} width={W} height={H} defaultProps={props} />
    ))}
  </>
);
