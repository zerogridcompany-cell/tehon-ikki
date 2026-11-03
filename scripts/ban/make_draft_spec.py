# 仕様書（spec.json）から CapCut の下書きを組む。字（CapCut の字）・全画面の重ね絵（PNG/動画）・音を時刻どおりに並べる。
# mini で打つ（CapCut を閉じてから）：python3 make_draft_spec.py <spec.json の入った置き場>
#   置き場の中身＝spec.json・fonts/*.ttf・spec が指す素材。全部を下書きの media/ に写してから使う（外に置くと「ファイルにアクセスできません」）
# spec = {name, W, H, fps, dur, k_px, fonts:{名前: 置き場からの道},
#   texts:[{t, font, px(字の em の画素), sx(横の倍率), anim:[{type:'in'|'out', id, name, dur(秒)}], x, y(字の箱の真ん中の画素・左上原点), color:'#rrggbb', alpha, a, b(秒), bold}],
#   layers:[{path, a, b, alpha, src, kf}]（kf＝CapCut のキーフレーム {'alpha'|'x'|'y'|'scale'|'rot': [[区切りの頭からの秒, 値], ...]}・字も同じ）  …全画面の絵（W×H の PNG か動画）。並びが後ろほど上
#   audio:[{path, a, b, src, vol}]}
# 字のアニメの番号（CapCut と剪映で共通・pyJianYingDraft metadata）：フェードイン 6724916044072227332／フェードアウト 6724919382104871427／タイプライター I 6724920249654710791
# 🔴字に透明度のキーフレーム（KFTypeAlpha）を書いても効かん（10/31 test2・動画には効く）。clip.alpha と text_alpha も CapCut が開いた時に 1 に戻す
#   ＝字の透明度は素材の global_alpha（spec の alpha）。フェードは手本を1コマずつ測った値で、1コマの区切りごとに alpha を打つ（ban_spec.py）
# 字の大きさ＝fs（CapCut の font_size）。CapCut は行の高さ（OS/2 の sTypoAscender−sTypoDescender）で大きさを決める＝1 あたり 11.46px（1920x1080 の下書きで測った）。fs = em画素 × typo の行の高さ/em ÷ 11.46
import json, os, sys, copy, uuid, shutil, subprocess, time
IN = os.path.expanduser(sys.argv[1]); S = json.load(open(f'{IN}/spec.json'))
TPL = os.path.expanduser(os.environ.get('CK_TPL', '~/work/zgvoid/tpl1024'))   # 型の下書き＝CapCut で自分で作った下書き（動画の段2つ・字1つ・音1つ）を写した置き場
ROOT = os.path.expanduser('~/Movies/CapCut/User Data/Projects/com.lveditor.draft')
NAME = S['name']; FOLD = f'{ROOT}/{NAME}'; MED = f'{FOLD}/media'
W, H, FPS = S['W'], S['H'], S.get('fps', 30.0); K_PX = S.get('k_px', 4.0)
US = 1_000_000
nid = lambda: str(uuid.uuid4()).upper()
us = lambda s: int(round(s * US))
probe = lambda p: json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=width,height,codec_type', '-of', 'json', p], capture_output=True, text=True).stdout)

if os.path.exists(FOLD): raise SystemExit('同じ名前の下書きがある ' + FOLD)
os.makedirs(MED)
tpl = json.load(open(f'{TPL}/draft_info.json')); M0 = tpl['materials']
byid = {x['id']: (k, x) for k, l in M0.items() if isinstance(l, list) for x in l if isinstance(x, dict) and 'id' in x}
d = copy.deepcopy(tpl)
for k, l in d['materials'].items():
    if isinstance(l, list): d['materials'][k] = []
M = d['materials']
def add(kind, obj):
    o = copy.deepcopy(obj); o['id'] = nid(); M.setdefault(kind, []).append(o); return o
def new_track(tt, flag=0):
    t = copy.deepcopy([x for x in tpl['tracks'] if x['type'] == tt][0]); t['id'] = nid(); t['segments'] = []; t['flag'] = flag; return t
def tseg(tt, idx=0):
    return [x for x in tpl['tracks'] if x['type'] == tt][idx]['segments'][0]
VSEG = tseg('video', 1)                       # 型の重ね写真の区切り（写真・動画の両方に使う）
VMAT = byid[VSEG['material_id']][1]
TSEG = tseg('text'); TMAT = byid[TSEG['material_id']][1]; TANIM = byid[TSEG['extra_material_refs'][0]][1]
ASEG = tseg('audio'); AMAT = byid[ASEG['material_id']][1]
KFT = {'alpha': 'KFTypeAlpha', 'x': 'KFTypePositionX', 'y': 'KFTypePositionY', 'scale': 'KFTypeScaleX', 'rot': 'KFTypeRotation'}
def keyframes(kf):                           # kf = {'alpha': [[秒(区切りの頭から), 値], ...], 'x': [[秒, 画素]], ...}  x,y は画素（左上原点）→ CapCut の単位
    out = []
    for prop, pts in (kf or {}).items():
        lst = []
        for t, v in pts:
            if prop == 'x': v = (v - W / 2) / (W / 2)
            if prop == 'y': v = -(v - H / 2) / (H / 2)
            lst.append({'id': nid(), 'curveType': 'Line', 'time_offset': us(t), 'left_control': {'x': 0.0, 'y': 0.0}, 'right_control': {'x': 0.0, 'y': 0.0},
                        'values': [float(v)], 'string_value': '', 'graphID': ''})
        out.append({'id': nid(), 'material_id': '', 'property_type': KFT[prop], 'keyframe_list': lst})
    return out
