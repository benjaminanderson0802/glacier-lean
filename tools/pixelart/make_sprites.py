"""Glacier pixel-art UI kit: draws every frame, button, bar, cursor and icon as small PNG sprites.
Run: python make_sprites.py <out_dir>. All art is original (Apache-2.0, part of Glacier)."""
import sys, os
from PIL import Image
OUT = sys.argv[1] if len(sys.argv) > 1 else "sprites"
os.makedirs(OUT, exist_ok=True)
P = {'.': None, 'N': (20,40,74), 'n': (34,64,108), 'm': (52,92,146), 'W': (255,255,255), 'i': (244,250,255), 'j': (222,236,249),
     'k': (196,219,241), 'l': (160,195,229), 'b': (118,160,206), 'S': (12,28,52), 'g': (56,168,88), 'G': (120,220,130),
     'y': (236,178,40), 'Y': (252,214,110), 'r': (214,72,72), 'R': (255,140,130), 'K': (8,18,38)}
def save(name, rows):
    h, w = len(rows), max(len(r) for r in rows)
    im = Image.new('RGBA', (w, h), (0,0,0,0))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            c = P.get(ch)
            if c: im.putpixel((x, y), c + (255,))
    im.save(os.path.join(OUT, name + '.png'))
# 9-slice window frame, 4px border: navy outline, white highlight top-left, blue shade bottom-right, 1px rounded corners
frame = [".NNNNNNNNNNNNNN.",
         "NWWWWWWWWWWWWWWN",
         "NWiiiiiiiiiiiibN",
         "NWiiiiiiiiiiiibN"] + ["NWiiiiiiiiiiiibN"]*8 + [
         "NWiiiiiiiiiiiibN",
         "NWbbbbbbbbbbbbbN",
         "NbbbbbbbbbbbbbbN",
         ".NNNNNNNNNNNNNN."]
save('frame-light', frame)
save('frame-dark', [r.replace('W','m').replace('i','N').replace('b','S') for r in frame])
save('frame-inset', [r.replace('W','b').replace('b','W') if 0<k<15 else r for k,r in enumerate(frame)])
# title bar strip (tileable horizontally) and its ends
save('titlebar', ["NNNNNNNN"] + ["nnnnnnnn"]*8 + ["NNNNNNNN"])
# buttons 9-slice (3px border)
btn = [".NNNNNNNNNN.","NWWWWWWWWWbN","NWiiiiiiiibN","NWiiiiiiiibN","NWiiiiiiiibN","NWiiiiiiiibN","NWiiiiiiiibN","NWbbbbbbbbbN",".NNNNNNNNNN."]
save('button', btn)
save('button-pressed', [r.replace('W','#').replace('b','W').replace('#','b').replace('i','j') for r in btn])
save('button-primary', [r.replace('W','m').replace('i','n').replace('b','S') for r in btn])
# progress bar track and fills (tileable middle)
save('bar-track', ["NNNNNNNN","NSSSSSSN","NSSSSSSN","NSSSSSSN","NNNNNNNN"])
save('bar-fill-ok', ["GGGGGGGG","gggggggg","gggggggg"])
save('bar-fill-warn', ["YYYYYYYY","yyyyyyyy","yyyyyyyy"])
save('bar-fill-bad', ["RRRRRRRR","rrrrrrrr","rrrrrrrr"])
# menu cursor (gold triangle) and blinking text-box arrow
save('cursor', ["Y.....","YY....","YYY...","YYYY..","YYY...","YY....","Y....."])
save('more-arrow', ["YYYYYYY",".YYYYY.","..YYY..","...Y..."])
# selection bar (tileable)
save('select', ["mmmm"] + ["nnnn"]*10 + ["NNNN"])
# dither tiles for backgrounds (4x4 ordered dither between two ice tones)
bay=[[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]]
for lvl in (4,8,12):
    save(f'dither-{lvl}', ["".join('l' if bay[y][x] < lvl else 'k' for x in range(4)) for y in range(4)])
# 8x8 icons (drawn in navy; the screen recolours them with CSS mask)
icons = {
 'home':  ["...##...","..####..",".######.","########",".##..##.",".##..##.",".######.","........"],
 'build': ["......##",".....###","....###.","#..###..","##.##...",".###....","..##....",".#......"],
 'automations': ["###.....","#.#.....","###.....",".#......",".####...","....#...","...###..","...#.#.."],
 'memory':["######..","#....##.","#.##..#.","#......#","#.####.#","#......#","#.####.#","########"],
 'settings':["...##...",".#.##.#.","########",".##..##.",".##..##.","########",".#.##.#.","...##..."],
 'warn':  [".######.","##.##.##","##.##.##","##.##.##","###..###","##.##.##",".######.","........"],
 'note':  ["#####...","#...##..","#.###.#.","#.....#.","#.####..","#......#","#.####.#","########"],
 'check': ["........",".......#","......##","#....##.","##..##..",".####...","..##....","........"],
 'cross': ["##....##",".##..##.","..####..","...##...","..####..",".##..##.","##....##","........"],
 'play':  [".#......",".##.....",".###....",".####...",".###....",".##.....",".#......","........"],
 'pause': [".##.##..",".##.##..",".##.##..",".##.##..",".##.##..",".##.##..",".##.##..","........"],
 'trash': ["..####..","########",".#.#.#..",".#.#.#..",".#.#.#..",".#.#.#..",".######.","........"],
 'plus':  ["...##...","...##...","...##...","########","########","...##...","...##...","...##..."],
 'team':  [".##..##.","#..##..#","#..##..#",".##..##.","........","########","#......#","########"],
 'search':[".####...","#....#..","#....#..","#....#..",".####...","....##..",".....##.","......##"],
 'min':   ["........","........","........","........","........","........","######..","######.."],
 'max':   ["#######.","#######.","#.....#.","#.....#.","#.....#.","#.....#.","#######.","........"],
 'close': ["##...##.",".##.##..","..###...","..###...",".##.##..","##...##.","........","........"],
 'mountain':["...#....","..###...","..#.##..",".#...##.","#.....##","........","........","........"],
}
for name, rows in icons.items():
    save('icon-' + name, [r.replace('#', 'N') for r in rows])
# logo 17x13
save('logo', [".......N.........","......NWN........",".....NWWWN.......","....NWW.WWN......","...NbW...bbN..N..","...Nb.....bbNNbN.","..Nb.......bbbbbN",".Nb..........bbbN","Nb.............bN","NbbbbbbbbbbbbbbbN","NNNNNNNNNNNNNNNNN"])
print("sprites written to", OUT)
