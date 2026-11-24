線画 2D の写し（mute 型）の道具。案件フォルダ（rikai/・tools/・proj/）で使う。手順と数字＝references/senga2d_mute.md
senga2d_rf_make.py      rikai/rf.json（手本の秒→うちの秒の地図）＝切り替えの表 zure_kirikae.md＋出来事 zure_dekigoto.md＋締めの札の頭
kamera_gyaku.py         手本のカメラ（寄り・流し・回り）を切り替えごとに逆算 → senga2d_kamera_fit.py でならして proj/src/mp/kamera.json
                        （流しが 40px を超えるカット＝物の動き → NOPAN に入れて流しを 0）
kirikae_shurui.py       切り替えの種類（光 3 コマ / ずれ 4 コマ）を 1 コマずつ測る
senga_trace.py          手本のコマから線の芯を点にする（形は写して作る）
senga2d_stills_list.py  比べるコマの一覧 → proj で node stills.mjs <dir> <Comp> <一覧>（書き出しより速く回せる）
senga2d_sabun2.py       カットごとの差の表（位置・大きさ・回り＝ECC／形 F1／線の芯・にじみ／背景 ΔE／カメラ＝0.1→0.9 の直接合わせ）。動画でも静止画の dir でも
senga2d_sabun2_md.py    json から表だけ作り直す
senga2d_hito_box.py     掃除係（差し色の塊）の箱を手本とうちで比べる＝人の置き場所を px で直す
senga2d_align_base.py   差の表の「位置・大きさ」から場面の土台 z0・ox・oy を直す（形が違いすぎる所は触らん）
senga2d_telop_y05.py    照合の門の字幕の高さを 0.5 秒おきで測り直す
narabe.py               手本｜前の版｜新しい版 を 0.5 秒おきに並べる（検品の一覧）
ken_ichiran.py          手本を 2 コマおきに全部並べる（見る 100%）
sen_futosa.py           線の芯の太さ・光のにじみの断面
Remotion の部品＝assets/senga2d/kirikae_kamera.tsx（カメラ・切り替え・光のにじみ）