def refs_from(seg, skip):
    return [add(byid[r][0], byid[r][1])['id'] for r in seg['extra_material_refs'] if byid[r][0] not in skip]
def put(p):                                  # 素材を下書きの中へ
    dst = f'{MED}/{os.path.basename(p)}'
    if not os.path.exists(dst): shutil.copy(p if os.path.isabs(p) else f'{IN}/{p}', dst)
    return dst

FONTS = {key: put(fn) for key, fn in S.get('fonts', {}).items()}

# ---- 重ね絵（全画面）----
def place_layer(L):
    path = put(L['path']); p = probe(path); st = [s for s in p['streams'] if s.get('codec_type') == 'video'][0]
    isv = not path.lower().endswith(('.png', '.jpg', '.jpeg'))
    m = add('videos', VMAT); m.update(path=path, material_name=os.path.basename(path), width=st['width'], height=st['height'],
                                    type='video' if isv else 'photo', duration=us(float(p['format'].get('duration', 10800))) if isv else 10800000000)
    a, b = L['a'], L['b']
    s = copy.deepcopy(VSEG); s['id'] = nid(); s['material_id'] = m['id']
    s['target_timerange'] = {'start': us(a), 'duration': us(b - a)}
    s['source_timerange'] = {'start': us(L.get('src', 0.0)), 'duration': us(b - a)}
    s['speed'] = 1.0; s['volume'] = 0.0
    s['clip'] = {'scale': {'x': 1.0, 'y': 1.0}, 'rotation': 0.0, 'transform': {'x': 0.0, 'y': 0.0}, 'flip': {'vertical': False, 'horizontal': False}, 'alpha': L.get('alpha', 1.0)}
    s['extra_material_refs'] = refs_from(VSEG, ('material_animations', 'common_mask', 'chromas', 'effects'))
    s['common_keyframes'] = keyframes(L.get('kf'))
    return s
def lay_out(items, maker, tt, flag=0):        # 重ならんように段へ詰める
    tracks, ends = [], []
    for it in sorted(items, key=lambda z: z['a']):
        j = next((j for j, e in enumerate(ends) if e <= it['a'] + 1e-6), None)
        if j is None: tracks.append(new_track(tt, flag)); ends.append(0); j = len(ends) - 1
        tracks[j]['segments'].append(maker(it)); ends[j] = it['b']
    return tracks
layer_tracks = lay_out(S.get('layers', []), place_layer, 'video', 2)

# ---- 字 ----
def hexrgb(h): h = h.lstrip('#'); return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
def place_text(T):
    t = T['t']; n = len(t.encode('utf-16-le')) // 2
    fpath = FONTS.get(T.get('font'), '')
    size = T['fs'] if 'fs' in T else T['px'] / K_PX; col = T.get('color', '#ffffff')
    st = {'fill': {'content': {'solid': {'color': hexrgb(col)}, 'render_type': 'solid'}}, 'range': [0, n], 'size': size,
          'font': {'path': fpath, 'id': ''}, 'useLetterColor': True}
    if T.get('bold'): st['bold'] = True
    m = add('texts', TMAT)
    m.update(content=json.dumps({'styles': [st], 'text': t}, ensure_ascii=False), font_path=fpath, font_id='', font_resource_id='', font_name='',
             font_title='none', font_size=size, text_color=col, text_alpha=1.0, global_alpha=T.get('alpha', 1.0), alignment=1,   # 字の不透明度＝global_alpha（1024 の字で 0.82 等。clip.alpha と text_alpha は CapCut が開くと 1 に戻す・10/31 v11）
             has_shadow=False, border_width=0.0, border_color='', line_max_width=2.0, letter_spacing=T.get('ls', 0.0),
             fonts=[], use_effect_default_color=False, base_content='')
    an = add('material_animations', TANIM); an['animations'] = []
    seg_us = us(T['b'] - T['a'])
    for A in T.get('anim', []):               # CapCut の字のアニメ（in/out）＝番号で入れると CapCut が開く時に取ってくる（1024 のフェードアウトと同じ番号で確認）
        d_ = min(seg_us, us(A['dur']))
        an['animations'].append({'anim_adjust_params': None, 'platform': 'all', 'panel': '', 'material_type': 'sticker', 'name': A['name'], 'id': A['id'],
                                 'type': A['type'], 'resource_id': A['id'], 'start': 0 if A['type'] == 'in' else seg_us - d_, 'duration': d_,
                                 'path': '', 'third_resource_id': A['id'], 'source_platform': 1, 'category_id': '', 'category_name': '', 'request_id': ''})
    s = copy.deepcopy(TSEG); s['id'] = nid(); s['material_id'] = m['id']; s['extra_material_refs'] = [an['id']]
    s['target_timerange'] = {'start': us(T['a']), 'duration': us(T['b'] - T['a'])}
    sx = T.get('sx', 1.0)                    # 横の倍率（手本の字の幅に合わせる）
    if abs(sx - 1.0) > 1e-4: s['uniform_scale'] = {'on': False, 'value': 1.0}
    s['clip'] = {'scale': {'x': sx, 'y': 1.0}, 'rotation': 0.0,
                 'transform': {'x': (T['x'] - W / 2) / (W / 2), 'y': -(T['y'] - H / 2) / (H / 2)},
                 'flip': {'vertical': False, 'horizontal': False}, 'alpha': 1.0}
    s['common_keyframes'] = keyframes(T.get('kf'))
    return s
