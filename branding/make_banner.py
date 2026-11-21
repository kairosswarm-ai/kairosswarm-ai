from PIL import Image, ImageDraw, ImageFont
import math
FB="/home/claude/kairosswarm-ai/fonts/Inter-Black.otf"; FS="/home/claude/kairosswarm-ai/fonts/Inter-SemiBold.otf"
logo=Image.open('/mnt/user-data/uploads/7502087c-image.png').convert('RGB')
W,H=2560,1440; YEL=(255,204,0); BLK=(14,16,22); WHITE=(242,244,247)
SAFE_W,SAFE_H=1546,423
def circ(img,size):
    l=img.resize((size,size),Image.LANCZOS); m=Image.new('L',(size*4,size*4),0)
    ImageDraw.Draw(m).ellipse((0,0,size*4-1,size*4-1),fill=255); return l,m.resize((size,size),Image.LANCZOS)
def curve(x0,y0,x1,y1,k=5,n=120):
    return [(x0+(x1-x0)*i/n, y0-(y0-y1)*((math.exp(k*i/n)-1)/(math.exp(k)-1))) for i in range(n+1)]
def build(bg,grid,curvecol,c1,c2,sub,sub2,ring=None):
    im=Image.new('RGB',(W,H),bg); d=ImageDraw.Draw(im)
    for g in range(0,W,80): d.line((g,0,g,H),fill=grid,width=2)
    for g in range(0,H,80): d.line((0,g,W,g),fill=grid,width=2)
    d.line(curve(0,H*0.97,W,H*0.22),fill=curvecol,width=16)
    fb=ImageFont.truetype(FB,112); fs=ImageFont.truetype(FS,48); fs2=ImageFont.truetype(FS,36)
    LS=250; gap=44
    tw=d.textlength("COMPOUND SHOCK",font=fb)
    total=LS+gap+tw; x0=(W-total)/2; y0=(H-LS)/2
    l,m=circ(logo,LS)
    if ring: d.ellipse((x0-8,y0-8,x0+LS+8,y0+LS+8),fill=ring)
    im.paste(l,(int(x0),int(y0)),m)
    tx=x0+LS+gap; ty=y0+8
    d.text((tx,ty),"COMPOUND",font=fb,fill=c1)
    d.text((tx+d.textlength("COMPOUND ",font=fb),ty),"SHOCK",font=fb,fill=c2)
    d.text((tx+4,ty+148),"The hidden math of money.",font=fs,fill=sub)
    d.text((tx+4,ty+206),"New money facts daily · 9AM · 2PM · 6PM ET",font=fs2,fill=sub2)
    return im, total
a,ta=build((10,12,17),(20,24,32),(70,58,10),WHITE,YEL,YEL,(150,156,168))
b,tb=build(YEL,(245,194,0),(232,182,0),BLK,WHITE,BLK,(80,66,0),ring=BLK)
print(ta)
a.save('banner_dark.jpg',quality=93); b.save('banner_yellow.jpg',quality=93)
rows=[]
for n,im in [('dark',a),('yellow',b)]:
    full=im.resize((960,540)); safe=im.crop(((W-SAFE_W)//2,(H-SAFE_H)//2,(W+SAFE_W)//2,(H+SAFE_H)//2)).resize((960,263))
    p=Image.new('RGB',(960,540+263+20),(255,255,255)); p.paste(full,(0,0)); p.paste(safe,(0,560)); rows.append(p)
c=Image.new('RGB',(1940,rows[0].height),(255,255,255)); c.paste(rows[0],(0,0)); c.paste(rows[1],(980,0)); c.save('both.png')
