# neon3d（3D 線画ネオンの部品・goat-mercedes 11/24 から）
- three.tsx：Glow（芯＋にじみの 2 本の LineSegments2）・Post（ぶれ＋UnrealBloom）・Floor・Dust・setCam。ACCENT＝差し色 1 か所
- geo.ts：線分の形（sedan＝手本の車の輪郭・wheelOne・engine・turbo・cog・table・shelf・obd・laptop・bunting・heart・helix）
- parts.tsx：Car（黒い中身で後ろの線を隠す）・Refl（映り込み）・Board（canvas の札を板に）・Person・Cone（スポットライト）・Plate・Smoke・Pixels・RingFx
- lib.ts：曲線（B＝ease-out・Cq・D・E＝はね返り）・pchip の鍵
使い方＝`cp ~/.claude/skills/mg-mane/assets/neon3d/*.ts* <作業>/proj/src/<名>/`（labels.ts は案件ごとに書く・Board の Tx 型だけ合わせる）。カメラの逆算は references/neon3d_kamera.md
