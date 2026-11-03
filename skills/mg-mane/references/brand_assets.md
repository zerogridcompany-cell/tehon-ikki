# ブランドの印（ロゴ・アプリの中のボタン）を「全く同じ」にする（11/3 依頼者「TikTok のロゴ・中のボタンを使うなら全く同じ物を作らんといかん。画像生成で？変わるなら別の道で」）

🔴 **画像生成は使わん**＝拡散モデルはロゴの字・比・角を必ず少し変える（参照を渡しても同じ）。写真の中の物に印が焼き付いとる場面（看板・箱）だけ生成（その時も印は参照 SVG から貼って照合）。
印は**ベクター（SVG）**で持ってきて Remotion で描く（大きさ自由・動かせる・字幕と同じ層）。

## 道（上から順に試す・`scripts/brand_fetch.py <名前>` が ①②を自動）
1. **Wikimedia Commons の公式そのままの SVG（色つき）**＝Google Maps のピン・TikTok の印・Instagram・YouTube・X・Apple・Spotify… `brand_fetch.py` の COMMONS 表（無い名前は `--commons "File 名"`）
2. **Simple Icons**（cdn.simpleicons.org/<名前>・CC0・3,000 社の公式の形・単色）＝色は公式の色を自分で当てる
3. **公式のブランドページ**（tiktok.com/about/brand-assets・design.google・brand.linecorp.com 等）の SVG/PNG/zip ＝ `--url` で落とす。ログインや同意が要る物は本人が落としてフォルダに置く
4. **アプリの中のボタン・UI の動き**＝実物を録る：iPhone の画面収録（60fps）か Mac の QuickTime（iPhone をつないで「新規ムービー収録」）→ `tehon-ikki` の miru で字・箱・色・コマを測り、動きは `kiseki.py`→`ease_fit.py` で曲線に → Remotion で同じ数字で描く。見た目の部品は Material Icons（Google）・SF Symbols（Apple）・各社の Figma の公開 UI キット（公式やないが形は近い）
5. **手本の動画からしか取れん印**＝きれいなコマを切って potrace（`brew install potrace`）でベクター化（線は少し荒れる＝①〜③が無い時だけ）
- 字体＝公式が出しとる物は Google Fonts にある：**TikTok Sans**（@remotion/google-fonts の TikTokSans）・**Google Sans／Google Sans Flex**（GoogleSans.mjs）。無い字体（Apple の SF Pro 等）は一番近い公開の物で妥協と書く

## 門（見せる前）
- `scripts/brand_check.py <公式.svg> <うちの画像か動画> [--frame N] [--box x,y,w,h] --out 比べ.png`＝形の IoU（±6px のずれは許す）と主な色の ΔE。**IoU 0.97 以上**で通す。比べ.png＝公式｜うち｜差（赤＝うちだけ・青＝公式だけ）
- 11/3 実測：tehonI v5 のピン（係が手で描いた）＝IoU 低い・色 ΔE 40（赤が #EA4335 やなく暗い赤・黄が黄緑）→ 公式の SVG に差し替え

## 決まり
- 商標＝社内の写し・練習は可。**本番の広告に他社の印を使うなら許可が要る**（json に出所を残す）
- 印の色は公式の値（Google：赤 #EA4335・青 #4285F4・黄 #FBBC04・緑 #34A853／TikTok：黒 #000000・水色 #25F4EE・赤 #FE2C55）。手本の板の色に寄せるのは地と UI だけ・印の色は変えん
