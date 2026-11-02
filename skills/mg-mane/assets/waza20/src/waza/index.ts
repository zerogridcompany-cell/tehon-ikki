// 20 の技の部品の一覧（番号・英語の名前・日本語の一言・部品）。使い方は ~/.claude/skills/mg-mane/references/waza20.md
import React from 'react';
import {W01_Particles} from './W01_Particles';
import {W02_LiquidMorph} from './W02_LiquidMorph';
import {W03_Holographic} from './W03_Holographic';
import {W04_NeonGlow} from './W04_NeonGlow';
import {W05_Wireframe3D} from './W05_Wireframe3D';
import {W06_Glassmorphism} from './W06_Glassmorphism';
import {W07_KineticType} from './W07_KineticType';
import {W08_Isometric} from './W08_Isometric';
import {W09_Clay3D} from './W09_Clay3D';
import {W10_ASCIIArt} from './W10_ASCIIArt';
import {W11_GradientMesh} from './W11_GradientMesh';
import {W12_ComicBook} from './W12_ComicBook';
import {W13_SplitFlap} from './W13_SplitFlap';
import {W14_RetroVHS} from './W14_RetroVHS';
import {W15_Halftone} from './W15_Halftone';
import {W16_Bauhaus} from './W16_Bauhaus';
import {W17_PixelArt} from './W17_PixelArt';
import {W18_Blueprint} from './W18_Blueprint';
import {W19_ArtDeco} from './W19_ArtDeco';
import {W20_NeoBrutalism} from './W20_NeoBrutalism';

export {W01_Particles, W02_LiquidMorph, W03_Holographic, W04_NeonGlow, W05_Wireframe3D, W06_Glassmorphism, W07_KineticType, W08_Isometric, W09_Clay3D, W10_ASCIIArt, W11_GradientMesh, W12_ComicBook, W13_SplitFlap, W14_RetroVHS, W15_Halftone, W16_Bauhaus, W17_PixelArt, W18_Blueprint, W19_ArtDeco, W20_NeoBrutalism};

export type WazaItem = {n: number; id: string; name: string; ja: string; C: React.FC<any>};
export const WAZA: WazaItem[] = [
  {n: 1, id: 'W01-Particles', name: 'Particles', ja: '粒子が集まる', C: W01_Particles},
  {n: 2, id: 'W02-LiquidMorph', name: 'Liquid morph', ja: '液体の玉がくっつく', C: W02_LiquidMorph},
  {n: 3, id: 'W03-Holographic', name: 'Holographic', ja: '虹の薄膜', C: W03_Holographic},
  {n: 4, id: 'W04-NeonGlow', name: 'Neon glow', ja: 'ネオン管が灯る', C: W04_NeonGlow},
  {n: 5, id: 'W05-Wireframe3D', name: 'Wireframe 3D', ja: '線だけの立体', C: W05_Wireframe3D},
  {n: 6, id: 'W06-Glassmorphism', name: 'Glassmorphism', ja: 'すりガラスのUI', C: W06_Glassmorphism},
  {n: 7, id: 'W07-KineticType', name: 'Kinetic type', ja: '字が動いて場面が替わる', C: W07_KineticType},
  {n: 8, id: 'W08-Isometric', name: 'Isometric', ja: '等角の街がせり上がる', C: W08_Isometric},
  {n: 9, id: 'W09-Clay3D', name: 'Clay 3D', ja: '粘土の立体が弾む', C: W09_Clay3D},
  {n: 10, id: 'W10-ASCIIArt', name: 'ASCII art', ja: '字で描く立体', C: W10_ASCIIArt},
  {n: 11, id: 'W11-GradientMesh', name: 'Gradient mesh', ja: '溶けて流れる色', C: W11_GradientMesh},
  {n: 12, id: 'W12-ComicBook', name: 'Comic book', ja: 'アメコミのコマ', C: W12_ComicBook},
  {n: 13, id: 'W13-SplitFlap', name: 'Split-flap', ja: '空港のパタパタ板', C: W13_SplitFlap},
  {n: 14, id: 'W14-RetroVHS', name: 'Retro VHS', ja: '80年代のビデオ', C: W14_RetroVHS},
  {n: 15, id: 'W15-Halftone', name: 'Halftone', ja: '網点の印刷', C: W15_Halftone},
  {n: 16, id: 'W16-Bauhaus', name: 'Bauhaus', ja: '原色の立体が積まれる', C: W16_Bauhaus},
  {n: 17, id: 'W17-PixelArt', name: 'Pixel art', ja: 'ドット絵のゲーム画面', C: W17_PixelArt},
  {n: 18, id: 'W18-Blueprint', name: 'Blueprint', ja: '設計図から立体へ', C: W18_Blueprint},
  {n: 19, id: 'W19-ArtDeco', name: 'Art deco', ja: '金の放射とアーチ', C: W19_ArtDeco},
  {n: 20, id: 'W20-NeoBrutalism', name: 'Neo-brutalism', ja: '太い黒枠とずらした影', C: W20_NeoBrutalism},
];
