# waza3d（MG の手札＝空間の部品・道 A＝CSS 3D／道 B＝@remotion/three）
- 部品（T01・T02＝道 B three／T03・T04・T05＝道 A）：src/T01_ZoomThroughScreen・T02_GlassCardsCursor・T03_FloatingUI・T04_IsoDecompose・T05_IconCloud（各 1 つで完結・props で色・字・絵を替える・絵は staticFile の名前か URL）
- 共通：src/lib.ts（役→曲線＝easing.md・tw・logLerp・息・粒）
- 見本：`tools/render_all.sh`（Root.tsx の 5 本・1920x1080・30fps・3 秒）→ out/T0N.mp4
- 比べ：`tools/vs.sh ref/T0N_ref.mp4 out/T0N.mp4 out/T0N_vs.jpg`／測り：`/usr/bin/python3 tools/sokutei.py <手本> <うち> <json>`
- 手本の 3 秒：ref/T0N_ref.mp4（元＝~/research/mg-tefuda-20261105/dl/）。点と未達は out/検品表.md
- 版：Remotion 4.0.529・three 0.169・@react-three/fiber 8.17（R3 lab と同じ）。public/icons＝compreel の 44 個（MIT のコード・絵は作品に使って可・束で配らん）
