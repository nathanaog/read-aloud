import zipfile
def write(path, files, enc=None):
    with zipfile.ZipFile(path,'w') as z:
        z.writestr(zipfile.ZipInfo('mimetype'),'application/epub+zip')
        z.writestr('META-INF/container.xml','<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        if enc: z.writestr('META-INF/encryption.xml',enc)
        for k,v in files.items(): z.writestr(k,v,compress_type=zipfile.ZIP_DEFLATED)
X='<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>x</title></head><body>%s</body></html>'
long = "The river, which had been swollen for weeks by the rains that fell without pause across the northern hills, carried with it branches, fence posts, the occasional bewildered sheep, and a great deal of mud; and the villagers, who had seen floods before but never one quite like this, gathered on the bridge to watch it pass."
ch1 = X % ('<section epub:type="chapter"><h1>Chapter One: The Flood</h1><p>It rained for forty days.<sup><a epub:type="noteref" href="#n1">1</a></sup> Mr. Hale was not amused. Nobody was!</p><p>'+long+'</p><p>“Will it stop?” asked Ada. “Eventually,” said her father.</p></section><aside epub:type="footnote" id="n1"><p>Roughly forty. Nobody counted.</p></aside>')
ch2 = X % ('<h2>Chapter Two: After</h2>'+''.join(f'<p>Paragraph {i} begins here. It has a second sentence too. And a third one for good measure.</p>' for i in range(1,31)))
nav = X % '<nav epub:type="toc"><ol><li><a href="text/ch1.xhtml">The Flood</a></li><li><a href="text/ch2.xhtml#top">After the Rain</a></li></ol></nav>'
opf='''<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">t1</dc:identifier><dc:title>The Small Flood</dc:title><dc:creator>A. Tester</dc:creator><dc:language>en</dc:language></metadata>
<manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="cover" href="text/cover.xhtml" media-type="application/xhtml+xml"/><item id="c1" href="text/ch1.xhtml" media-type="application/xhtml+xml"/><item id="c2" href="text/ch2.xhtml" media-type="application/xhtml+xml"/></manifest>
<spine><itemref idref="cover"/><itemref idref="nav" linear="no"/><itemref idref="c1"/><itemref idref="c2"/></spine></package>'''
write('test/small-epub3.epub',{'OEBPS/content.opf':opf,'OEBPS/nav.xhtml':nav,'OEBPS/text/cover.xhtml':X%'<img src="c.jpg" alt="cover"/>','OEBPS/text/ch1.xhtml':ch1,'OEBPS/text/ch2.xhtml':ch2})
# EPUB2 + NCX + &nbsp; (not valid XML without DTD → HTML fallback)
H='<html xmlns="http://www.w3.org/1999/xhtml"><head><title>x</title></head><body>%s</body></html>'
opf2='''<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="2.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Zwei Kapitel</dc:title><dc:creator>B. Prüfer</dc:creator><dc:language>de</dc:language></metadata>
<manifest><item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/><item id="a" href="a%20b.html" media-type="application/xhtml+xml"/><item id="b" href="b.html" media-type="application/xhtml+xml"/></manifest><spine toc="ncx"><itemref idref="a"/><itemref idref="b"/></spine></package>'''
ncx='<?xml version="1.0"?><ncx xmlns="http://www.daisy.org/z3986/2005/ncx/"><navMap><navPoint id="p1"><navLabel><text>Erstes Kapitel</text></navLabel><content src="a%20b.html"/></navPoint><navPoint id="p2"><navLabel><text>Zweites Kapitel</text></navLabel><content src="b.html"/></navPoint></navMap></ncx>'
write('test/epub2-ncx.epub',{'OEBPS/content.opf':opf2,'OEBPS/toc.ncx':ncx,'OEBPS/a b.html':H%'<div><p>Es war&nbsp;einmal ein Test. Dr. Müller las vor.</p></div>','OEBPS/b.html':H%'<p>Das zweite Kapitel. Ende.</p>'})
write('test/drm.epub',{'OEBPS/content.opf':opf2},enc='<encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container" xmlns:enc="http://www.w3.org/2001/04/xmlenc#"><enc:EncryptedData><enc:EncryptionMethod Algorithm="http://www.w3.org/2001/04/xmlenc#aes128-cbc"/></enc:EncryptedData></encryption>')
print('ok')
