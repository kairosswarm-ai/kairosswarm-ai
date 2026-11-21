import math
from PIL import Image, ImageDraw, ImageFilter, ImageFont
S=3200; OUT=800
FB="/home/claude/kairosswarm-ai/fonts/Inter-Black.otf"
def bolt(cx,cy,s,pts=None):
    pts=pts or [(0.12,-0.5),(-0.26,0.06),(-0.03,0.06),(-0.13,0.5),(0.28,-0.08),(0.05,-0.08),(0.17,-0.5)]
    return [(cx+x*s,cy+y*s) for x,y in pts]
def radial(size,inner,outer):
    im=Image.new("RGB",(size,size),outer); d=ImageDraw.Draw(im)
    for r in range(size//2,0,-8):
        t=r/(size/2); c=tuple(int(inner[i]*(1-t)+outer[i]*t) for i in range(3))
        d.ellipse((size/2-r,size/2-r,size/2+r,size/2+r),fill=c)
    return im
def glow(im,mask_draw_fn,color,blur,strength=1.0):
    m=Image.new("L",im.size,0); mask_draw_fn(ImageDraw.Draw(m))
    m=m.filter(ImageFilter.GaussianBlur(blur)).point(lambda v:int(min(255,v*strength)))
    im.paste(Image.new("RGB",im.size,color),(0,0),m)
def save(im,name): im.resize((OUT,OUT),Image.LANCZOS).save(f"/home/claude/logos/{name}.png")

# 1) Gold coin with a bolt
im=radial(S,(30,36,52),(8,10,16)); d=ImageDraw.Draw(im)
c=S/2; R=S*0.36
glow(im,lambda g:g.ellipse((c-R,c-R,c+R,c+R),fill=255),(255,190,40),S*0.04,0.5); d=ImageDraw.Draw(im)
d.ellipse((c-R,c-R,c+R,c+R),fill=(255,196,0))
d.ellipse((c-R*0.86,c-R*0.86,c+R*0.86,c+R*0.86),fill=(255,214,51),outline=(214,150,0),width=int(S*0.012))
for k in range(36):
    a=2*math.pi*k/36; r1=R*0.92; r2=R*0.98
    d.line((c+r1*math.cos(a),c+r1*math.sin(a),c+r2*math.cos(a),c+r2*math.sin(a)),fill=(214,150,0),width=int(S*0.008))
d.polygon(bolt(c,c,R*1.25),fill=(16,18,24))
save(im,"logo1_coin")

# 2) Rising-arrow bolt (green neon)
im=radial(S,(20,40,34),(6,9,12)); d=ImageDraw.Draw(im)
P=[(0.18,-0.52),(-0.30,0.10),(-0.04,0.10),(-0.16,0.52),(0.34,-0.12),(0.08,-0.12),(0.22,-0.52)]
B=bolt(c,c*1.02,S*0.62,P)
glow(im,lambda g:g.polygon(B,fill=255),(46,214,120),S*0.05,1.2); d=ImageDraw.Draw(im)
d.polygon(B,fill=(46,214,120))
# arrow head at top
tip=(c+0.30*S*0.62, c*1.02-0.62*S*0.62)
d.polygon([(tip[0],tip[1]-S*0.02),(tip[0]-S*0.13,tip[1]+S*0.10),(tip[0]+S*0.08,tip[1]+S*0.12)],fill=(46,214,120))
save(im,"logo2_arrowbolt")

# 3) Monogram: C ring + bolt, yellow/black
im=Image.new("RGB",(S,S),(255,204,0)); d=ImageDraw.Draw(im)
R=S*0.30; w=int(S*0.11)
d.arc((c-R,c-R,c+R,c+R),start=40,end=320,fill=(14,16,22),width=w)
d.polygon(bolt(c+S*0.05,c,S*0.42),fill=(14,16,22))
save(im,"logo3_monogram")

# preview with circle crop
prev=Image.new("RGB",(3*420+40,460),(245,245,245))
for i,n in enumerate(["logo1_coin","logo2_arrowbolt","logo3_monogram"]):
    l=Image.open(f"/home/claude/logos/{n}.png").resize((400,400),Image.LANCZOS)
    m=Image.new("L",(400,400),0); ImageDraw.Draw(m).ellipse((0,0,399,399),fill=255)
    prev.paste(l,(20+i*420,20),m)
    sm=l.resize((48,48),Image.LANCZOS); ms=m.resize((48,48)); prev.paste(sm,(20+i*420+176,410),ms)
prev.save("/home/claude/logos/preview.png")
