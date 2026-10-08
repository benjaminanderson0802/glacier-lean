from PIL import Image, ImageDraw, ImageFont
W,H=427,267
P=dict(void=(8,18,38),navy=(20,40,74),navy2=(34,64,108),navy3=(52,92,146),ice0=(244,250,255),ice1=(222,236,249),ice2=(196,219,241),ice3=(160,195,229),ice4=(118,160,206),ink=(22,44,78),ink2=(66,98,138),white=(255,255,255),ok=(56,168,88),ok2=(120,220,130),warn=(236,178,40),bad=(214,72,72),gold=(252,214,110),shadow=(12,28,52))
im=Image.new('RGB',(W,H),P['void']); d=ImageDraw.Draw(im); d.fontmode="1"
T=ImageFont.truetype('PressStart2P.ttf',8); TS=T; HD=ImageFont.truetype('PressStart2P.ttf',8); BIG=ImageFont.truetype('PressStart2P.ttf',16)
def dither_v(x0,y0,x1,y1,c0,c1,steps=6):
    h=y1-y0
    for y in range(y0,y1):
        t=(y-y0)/max(1,h-1)*steps; k=int(t); f=t-k
        a=c0 if k%2==0 else c1
        for x in range(x0,x1):
            mix=[c0,c1]
            # 4-level ordered dither between c0->c1 bands
            lvl=(y-y0)/max(1,h-1)
            th=[[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]][y%4][x%4]/16
            im.putpixel((x,y), c1 if lvl>th else c0)
# backdrop: dithered sky + pixel mountains
dither_v(0,0,W,H,P['ice3'],P['ice4'])
import random; random.seed(3)
pts=[(0,200),(40,150),(70,175),(110,110),(150,160),(190,120),(240,175),(280,100),(330,165),(380,125),(427,170),(427,267),(0,267)]
d.polygon(pts,fill=P['ice1'])
pts2=[(0,230),(60,190),(120,225),(200,170),(270,220),(340,180),(427,215),(427,267),(0,267)]
d.polygon(pts2,fill=P['ice2'])
for (x,y) in [(110,110),(190,120),(280,100),(380,125)]:
    d.polygon([(x,y),(x-10,y+12),(x-4,y+9),(x,y+14),(x+5,y+8),(x+11,y+12)],fill=P['white'])
for i in range(60):
    x=random.randrange(W); y=random.randrange(H); im.putpixel((x,y),P['white'])
def frame(x0,y0,x1,y1,fill=P['ice0'],title=None,dark=False):
    # drop shadow
    d.rectangle([x0+3,y0+3,x1+3,y1+3],fill=P['shadow'])
    d.rectangle([x0,y0,x1,y1],fill=P['navy'])            # outer 1px navy
    d.rectangle([x0+1,y0+1,x1-1,y1-1],fill=P['white'] if not dark else P['navy3'])
    d.rectangle([x0+2,y0+2,x1-1,y1-1],fill=P['ice4'] if not dark else P['shadow'])   # bevel shadow
    d.rectangle([x0+2,y0+2,x1-2,y1-2],fill=fill)
    for (cx,cy) in [(x0,y0),(x1,y0),(x0,y1),(x1,y1)]: im.putpixel((cx,cy),P['void'])  # rounded pixel corners
    if title:
        d.rectangle([x0+2,y0+2,x1-2,y0+12],fill=P['navy2'] if not dark else P['navy'])
        d.line([x0+2,y0+13,x1-2,y0+13],fill=P['navy'])
        d.text((x0+6,y0+4),title,font=HD,fill=P['white'])
def icon(x,y,kind,c):
    pix={'home':["...##...","..####..",".######.","########",".##..##.",".##..##.",".######.","........"],
         'build':["......##",".....###","....###.","#..###..","##.##...",".###....","..##....",".#......"],
         'auto':["###.....","#.#.....","###.....",".#......",".####...","....#...","...###..","...#.#.."],
         'mem':["######..","#....##.","#.##..#.","#......#","#.####.#","#......#","#.####.#","########"],
         'set':["...##...",".#.##.#.","########",".##..##.",".##..##.","########",".#.##.#.","...##..."],
         'warn':[".######.","##.##.##","##.##.##","##.##.##","###..###","##.##.##",".######.","........"],
         'note':["#####...","#...##..","#.###.#.","#.....#.","#.####..","#......#","#.####.#","########"]}[kind]
    for j,row in enumerate(pix):
        for i,ch in enumerate(row):
            if ch=='#': im.putpixel((x+i,y+j),c)
# main window
frame(4,4,422,262,fill=P['ice1'])
d.rectangle([6,6,420,18],fill=P['navy2']); d.line([6,19,420,19],fill=P['navy'])
icon(9,8,'home',P['white']); d.text((21,8),"GLACIER",font=HD,fill=P['white']); d.text((83,8),"- HOME",font=HD,fill=P['ice2'])
for k,x in enumerate([389,400,411]):
    d.rectangle([x,8,x+8,16],fill=P['ice0']); d.line([x,16,x+8,16],fill=P['ice4']); d.line([x+8,8,x+8,16],fill=P['ice4'])
    d.text((x+1,8),["_","o","x"][k],font=HD,fill=P['navy'])
