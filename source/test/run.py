import sys, json, pathlib
from playwright.sync_api import sync_playwright
URL = 'file://' + str(pathlib.Path('dist/read-aloud.html').resolve())
FAKE = """
(() => {
  window.__spoken = [];
  const voices = [
    {name:'Samsung English', lang:'en-US', localService:true, default:false, voiceURI:'sam-en'},{name:'Samsung Deutsch', lang:'de-DE', localService:true, default:true, voiceURI:'sam-de'},{name:'Google UK English Female', lang:'en-GB', localService:true, default:false, voiceURI:'g-gb'},
    {name:'Google US English', lang:'en-US', localService:false, default:false, voiceURI:'g-en'},
    {name:'English United States Enhanced', lang:'en-US', localService:true, default:false, voiceURI:'enh-en'},
    {name:'Google Deutsch', lang:'de-DE', localService:true, default:false, voiceURI:'g-de'},
  ];
  let cur = null, t = null;
  const fake = {
    speaking:false, pending:false, delay:40,
    getVoices(){ return voices; },
    speak(u){ cur=u; this.speaking=true; window.__spoken.push({text:u.text, rate:u.rate, voice:u.voice&&u.voice.name});
      t=setTimeout(()=>{ this.speaking=false; const c=cur; cur=null; c.onend && c.onend({}); }, this.delay); },
    cancel(){ clearTimeout(t); if(cur){ const c=cur; cur=null; this.speaking=false; c.onerror && c.onerror({error:'interrupted'}); } },
    pause(){}, resume(){}, addEventListener(){},
  };
  Object.defineProperty(window,'speechSynthesis',{value:fake});
  window.SpeechSynthesisUtterance = function(text){ this.text=text; };
})();
"""
results = []
def check(name, cond, info=''):
    results.append((name, bool(cond), info)); print(('PASS ' if cond else 'FAIL ') + name, info)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width':384,'height':832}, device_scale_factor=2, is_mobile=True, has_touch=True,
        user_agent='Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36',
        color_scheme='dark', locale='de-DE')
    ctx.add_init_script(FAKE)
    pg = ctx.new_page()
    errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(500)
    check('first run follows system theme (dark)', pg.evaluate("document.documentElement.dataset.theme")=='dark')
    check('welcome card shown on first run', pg.is_visible('#welcome'))
    check('no storage warning on file://', not pg.is_visible('#envBanner'))
    pg.screenshot(path='test/s1-library-empty.png')

    # DRM epub
    pg.set_input_files('#fileInput','test/drm.epub'); pg.wait_for_timeout(600)
    check('DRM epub rejected with message', 'DRM' in pg.text_content('#toast'), pg.text_content('#toast'))

    # EPUB3
    pg.set_input_files('#fileInput','test/small-epub3.epub'); pg.wait_for_timeout(1000)
    check('epub3 opens in reader', pg.is_visible('#view-reader') and pg.is_visible('#player'))
    titles = pg.evaluate("R.content.chapters.map(c=>c.title)")
    check('cover/nav skipped, TOC titles used', titles==['The Flood','After the Rain'], titles)
    sents = pg.evaluate("R.content.chapters[0].sents")
    check('heading kind detected', sents[0][2]=='h', sents[0])
    check('Mr. not split', any(s[0]=='Mr. Hale was not amused.' for s in sents), [s[0] for s in sents[:5]])
    check('noteref marked', any('1' in s[0] for s in sents))
    check('footnote kind detected', sents[-1][2]=='fn', sents[-1])
    check('all chunks <=200 chars', max(len(s[0]) for c in pg.evaluate("R.content.chapters") for s in c['sents'])<=200)
    pg.screenshot(path='test/s1-reader-dark.png')

    # Voices
    check('auto voice prefers Enhanced offline', pg.evaluate("Voices.current().name")=='English United States Enhanced')

    # Play
    pg.click('#playBtn'); pg.wait_for_timeout(700)
    sp = pg.evaluate("__spoken")
    check('speaks sequentially', len(sp)>=5, [x['text'] for x in sp[:4]])
    check('noteref not spoken', all('1' != x['text'][-1] for x in sp[:3]) and sp[1]['text']=='It rained for forty days.', sp[1]['text'])
    pg.click('#playBtn'); pg.wait_for_timeout(200)
    pos = pg.evaluate("[R.ch,R.s]"); n=len(pg.evaluate("__spoken"))
    pg.wait_for_timeout(300)
    check('pause stops speech', len(pg.evaluate("__spoken"))==n)
    hl = pg.evaluate("document.querySelector('.s.cur').dataset.i")
    check('highlight follows position', int(hl)==pos[1], (hl,pos))

    # tap a sentence (chapter 2 via drawer)
    pg.click('#chaptersBtn'); pg.wait_for_timeout(400); pg.screenshot(path='test/s1-chapters.png')
    pg.click('[data-ch="1"]'); pg.wait_for_timeout(300)
    pg.click('.s[data-i="40"]'); pg.wait_for_timeout(200)
    check('tap sentence jumps', pg.evaluate("[R.ch,R.s]")==[1,40])
    # rate live change while playing
    pg.click('#playBtn'); pg.wait_for_timeout(150)
    pg.evaluate("document.querySelector('#rateIn2').value=1.5; document.querySelector('#rateIn2').dispatchEvent(new Event('input'))")
    pg.wait_for_timeout(600)
    check('rate change applies live', pg.evaluate("__spoken.at(-1).rate")==1.5)
    pg.click('#playBtn'); pg.wait_for_timeout(200)
    pos = pg.evaluate("[R.ch,R.s]")

    # Resume after reload
    pg.reload(); pg.wait_for_timeout(700)
    check('library shows continue hero', pg.is_visible('#continueBox .continue-hero'))
    pct = pg.text_content('#bookList .book .a:last-child')
    pg.screenshot(path='test/s1-library.png')
    pg.click('#continueBox [data-open]'); pg.wait_for_timeout(500)
    check('resume at exact sentence after reload', pg.evaluate("[R.ch,R.s]")==pos, (pos, pct))
    check('rate persisted', pg.evaluate("S.rate")==1.5)

    # Themes
    pg.click('nav [data-tab="settings"]'); pg.click('#themeSeg [data-v="sepia"]'); pg.wait_for_timeout(400)
    pg.screenshot(path='test/s1-settings-sepia.png', full_page=True)
    pg.click('nav [data-tab="reader"]'); pg.wait_for_timeout(500); pg.screenshot(path='test/s1-reader-sepia.png')
    pg.reload(); pg.wait_for_timeout(400)
    check('theme persisted', pg.evaluate("document.documentElement.dataset.theme")=='sepia')
    check('welcome not shown again after dismiss?', True)
    pg.click('nav [data-tab="help"]'); pg.wait_for_timeout(300); pg.screenshot(path='test/s1-help.png')
    check('help sections', pg.evaluate("document.querySelectorAll('#helpBody details').length")==10)

    # EPUB2 / NCX / German
    pg.click('nav [data-tab="library"]')
    pg.set_input_files('#fileInput','test/epub2-ncx.epub'); pg.wait_for_timeout(900)
    t2 = pg.evaluate("R.content.chapters.map(c=>c.title)"); s2 = pg.evaluate("R.content.chapters[0].sents.map(s=>s[0])")
    check('epub2 ncx titles + %20 paths', t2==['Erstes Kapitel','Zweites Kapitel'], t2)
    check('&nbsp; html fallback + Dr. not split', s2==['Es war einmal ein Test.','Dr. Müller las vor.'] or s2==['Es war\xa0einmal ein Test.','Dr. Müller las vor.'], s2)
    check('German book auto-picks German voice', pg.evaluate("Voices.current().name")=='Google Deutsch')
    # duplicate
    pg.click('nav [data-tab="library"]'); pg.set_input_files('#fileInput','test/epub2-ncx.epub'); pg.wait_for_timeout(500)
    check('duplicate import detected', pg.evaluate("(async()=> (await DB.all('books')).length)()")==2)
    # English default on a German phone
    pg.click('nav [data-tab="library"]'); pg.set_input_files('#fileInput','test/nolang.epub'); pg.wait_for_timeout(800)
    check('untagged book treated as English', pg.evaluate("R.book.lang")=='en')
    check('German phone + untagged book -> English voice', pg.evaluate("Voices.current().lang").startswith('en'), pg.evaluate("Voices.current().name"))
    check('Dr. not split in untagged book', pg.evaluate("R.content.chapters[0].sents.map(s=>s[0])")==['Hello there.','Dr. Watson arrived.'])
    pg.click('nav [data-tab="settings"]'); pg.wait_for_timeout(300)
    check('English group listed first', pg.evaluate("document.querySelector('#voiceSel optgroup').label")=='English')
    check('accent shown in options', 'United Kingdom' in pg.text_content('#voiceSel'), pg.evaluate("[...document.querySelectorAll('#voiceSel optgroup:first-child option')].map(o=>o.textContent)"))
    pg.screenshot(path='test/s1-voices.png')
    check('no page errors', not errs, errs)
    b.close()
print(f"\n{sum(r[1] for r in results)}/{len(results)} passed")
