"""Builds the Read Aloud website from this folder.

    npm install          # fetches JSZip + kokoro-js (incl. Transformers.js) into node_modules/
    python3 build.py     # writes ../index.html, ../sw.js, manifest, icons, README  (+ dist/read-aloud.html)

app.html is the readable source; the libraries are inlined so the result is one self-contained file.
"""
import hashlib, pathlib, shutil
here = pathlib.Path(__file__).resolve().parent
site = here.parent  # GitHub Pages serves the repository root
src = (here / 'app.html').read_text()
jszip = (here / 'node_modules/jszip/dist/jszip.min.js').read_text()

# kokoro-js ships as an ES module. Embed it as-is, but also export the Transformers.js env (Wg)
# so the app can set the thread count. The page converts it to a classic script at runtime only
# where module workers are refused (a file opened directly).
kokoro = (here / 'node_modules/kokoro-js/dist/kokoro.web.js').read_text()
EXP = 'export{Ef as KokoroTTS,kf as TextSplitterStream,Mf as env}'
assert kokoro.count(EXP) == 1 and kokoro.count('Wg=Yg.env') == 1, 'kokoro-js bundle changed — check the export line'
kokoro = kokoro.replace(EXP, 'export{Ef as KokoroTTS,kf as TextSplitterStream,Mf as env,Wg as tfEnv}')
assert '</script' not in kokoro and '<!--' not in kokoro and '</script' not in jszip

out = src.replace('/*__JSZIP__*/', jszip).replace('/*__KOKORO__*/', kokoro)
(here / 'dist').mkdir(exist_ok=True)
(here / 'dist/read-aloud.html').write_text(out)          # standalone single file
(site / 'index.html').write_text(out)                     # website
ver = hashlib.sha256(out.encode()).hexdigest()[:10]      # new version → service worker refreshes its cache
(site / 'sw.js').write_text((here / 'sw.js').read_text().replace('__VERSION__', ver))
for f in ['manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'icon-maskable.png']:
    shutil.copy(here / f, site / f)
shutil.copy(here / 'README.site.md', site / 'README.md')
print(f'built index.html ({len(out)//1024} KB), version {ver}')
