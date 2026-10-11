import time
from playwright.sync_api import sync_playwright
SPY = open('test/neural.py').read().split('SPY = """')[1].split('"""')[0]
with sync_playwright() as p:
    b = p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
    ctx = b.new_context(viewport={'width':384,'height':832}, is_mobile=True, has_touch=True)
    ctx.add_init_script(SPY); pg = ctx.new_page(); pg.set_default_timeout(0); errs=[]
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text[:200]) if m.type=='error' else None)
    pg.goto('http://localhost:8767/'); pg.wait_for_timeout(3000)
    print('controlled by SW:', pg.evaluate('!!navigator.serviceWorker.controller'), '| crossOriginIsolated:', pg.evaluate('self.crossOriginIsolated'), '| reload guard:', pg.evaluate("sessionStorage.getItem('ra.coiReload')"), flush=True)
    print('storage persistent (IDB):', pg.evaluate('DB.persistent'), '| hardwareConcurrency:', pg.evaluate('navigator.hardwareConcurrency'), flush=True)
    pg.evaluate("Neural.download('cpu', ()=>{})"); pg.evaluate("S.neuralInstalled='cpu'; S.engine='neural'")
    t=time.time(); pg.evaluate("Neural.start()"); print(f'model loaded in {time.time()-t:.1f}s, mode:', pg.evaluate('Neural.mode'), '| threads:', pg.evaluate('Neural.threads()'), flush=True)
    for i in range(2):
        r = pg.evaluate("""async () => { const r = await Neural.synth('The quick brown fox jumps over the lazy dog, then settles down by the fire to read a good book.', 'af_heart', 1).promise; return {dur:r.dur, ms:r.ms} }""")
        print(f"  run {i+1}: {r['dur']:.2f}s of speech in {r['ms']/1000:.2f}s → {r['dur']/(r['ms']/1000):.2f}× real time", flush=True)
    print('errors:', errs[:5])
    # Offline: second visit with server unreachable
    b.close()
