// 使い方：node tools/stills.mjs T01 out/st 0,20,40,60,80 [scale]
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import path from 'path'; import fs from 'fs';
const [comp, out, list, sc] = process.argv.slice(2);
fs.mkdirSync(out, {recursive: true});
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts'), publicDir: path.resolve('public')});
const composition = await selectComposition({serveUrl, id: comp});
for (const s of list.split(',')) {
  const frame = parseInt(s);
  await renderStill({serveUrl, composition, frame, output: `${out}/${comp}_f${String(frame).padStart(3, '0')}.png`, scale: sc ? parseFloat(sc) : 0.5, chromiumOptions: {gl: 'angle'}});
  process.stdout.write(frame + ' ');
}
console.log('done');
