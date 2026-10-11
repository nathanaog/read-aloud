import pathlib, base64
from playwright.sync_api import sync_playwright
URL = 'file://' + str(pathlib.Path('dist/read-aloud.html').resolve())
SPY = open('test/neural.py').read().split('SPY = """')[1].split('"""')[0]
TEXT = ("It rained for forty days, and the river carried branches, fence posts and the occasional "
        "bewildered sheep down past the bridge, where the whole village had gathered to watch.")
VOICES = [('af_heart', 'Heart, American English.'), ('af_bella', 'Bella, American English.'),
          ('bf_emma', 'Emma, British English.'), ('bm_george', 'George, British English.')]
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(); ctx.add_init_script(SPY); pg = ctx.new_page(); pg.set_default_timeout(0)
    pg.goto(URL); pg.wait_for_timeout(500)
    pg.evaluate("Neural.download('cpu', ()=>{})"); pg.evaluate("S.neuralInstalled='cpu'; S.engine='neural'"); pg.evaluate("Neural.start()")
    print('model ready', flush=True)
    b64 = pg.evaluate("""async ([voices, text]) => {
      const parts = []; const sr = 24000; const gap = new Float32Array(sr);
      for (const [v, intro] of voices) {
        for (const t of [intro, text]) {
          const r = await Neural.synth(t, v, 1).promise;
          parts.push(r.buffer.getChannelData(0).slice(), gap.slice(0, t === intro ? sr * 0.25 : sr * 0.9));
        }
      }
      const n = parts.reduce((a, x) => a + x.length, 0), pcm = new Int16Array(n); let o = 0;
      for (const x of parts) for (let i = 0; i < x.length; i++) pcm[o++] = Math.max(-1, Math.min(1, x[i])) * 32767;
      const h = new DataView(new ArrayBuffer(44)), w = (i, s) => [...s].forEach((c, k) => h.setUint8(i + k, c.charCodeAt(0)));
      w(0, 'RIFF'); h.setUint32(4, 36 + n * 2, true); w(8, 'WAVE'); w(12, 'fmt '); h.setUint32(16, 16, true); h.setUint16(20, 1, true);
      h.setUint16(22, 1, true); h.setUint32(24, sr, true); h.setUint32(28, sr * 2, true); h.setUint16(32, 2, true); h.setUint16(34, 16, true);
      w(36, 'data'); h.setUint32(40, n * 2, true);
      const bytes = new Uint8Array(44 + n * 2); bytes.set(new Uint8Array(h.buffer), 0); bytes.set(new Uint8Array(pcm.buffer), 44);
      let s = ''; for (let i = 0; i < bytes.length; i += 32768) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 32768));
      return btoa(s); }""", [VOICES, TEXT])
    pathlib.Path('/home/claude/neural-voice-samples.wav').write_bytes(base64.b64decode(b64)); print('saved', flush=True)
    b.close()
