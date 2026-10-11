import pathlib
from playwright.sync_api import sync_playwright
FAKE = open('test/run.py').read().split('FAKE = """')[1].split('"""')[0]
CAPTURE = """
window.__ms = {};
if (navigator.mediaSession) { const o = navigator.mediaSession.setActionHandler.bind(navigator.mediaSession);
  navigator.mediaSession.setActionHandler = (a, f) => { window.__ms[a] = f; try { o(a, f); } catch (e) {} }; }
"""
res=[]
def check(n, c, i=''): res.append(bool(c)); print(('PASS ' if c else 'FAIL ')+n, i, flush=True)
with sync_playwright() as p:
    b = p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
    ctx = b.new_context(viewport={'width':384,'height':832}, is_mobile=True, has_touch=True)
    ctx.add_init_script(FAKE); ctx.add_init_script(CAPTURE)
    pg = ctx.new_page(); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://localhost:8767/'); pg.wait_for_timeout(2500)
    pg.set_input_files('#fileInput','test/small-epub3.epub'); pg.wait_for_timeout(800)
    # next chapter button
    pg.click('#nextChBtn'); pg.wait_for_timeout(200)
    check('next-chapter button jumps to chapter 2', pg.evaluate('[R.ch,R.s]')==[1,0])
    pg.click('#nextChBtn'); pg.wait_for_timeout(200)
    check('next-chapter on last chapter shows message', 'last chapter' in pg.text_content('#toast'))
    pg.click('#prevChBtn'); pg.wait_for_timeout(200)
    check('prev-chapter goes back', pg.evaluate('R.ch')==0)
    # player fits at S24 width
    boxes = pg.evaluate("[...document.querySelectorAll('.ctl-row > *')].map(e=>{const r=e.getBoundingClientRect(); return [r.left,r.right,r.width,r.height]})")
    check('6 player buttons fit without overlap, all ≥44px', len(boxes)==6 and all(boxes[i][1]<=boxes[i+1][0]+0.5 for i in range(5)) and boxes[-1][1]<=384 and all(w>=44 and h>=40 for _,_,w,h in boxes), [round(x[2]) for x in boxes])
    pg.screenshot(path='test/m-player.png')
    # speed presets
    pg.click('#rateChip'); pg.wait_for_timeout(350)
    pg.click('#rateSheet [data-rate="1.5"]'); check('1.5× preset', pg.evaluate('S.rate')==1.5 and pg.text_content('#rateChip')=='1.5×', pg.text_content('#rateChip'))
    pg.click('#rateSheet [data-rate-step="0.1"]'); check('+ adds 0.1', abs(pg.evaluate('S.rate')-1.6)<1e-9, pg.evaluate('S.rate'))
    pg.click('#rateSheet [data-rate-step="-0.1"]'); pg.click('#rateSheet [data-rate-step="-0.1"]'); check('− subtracts 0.1', abs(pg.evaluate('S.rate')-1.4)<1e-9)
    pg.click('#rateSheet [data-rate="1"]'); check('1× resets and is highlighted', pg.evaluate('S.rate')==1 and pg.get_attribute('#rateSheet [data-rate="1"]','aria-pressed')=='true')
    check('slider steps 0.1', pg.get_attribute('#rateIn2','step')=='0.1')
    pg.screenshot(path='test/m-speed.png'); pg.click('#rateSheet [data-close]'); pg.wait_for_timeout(300)
    # media session
    pg.click('#playBtn'); pg.wait_for_timeout(400)
    check('silent media loop plays while reading', pg.evaluate('!Media.el.paused'))
    check('lock screen shows playing + chapter/book', pg.evaluate("navigator.mediaSession.playbackState")=='playing' and pg.evaluate("navigator.mediaSession.metadata && navigator.mediaSession.metadata.title")=='The Flood', pg.evaluate("[navigator.mediaSession.metadata?.title, navigator.mediaSession.metadata?.artist]"))
    check('handlers registered', all(k in pg.evaluate('Object.keys(__ms)') for k in ['play','pause','nexttrack','previoustrack']))
    pg.evaluate("__ms.pause()"); pg.wait_for_timeout(200)
    check('lock-screen pause pauses reading', not pg.evaluate('Player.playing') and pg.evaluate('Media.el.paused') and pg.evaluate("navigator.mediaSession.playbackState")=='paused')
    p0 = pg.evaluate('[R.ch,R.s]'); s0 = p0[1]; pg.evaluate("__ms.nexttrack()"); pg.wait_for_timeout(100)
    p1=pg.evaluate('[R.ch,R.s]'); exp = [p0[0], p0[1]+1] if p0[1]+1 < pg.evaluate(f'R.content.chapters[{p0[0]}].sents.length') else [p0[0]+1, 0]; check('headphone next = next sentence (across chapters too)', p1==exp, (p0, p1))
    pg.evaluate("__ms.previoustrack()"); pg.wait_for_timeout(100)
    check('headphone previous = previous sentence', pg.evaluate('[R.ch,R.s]')==p0)
    pg.evaluate("__ms.play()"); pg.wait_for_timeout(300)
    check('lock-screen play resumes', pg.evaluate('Player.playing') and not pg.evaluate('Media.el.paused'))
    n = len(pg.evaluate('__spoken'))
    pg.evaluate("Media.el.pause()"); pg.wait_for_timeout(300)   # what Chrome does when headphones disconnect
    check('headphones unplugged (system pause) → reading pauses', not pg.evaluate('Player.playing'))
    pg.wait_for_timeout(300); check('…and no more sentences spoken', len(pg.evaluate('__spoken'))<=n+1)
    pg.click('#nextChBtn'); pg.wait_for_timeout(200)
    check('metadata follows chapter change', pg.evaluate("navigator.mediaSession.metadata.title")=='After the Rain')
    check('no page errors', not errs, errs)
    b.close()
print(f'\n{sum(res)}/{len(res)} passed')