# menu window
frame(9,24,118,190,title="MENU")
items=[('home','Home'),('build','Build'),('auto','Automations'),('mem','Memory'),('set','Settings')]
for n,(k,label) in enumerate(items):
    y=42+n*22
    if n==0:
        d.rectangle([12,y-3,115,y+12],fill=P['navy2']); col=P['white']
        d.polygon([(12,y+1),(12,y+9),(16,y+5)],fill=P['gold'])  # cursor
    else: col=P['ink']
    icon(18,y+1,k,col); d.text((30,y+1),label,font=T,fill=col)
# party/status window under menu
frame(9,196,118,240,title="ENGINES")
d.rectangle([14,214,18,218],fill=P['ok']); d.text((22,212),"Codex",font=T,fill=P['ink'])
d.rectangle([14,226,18,230],fill=P['ok']); d.text((22,224),"granite",font=T,fill=P['ink'])
# header window
frame(124,24,417,48)
d.text((131,29),"HOME",font=BIG,fill=P['navy'])
# banner scene inside header
bx0,by0,bx1,by1=196,27,248,45
for y in range(by0,by1+1):
    for x in range(bx0,bx1+1):
        th=[[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]][y%4][x%4]/16
        im.putpixel((x,y),P['ice2'] if (y-by0)/(by1-by0)>th else P['ice0'])
d.polygon([(bx0,by1),(bx0+10,by0+8),(bx0+20,by0+2),(bx0+30,by0+11),(bx0+40,by0+5),(bx1,by0+12),(bx1,by1)],fill=P['ice4'])
for px,py in [(bx0+20,2),(bx0+40,5)]:
    d.polygon([(px,by0+py),(px-4,by0+py+5),(px+4,by0+py+5)],fill=P['white'])
d.rectangle([bx0,by1-3,bx1,by1],fill=P['ice3'])
t2="4 need you"; w2=d.textlength(t2,font=T); d.text((413-w2,32),t2,font=T,fill=P['bad'])
t1="2 running"; w1=d.textlength(t1,font=T); d.text((413-w2-8-w1,32),t1,font=T,fill=P['ink'])
# needs you
frame(124,54,280,160,title="NEEDS YOU [4]")
rows=[("Approve plan","Game"),("Platform?","Game"),("Backup fail","Files"),("Moved twice","Tidy")]
for n,(a,b) in enumerate(rows):
    y=74+n*20
    if n==0: d.rectangle([127,y-3,277,y+13],fill=P['ice2'])
    icon(130,y+1,'warn',P['bad'] if n>1 else P['warn']); d.text((142,y+1),a,font=T,fill=P['ink']); bw=d.textlength(b,font=T); d.text((274-bw,y+1),b,font=T,fill=P['ink2'])

# teams with HP-style bars
frame(286,54,417,160,title="TEAMS")
teams=[("Game proto",7,18,P['warn']),("Outreach",11,12,P['ok']),("Web monitor",3,3,P['ok'])]
for n,(nm,a,b,c) in enumerate(teams):
    y=72+n*28
    d.text((292,y),nm,font=T,fill=P['ink']); d.text((411-d.textlength(f'{a}/{b}',font=T),y),f"{a}/{b}",font=T,fill=P['ink2'])
    d.rectangle([292,y+10,411,y+16],fill=P['navy']); d.rectangle([293,y+11,410,y+15],fill=P['shadow'])
    w=int(117*a/b); d.rectangle([293,y+11,293+w,y+15],fill=c); d.line([293,y+11,293+w,y+11],fill=P['white'] if c==P['ok'] else P['gold'])
# dialogue-box activity log (dark, like a game text box)
frame(124,166,417,240,title="LOG",dark=True,fill=P['navy'])
log=["08:22 Lead: task 7 player moves","08:23 Builder: 12 checks run","08:24 Checker: 12/12 pass","08:24 Lead: next, task 8"]
for n,l in enumerate(log): d.text((130,183+n*13),l,font=T,fill=P['ice0'] if n<3 else P['gold'])
d.polygon([(408,232),(414,232),(411,236)],fill=P['gold'])
# hint bar
d.rectangle([6,246,420,260],fill=P['ice2']); d.line([6,245,420,245],fill=P['navy'])
hints=[("F1","Help"),("A","Approve"),("B","Build"),("K","Command"),("ESC","Menu")]
x=14
for k,v in hints:
    kw=int(d.textlength(k,font=HD))+6
    d.rectangle([x,248,x+kw,258],fill=P['navy2']); d.text((x+3,250),k,font=HD,fill=P['white']); d.text((x+kw+4,250),v,font=T,fill=P['ink']); x+=kw+int(d.textlength(v,font=T))+12
im.resize((W*3,H*3),Image.NEAREST).save('retro_game_home_ps2p.png')
print("ok")
