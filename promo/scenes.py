#!/usr/bin/env python3
"""Generate Q-Mol promo scene stills (1080x1920, vertical / YouTube Short).

Pure Pillow, no network. Produces promo/frames/scene_00.png .. scene_06.png
plus a scaled contact sheet promo/frames/_contact.png for previewing.
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
OUT = os.path.join(os.path.dirname(__file__), "frames")
os.makedirs(OUT, exist_ok=True)

# Brand palette
NAVY_TOP = (10, 37, 64)      # #0A2540
NAVY_BOT = (5, 18, 33)       # #051221
TEAL = (0, 212, 170)         # #00D4AA
AMBER = (255, 176, 32)       # #FFB020
WHITE = (255, 255, 255)
MUTED = (159, 179, 200)      # #9FB3C8
CARD = (16, 46, 74)

FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation",
]


def _find(name_options):
    for d in FONT_DIRS:
        for n in name_options:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    return None


BOLD = _find(["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"])
REG = _find(["DejaVuSans.ttf", "LiberationSans-Regular.ttf"])
MONO = _find(["DejaVuSansMono.ttf", "LiberationMono-Regular.ttf"])


def font(bold, size, mono=False):
    path = MONO if mono else (BOLD if bold else REG)
    return ImageFont.truetype(path, size)


def gradient_bg():
    img = Image.new("RGB", (W, H), NAVY_BOT)
    top = Image.new("RGB", (1, H))
    for y in range(H):
        t = y / (H - 1)
        # ease
        t = t ** 1.15
        r = int(NAVY_TOP[0] + (NAVY_BOT[0] - NAVY_TOP[0]) * t)
        g = int(NAVY_TOP[1] + (NAVY_BOT[1] - NAVY_TOP[1]) * t)
        b = int(NAVY_TOP[2] + (NAVY_BOT[2] - NAVY_TOP[2]) * t)
        top.putpixel((0, y), (r, g, b))
    img = top.resize((W, H))
    # subtle teal glow top-right
    glow = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([W - 520, -260, W + 260, 520], fill=70)
    glow = glow.resize((W, H))
    tint = Image.new("RGB", (W, H), TEAL)
    img = Image.composite(tint, img, glow.point(lambda p: int(p * 0.35)))
    return img


def rounded(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def center_text(draw, cx, y, text, fnt, fill, spacing=0):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    w = bbox[2] - bbox[0]
    draw.text((cx - w / 2, y), text, font=fnt, fill=fill)
    return (bbox[3] - bbox[1])


def wrap(draw, text, fnt, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=fnt) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def molecule(draw, cx, cy, scale=1.0, color=TEAL):
    """A simple stylised benzene-ish ring with nodes."""
    r = 120 * scale
    pts = []
    for i in range(6):
        a = math.radians(60 * i - 90)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    for i in range(6):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % 6]
        draw.line([x1, y1, x2, y2], fill=color, width=int(8 * scale))
    # inner double-bond hint
    for i in (0, 2, 4):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % 6]
        mx1 = x1 + (cx - x1) * 0.18
        my1 = y1 + (cy - y1) * 0.18
        mx2 = x2 + (cx - x2) * 0.18
        my2 = y2 + (cy - y2) * 0.18
        draw.line([mx1, my1, mx2, my2], fill=color, width=int(5 * scale))
    for (x, y) in pts:
        rr = 16 * scale
        draw.ellipse([x - rr, y - rr, x + rr, y + rr], fill=WHITE)
    # a couple of substituent nodes
    for i in (1, 4):
        x, y = pts[i]
        ox = x + (x - cx) * 0.55
        oy = y + (y - cy) * 0.55
        draw.line([x, y, ox, oy], fill=color, width=int(7 * scale))
        rr = 20 * scale
        draw.ellipse([ox - rr, oy - rr, ox + rr, oy + rr], fill=AMBER)


def chip(draw, x, y, text, fnt, fg=WHITE, bg=CARD, accent=TEAL):
    pad = 26
    tw = draw.textlength(text, font=fnt)
    box = [x, y, x + tw + pad * 2, y + 74]
    rounded(draw, box, 20, fill=bg, outline=accent, width=2)
    draw.text((x + pad, y + 20), text, font=fnt, fill=fg)
    return box[2] - box[0]


def footer_brand(draw):
    f = font(True, 40)
    draw.text((70, H - 120), "Q‑Mol", font=f, fill=WHITE)
    dot = 12
    draw.ellipse([70 + draw.textlength("Q‑Mol", font=f) + 18, H - 108, 70 + draw.textlength("Q‑Mol", font=f) + 18 + dot, H - 108 + dot], fill=TEAL)


def base():
    img = gradient_bg()
    return img, ImageDraw.Draw(img)


# ---------- Scenes ----------

def scene0():
    img, d = base()
    molecule(d, W / 2, 560, scale=1.7)
    center_text(d, W / 2, 900, "Q‑MOL", font(True, 190), WHITE)
    center_text(d, W / 2, 1110, "Molecular intelligence,", font(True, 62), TEAL)
    center_text(d, W / 2, 1185, "in your pocket.", font(True, 62), TEAL)
    center_text(d, W / 2, 1320, "RDKit-powered cheminformatics", font(False, 42), MUTED)
    return img


def scene1():
    img, d = base()
    center_text(d, W / 2, 250, "Paste any molecule.", font(True, 74), WHITE)
    # SMILES pill
    smi = "CC(=O)Oc1ccccc1C(=O)O"
    fm = font(False, 46, mono=True)
    tw = d.textlength(smi, font=fm)
    bx = (W - tw - 80) / 2
    rounded(d, [bx, 430, bx + tw + 80, 540], 22, fill=CARD, outline=TEAL, width=3)
    d.text((bx + 40, 458), smi, font=fm, fill=TEAL)
    center_text(d, W / 2, 570, "aspirin · SMILES", font(False, 34), MUTED)
    # result card
    rounded(d, [90, 700, W - 90, 1500], 40, fill=CARD, outline=(30, 70, 105), width=2)
    center_text(d, W / 2, 750, "Q‑Mol result", font(True, 46), WHITE)
    rows = [("Mol. weight", "180.16"), ("logP", "1.31"),
            ("TPSA", "63.6 Å²"), ("H-bond D/A", "1 / 4"),
            ("QED", "0.55"), ("Lipinski", "PASS")]
    y = 850
    for i, (k, v) in enumerate(rows):
        yy = y + i * 100
        d.text((150, yy), k, font=font(False, 44), fill=MUTED)
        vc = TEAL if v == "PASS" else WHITE
        vw = d.textlength(v, font=font(True, 48))
        d.text((W - 150 - vw, yy - 4), v, font=font(True, 48), fill=vc)
        if i < len(rows) - 1:
            d.line([150, yy + 78, W - 150, yy + 78], fill=(28, 62, 94), width=2)
    footer_brand(d)
    return img


def scene2():
    img, d = base()
    center_text(d, W / 2, 300, "50+ descriptors.", font(True, 84), WHITE)
    center_text(d, W / 2, 410, "In seconds.", font(True, 84), TEAL)
    labels = ["MW", "logP", "TPSA", "QED", "HBD", "HBA", "Rot. bonds",
              "Rings", "fsp3", "Murcko", "ECFP4", "InChIKey", "PAINS", "Veber"]
    x, y = 90, 640
    fnt = font(True, 40)
    for lab in labels:
        wch = d.textlength(lab, font=fnt) + 52
        if x + wch > W - 90:
            x = 90
            y += 100
        chip(d, x, y, lab, fnt)
        x += wch + 24
    center_text(d, W / 2, y + 240, "Powered by RDKit", font(False, 44), MUTED)
    footer_brand(d)
    return img


def scene3():
    img, d = base()
    center_text(d, W / 2, 250, "Predict. Screen. Flag.", font(True, 72), WHITE)
    cards = [
        ("ADMET predictions", "solubility · hERG · BBB", TEAL),
        ("Drug-likeness", "Lipinski · Veber rules", TEAL),
        ("PAINS liabilities", "caught before they cost you", AMBER),
    ]
    y = 470
    for title, sub, ac in cards:
        rounded(d, [90, y, W - 90, y + 300], 34, fill=CARD, outline=ac, width=3)
        d.ellipse([140, y + 110, 210, y + 180], outline=ac, width=6)
        d.text((260, y + 70), title, font=font(True, 56), fill=WHITE)
        d.text((260, y + 160), sub, font=font(False, 40), fill=MUTED)
        y += 360
    footer_brand(d)
    return img


def scene4():
    img, d = base()
    center_text(d, W / 2, 300, "Explore chemical space.", font(True, 62), WHITE)
    molecule(d, W / 2, 760, scale=1.2)
    feats = ["Similarity search across millions",
             "Butina clustering",
             "3D conformer generation",
             "Scaffolds · tautomers · reactions"]
    y = 1080
    for f in feats:
        d.ellipse([120, y + 14, 150, y + 44], fill=TEAL)
        d.text((190, y), f, font=font(True, 46), fill=WHITE)
        y += 110
    footer_brand(d)
    return img


def scene5():
    img, d = base()
    center_text(d, W / 2, 300, "Everywhere you work.", font(True, 72), WHITE)
    items = [("REST API", "~30 endpoints"),
             ("Command line", "qmol compute …"),
             ("Android app", "native, offline-ready")]
    y = 560
    for title, sub in items:
        rounded(d, [90, y, W - 90, y + 260], 34, fill=CARD, outline=TEAL, width=3)
        rounded(d, [150, y + 60, 290, y + 200], 24, fill=(8, 28, 48), outline=TEAL, width=3)
        d.text((340, y + 70), title, font=font(True, 58), fill=WHITE)
        d.text((340, y + 155), sub, font=font(False, 40), fill=MUTED)
        y += 320
    footer_brand(d)
    return img


def scene6():
    img, d = base()
    molecule(d, W / 2, 640, scale=1.5)
    center_text(d, W / 2, 940, "Q‑MOL", font(True, 150), WHITE)
    center_text(d, W / 2, 1130, "Compute the molecule.", font(True, 58), TEAL)
    # CTA button
    bw, bh = 640, 150
    bx = (W - bw) / 2
    rounded(d, [bx, 1320, bx + bw, 1320 + bh], 40, fill=TEAL)
    cta = "Download today"
    cf = font(True, 58)
    cw = d.textlength(cta, font=cf)
    d.text((W / 2 - cw / 2, 1355), cta, font=cf, fill=NAVY_BOT)
    center_text(d, W / 2, 1520, "No cloud lock-in · your data stays yours", font(False, 38), MUTED)
    return img


SCENES = [scene0, scene1, scene2, scene3, scene4, scene5, scene6]


def main():
    paths = []
    for i, fn in enumerate(SCENES):
        img = fn()
        p = os.path.join(OUT, f"scene_{i:02d}.png")
        img.save(p)
        paths.append(p)
        print("wrote", p)
    # contact sheet
    cols, rows = 4, 2
    tw, th = 270, 480
    sheet = Image.new("RGB", (cols * tw, rows * th), (0, 0, 0))
    for i, p in enumerate(paths):
        im = Image.open(p).resize((tw, th))
        sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
    sheet.save(os.path.join(OUT, "_contact.png"))
    print("wrote contact sheet")


if __name__ == "__main__":
    main()