text_tracks = lay_out(S.get('texts', []), place_text, 'text')

# ---- 音 ----
def place_audio(A):
    path = put(A['path'])
    m = add('audios', AMAT); m.update(path=path, name=os.path.basename(path), type='extract_music', music_id=str(uuid.uuid4()), wave_points=[], local_material_id='',
                                      duration=us(float(probe(path)['format']['duration'])))   # 手元の音（type=music はネットの曲を探しに行って止まった）
    s = copy.deepcopy(ASEG); s['id'] = nid(); s['material_id'] = m['id']
    s['target_timerange'] = {'start': us(A['a']), 'duration': us(A['b'] - A['a'])}
    s['source_timerange'] = {'start': us(A.get('src', 0.0)), 'duration': us(A['b'] - A['a'])}
    s['speed'] = 1.0; s['volume'] = A.get('vol', 1.0); s['last_nonzero_volume'] = A.get('vol', 1.0)
    s['extra_material_refs'] = refs_from(ASEG, ('material_animations', 'audio_fades', 'beats', 'time_marks'))
    return s
audio_tracks = lay_out(S.get('audio', []), place_audio, 'audio')

# 一番下の段＝黒（主の段が空やと CapCut が詰める）
main = new_track('video', 0)
blk = f'{MED}/black.png'
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=c=black:s={W}x{H}', '-frames:v', '1', blk], check=True)
main['segments'].append(place_layer({'path': blk, 'a': 0.0, 'b': S['dur']}))
ri = 1
for tr in layer_tracks + text_tracks:
    for s in tr['segments']: s['render_index'] = ri; s['track_render_index'] = ri
    ri += 1
d['tracks'] = [main] + layer_tracks + text_tracks + audio_tracks
did = nid(); now = int(time.time() * US); DUR = us(S['dur'])
ratio = '16:9' if W > H else ('9:16' if H > W else '1:1')
d.update(id=did, name=NAME, duration=DUR, fps=FPS, canvas_config={'ratio': ratio, 'width': W, 'height': H, 'background': None})
d['create_time'] = now // US; d['update_time'] = now // US
json.dump(d, open(f'{FOLD}/draft_info.json', 'w'), ensure_ascii=False); shutil.copy(f'{FOLD}/draft_info.json', f'{FOLD}/draft_info.json.bak')
for f in ('draft_settings', 'draft_agency_config.json', 'draft_biz_config.json', 'attachment_pc_common.json'):
    if os.path.exists(f'{TPL}/{f}'): shutil.copy(f'{TPL}/{f}', f'{FOLD}/{f}')
cov = put(S['cover']) if S.get('cover') else blk
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', cov, '-frames:v', '1', '-vf', 'scale=540:-1', f'{FOLD}/draft_cover.jpg'])
meta = json.load(open(f'{TPL}/draft_meta_info.json'))
meta.update(draft_id=did, draft_name=NAME, draft_fold_path=FOLD, draft_root_path=ROOT, draft_cover='draft_cover.jpg', draft_materials=[], draft_segment_extra_info=[],
            tm_draft_create=now, tm_draft_modified=now, tm_duration=DUR, tm_draft_cloud_entry_id=0, tm_draft_cloud_space_id=0, tm_draft_cloud_completed='',
            tm_draft_cloud_modified=0, cloud_draft_sync=False)
json.dump(meta, open(f'{FOLD}/draft_meta_info.json', 'w'), ensure_ascii=False)
rp = f'{ROOT}/root_meta_info.json'; shutil.copy(rp, rp + '.bak-' + time.strftime('%H%M%S')); r = json.load(open(rp))
e = copy.deepcopy(r['all_draft_store'][0])
e.update(draft_cover=f'{FOLD}/draft_cover.jpg', draft_fold_path=FOLD, draft_id=did, draft_json_file=f'{FOLD}/draft_info.json', draft_name=NAME,
         draft_root_path=ROOT, tm_draft_create=now, tm_draft_modified=now, tm_duration=DUR, cloud_draft_sync=False)
r['all_draft_store'].insert(0, e); json.dump(r, open(rp, 'w'), ensure_ascii=False)
print('作った', FOLD, '重ね絵の段', len(layer_tracks), '字', len(S.get('texts', [])), '字の段', len(text_tracks), '音の段', len(audio_tracks))
