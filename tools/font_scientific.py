"""Complete scientific coverage using composites of the licensed source face."""
from fontTools.pens.ttGlyphPen import TTGlyphPen

def complete(font):
    """Compose missing scientific signs from glyphs in the same licensed face."""
    cmap=font.getBestCmap()
    def add(code,name,components,width):
        if code in cmap:return
        pen=TTGlyphPen(font.getGlyphSet())
        for glyph,transform in components:pen.addComponent(glyph,transform)
        font['glyf'][name]=pen.glyph();font['hmtx'].metrics[name]=(round(width),0)
        font.setGlyphOrder(font.getGlyphOrder()+([name] if name not in font.getGlyphOrder() else []))
        for table in font['cmap'].tables:
            if table.isUnicode():table.cmap[code]=name
    prime=cmap[0x2032];advance=font['hmtx'].metrics[prime][0]
    add(0x2034,'thermodrawTriplePrime',[(prime,(1,0,0,1,i*advance,0)) for i in range(3)],advance*3)
    upem=font['head'].unitsPerEm
    for code,base,offset in [(0x207B,0x2212,.35),(0x207A,0x2B,.35),(0x208B,0x2212,-.15),(0x208A,0x2B,-.15)]:
        glyph=cmap[base];width=font['hmtx'].metrics[glyph][0]*.6
        add(code,'thermodrawScientific'+str(code),[(glyph,(.6,0,0,.6,0,round(offset*upem)))],width)
    return font
