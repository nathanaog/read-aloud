# Read Aloud

A read-aloud ebook reader that runs entirely in the browser. Built for Android Chrome (Galaxy S24 Ultra), works on desktop Chrome/Edge too.

**Open it:** https://nathanaog.github.io/read-aloud/ — then tap **Install** (or Chrome ⋮ › Install app).

- Import DRM-free EPUBs; it reads them aloud with the current sentence highlighted.
- Remembers your place in every book.
- System voices, or an optional natural-sounding neural voice (Kokoro) that runs on the phone after a one-time download.
- Light, sepia and night themes.

**Privacy:** no accounts, no server. Books, positions and settings are stored only in your browser on your device. The only network use is loading the app and the optional one-time voice download (from Hugging Face and jsDelivr).

## Files
| File | What it is |
|---|---|
| `index.html` | The whole app in one file (also works opened directly, with reduced features) |
| `sw.js` | Service worker: offline use, and the headers that let the neural voice use several processor cores |
| `manifest.webmanifest`, `icon-*.png` | Home-screen install |

## Credits
Kokoro-82M (Apache-2.0) · kokoro-js and Transformers.js (Apache-2.0) · ONNX Runtime Web (MIT) · JSZip (MIT).

## Building from source
Everything needed to rebuild the app is in `source/`:
```
cd source
npm install
python3 build.py
```
`app.html` is the readable source (all app code, commented); the build inlines the libraries into `index.html`. Tests (headless Chrome via Playwright) are in `source/test/`.
