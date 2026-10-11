import pathlib, time, sys, urllib.request
from playwright.sync_api import sync_playwright
VARIANT = sys.argv[1] if len(sys.argv) > 1 else 'cpu'
URL = sys.argv[2] if len(sys.argv) > 2 else 'file://' + str(pathlib.Path('dist/read-aloud.html').resolve())
results=[]
def check(name, cond, info=''):
    results.append(bool(cond)); print(('PASS ' if cond else 'FAIL ') + name, info, flush=True)
hits=lambda: int(urllib.request.urlopen('http://127.0.0.1:8766/hits').read())
SPY = """
const _f = window.fetch;   // test-only: send the page's downloads to the local mirror
window.fetch = (u, o) => { u = String(u.url || u)
  .replace('https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX/resolve/main/', 'http://127.0.0.1:8766/hf/')
  .replace('https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.5.1/dist/', 'http://127.0.0.1:8766/ort/');
  if (window.__offline && u.startsWith('http')) return Promise.reject(new TypeError('offline'));
  return _f(u, o); };
window.__played=[];
const _start = AudioBufferSourceNode.prototype.start;
AudioBufferSourceNode.prototype.start = function(...a){
  const d=this.buffer.getChannelData(0); let ss=0; for(let i=0;i<d.length;i+=7) ss+=d[i]*d[i];
  const r = (typeof R!=='undefined' && R.book) ? R : null;
  window.__played.push({ch:r&&r.ch, s:r&&r.s, dur:this.buffer.duration, rms:Math.sqrt(ss/(d.length/7)), t:performance.now(), engine: typeof S!=='undefined' && S.engine});
  return _start.apply(this,a); };
"""
def wait(pg, js, secs):
    for _ in range(int(secs*5)):
        if pg.evaluate(js): return True
        pg.wait_for_timeout(200)
    return False
with sync_playwright() as p:
    b = p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
    ctx = b.new_context(viewport={'width':384,'height':832}, device_scale_factor=2, is_mobile=True, has_touch=True,
        user_agent='Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36')
    ctx.add_init_script(SPY)
    pg = ctx.new_page(); logs=[]
    pg.on('console', lambda m: logs.append(m.type+': '+m.text[:200]) if m.type=='error' else None)
    pg.on('pageerror', lambda e: logs.append('PAGEERROR '+str(e)))
    pg.goto(URL); pg.wait_for_timeout(2500 if URL.startswith('http') else 400)
    pg.set_input_files('#fileInput','test/small-epub3.epub'); pg.wait_for_timeout(800)
    check('engine is system by default', pg.evaluate('S.engine')=='system')

    pg.click('nav [data-tab="settings"]'); pg.click('#engineSeg [data-v="neural"]'); pg.wait_for_timeout(300)
    check('setup panel with both sizes, Best pre-selected', pg.is_visible('#neuralSetup') and pg.is_checked('input[name=kvariant][value=full]'), (pg.text_content('#sizeFull'), pg.text_content('#sizeCpu')))
    pg.check(f'input[name=kvariant][value={VARIANT}]')
    pg.screenshot(path=f'test/n-setup-{VARIANT}.png')
    t0=time.time(); pg.click('#dlBtn'); seen=set()
    for _ in range(3000):
        pct = pg.text_content('#dlPct') or ''
        if pct: seen.add(pct)
        if pg.is_visible('#neuralReady'): break
        pg.wait_for_timeout(100)
    check('download completes, progress shown', pg.is_visible('#neuralReady') and len(seen)>=3, f'{time.time()-t0:.1f}s, {len(seen)} progress values')
    check('files in IndexedDB', pg.evaluate("(async()=>(await DB.all('assets')).length)()")==10)
    wait(pg, "/real time|failed/.test(document.querySelector('#benchOut').textContent)", 900)
    bench = pg.text_content('#benchOut'); check('speed test shows calculation', '÷' in bench and 'real time' in bench, bench)
    print('   engine mode:', pg.evaluate('Neural.mode'), '| chip:', pg.evaluate('Neural.device()'), '| threads:', pg.evaluate('Neural.threads()'), '| isolated:', pg.evaluate('self.crossOriginIsolated'))
    pg.screenshot(path=f'test/n-ready-{VARIANT}.png')

    pg.click('nav [data-tab="reader"]'); pg.wait_for_timeout(200)
    pg.click('#playBtn')
    ok = wait(pg, "__played.filter(x=>x.engine==='neural').length>=3", 600)
    pl = [x for x in pg.evaluate('__played') if x['engine']=='neural']
    check('neural audio plays in order from the start', ok and [x['s'] for x in pl[:3]]==[0,1,2], [(x['s'],round(x['dur'],2)) for x in pl[:4]])
    check('audio is real speech level (not silent)', pl and all(x['rms']>0.01 for x in pl[:3]), [round(x['rms'],3) for x in pl[:3]])
    sents = pg.evaluate("R.content.chapters[0].sents.map(s=>s[0].replace(/\\uE000[^\\uE001]*\\uE001/g,''))")
    rates = [len(sents[x['s']])/x['dur'] for x in pl[:3]]
    check('speech length fits text length (6–30 chars/s)', all(6<r<30 for r in rates), [f"{sents[x['s']][:28]!r} {x['dur']:.2f}s" for x in pl[:3]])
    check('runs in a background worker', pg.evaluate('Neural.mode') in ('module','classic'), pg.evaluate('Neural.mode'))
    t=time.time(); pg.evaluate('1'); pg.click('nav [data-tab="help"]'); pg.click('nav [data-tab="reader"]')
    check('tab switch during synthesis < 1 s', time.time()-t < 1, f'{time.time()-t:.2f}s')
    sf = pg.evaluate('Neural.speedFactor()'); print('   live speed:', sf)
    if sf and sf['factor'] < 1:
        ok = wait(pg, "S.engine==='system'", 900)
        check('too slow → falls back to system voices with explanation', ok, pg.text_content('#toast'))
    else:
        gaps=[(pl[i+1]['t']-pl[i]['t'])/1000-pl[i]['dur'] for i in range(len(pl)-1)]
        check('no gaps between sentences', all(g<0.3 for g in gaps[1:]), gaps)
    pg.click('#playBtn') if pg.evaluate('Player.playing') else None

    # Offline: reload with network blocked, neural on again, must produce audio
    pg.evaluate("S.engine='neural'; saveSettings()")
    before=hits(); ctx.add_init_script('window.__offline=true'); pg.reload(); pg.wait_for_timeout(1500)
    pg.click('#continueBox [data-open]'); pg.wait_for_timeout(300)
    n=len([x for x in pg.evaluate('__played') if x['engine']=='neural']); pg.click('#playBtn')
    ok = wait(pg, f"__played.filter(x=>x.engine==='neural').length>{n}", 600)
    check('works offline after the download', ok, pg.evaluate('Neural.error'))
    check('zero network requests while offline', hits()==before, (before, hits()))
    pg.click('#playBtn') if pg.evaluate('Player.playing') else None
    pg.screenshot(path=f'test/n-reader-{VARIANT}.png')
    # extra voice + preview (back online)
    print('console errors:', logs[:8])
    b.close()
print(f"\n{sum(results)}/{len(results)} passed")
