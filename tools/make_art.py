#!/usr/bin/env python3
"""Generates the pencil-sketch encounter art in public/art/*.svg.

Every picture is drawn procedurally from simple shapes, then roughened with
wobble, double strokes, cross-hatching and smudges to look hand-drawn.
Run:  python3 tools/make_art.py
"""
import math
import os
import random
import re

W, H = 320, 200
INK = '#2d2925'
PAPER = '#efe5cf'
OUT = os.path.join(os.path.dirname(__file__), '..', 'public', 'art')


def slug(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def f(v):
    return f'{v:.1f}'.rstrip('0').rstrip('.')


def smooth(pts, closed=False):
    if len(pts) < 3:
        return 'M' + ' L'.join(f'{f(x)},{f(y)}' for x, y in pts)
    P = [pts[-1]] + pts + pts[:2] if closed else [pts[0]] + pts + [pts[-1]]
    d = f'M{f(P[1][0])},{f(P[1][1])}'
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f' C{f(c1[0])},{f(c1[1])} {f(c2[0])},{f(c2[1])} {f(p2[0])},{f(p2[1])}'
    return d + ('Z' if closed else '')


def jit(pts, a):
    return [(x + random.uniform(-a, a), y + random.uniform(-a, a)) for x, y in pts]


def ell(cx, cy, rx, ry, n=22, a0=0.0, a1=2 * math.pi, rot=0.0):
    out = []
    for i in range(n + (0 if a1 - a0 >= 2 * math.pi - 1e-6 else 1)):
        t = a0 + (a1 - a0) * i / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        out.append((cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot)))
    return out


def densify(pts, closed=True, step=10.0):
    out = []
    n = len(pts)
    for i in range(n if closed else n - 1):
        a, b = pts[i], pts[(i + 1) % n]
        k = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
        for j in range(k):
            out.append((a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k))
    if not closed:
        out.append(pts[-1])
    return out


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


class Pic:
    def __init__(self, name):
        self.name = name
        random.seed(slug(name))
        self.defs, self.back, self.el = [], [], []
        self.n = 0

    def nid(self):
        self.n += 1
        return f'k{self.n}'

    # --- strokes ---
    def line(self, pts, w=1.5, closed=False, passes=2, j=1.0, op=0.85, back=False):
        tgt = self.back if back else self.el
        for p in range(passes):
            ww = w * (1 if p == 0 else random.uniform(0.45, 0.7))
            oo = op * (1 if p == 0 else 0.6)
            tgt.append(f'<path d="{smooth(jit(pts, j * (1 + p * 0.6)), closed)}" fill="none" stroke="{INK}" '
                       f'stroke-width="{f(ww)}" stroke-linecap="round" stroke-linejoin="round" opacity="{f(oo)}"/>')

    def fill(self, pts, color=PAPER, op=1.0, back=False):
        (self.back if back else self.el).append(f'<path d="{smooth(pts, True)}" fill="{color}" opacity="{f(op)}"/>')

    def hatch(self, pts, angle=45, gap=4.0, w=0.6, op=0.55, cross=0, back=False):
        cid = self.nid()
        self.defs.append(f'<clipPath id="{cid}"><path d="{smooth(pts, True)}"/></clipPath>')
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        R = math.hypot(max(xs) - min(xs), max(ys) - min(ys)) / 2 + gap
        angles = [angle, angle + 90, angle + 45][: cross + 1]
        d = []
        for ai, ang in enumerate(angles):
            a = math.radians(ang)
            dx, dy = math.cos(a), math.sin(a)
            nx, ny = -dy, dx
            k = -R + random.uniform(0, gap)
            g = gap * (1 + ai * 0.25)
            while k < R:
                ox, oy = cx + nx * k, cy + ny * k
                x0, y0 = ox - dx * R, oy - dy * R
                x1, y1 = ox + dx * R, oy + dy * R
                b = random.uniform(-1.2, 1.2)
                d.append(f'M{f(x0)},{f(y0)} Q{f((x0 + x1) / 2 + nx * b)},{f((y0 + y1) / 2 + ny * b)} {f(x1)},{f(y1)}')
                k += g * random.uniform(0.75, 1.25)
        (self.back if back else self.el).append(
            f'<g clip-path="url(#{cid})"><path d="{" ".join(d)}" fill="none" stroke="{INK}" stroke-width="{f(w)}" '
            f'opacity="{f(op)}" stroke-linecap="round"/></g>')

    def shape(self, pts, w=1.5, hatch=None, solid=True, back=False, j=1.0, sharp=False):
        """Closed outline: paper fill (hides what's behind), optional hatching, then outline."""
        if sharp:
            pts = densify(pts)
        if solid:
            self.fill(pts, back=back)
        if hatch:
            self.hatch(pts, back=back, **hatch)
        self.line(pts, w=w, closed=True, back=back, j=j)

    def smudge(self, cx, cy, rx, ry, op=0.18, back=True):
        (self.back if back else self.el).append(
            f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" fill="{INK}" opacity="{f(op)}" filter="url(#blur)"/>')

    def dot(self, x, y, r=1.6, color=INK, op=0.9):
        self.el.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="{color}" opacity="{f(op)}"/>')

    def glow(self, cx, cy, r, op=0.9):
        self.el.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="url(#glow)" opacity="{f(op)}"/>')

    def svg(self):
        guides = ''.join(
            f'<path d="M{f(random.uniform(0, W))},{f(random.uniform(0, H))} l{f(random.uniform(-90, 90))},{f(random.uniform(-40, 40))}" '
            f'stroke="{INK}" stroke-width=".4" opacity=".12"/>' for _ in range(7))
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<title>{self.name}</title>
<defs>
<filter id="pencil" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="{random.randint(1, 99)}" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="2.4"/></filter>
<filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="1.4" numOctaves="3" result="t"/><feColorMatrix in="t" values="0 0 0 0 0.18  0 0 0 0 0.15  0 0 0 0 0.12  0 0 0 0.35 0"/></filter>
<filter id="blur"><feGaussianBlur stdDeviation="6"/></filter>
<radialGradient id="vig" cx="50%" cy="45%" r="70%"><stop offset="60%" stop-color="{INK}" stop-opacity="0"/><stop offset="100%" stop-color="{INK}" stop-opacity=".35"/></radialGradient>
<radialGradient id="glow"><stop offset="0%" stop-color="#fffaf0" stop-opacity="1"/><stop offset="70%" stop-color="#fffaf0" stop-opacity=".6"/><stop offset="100%" stop-color="#fffaf0" stop-opacity="0"/></radialGradient>
{"".join(self.defs)}
</defs>
<rect width="{W}" height="{H}" fill="{PAPER}"/>
<rect width="{W}" height="{H}" filter="url(#grain)"/>
{guides}
<g filter="url(#pencil)">{"".join(self.back)}{"".join(self.el)}</g>
<rect width="{W}" height="{H}" fill="url(#vig)"/>
</svg>'''


# ---------------- scenery ----------------
def floor(p, y=172, cracks=True):
    p.line([(-5, y + random.uniform(-2, 2)), (80, y + random.uniform(-2, 2)), (170, y + random.uniform(-2, 2)),
            (250, y + random.uniform(-2, 2)), (325, y)], w=1.3, back=True, op=0.6)
    p.hatch([(-5, y), (325, y), (325, 205), (-5, 205)], angle=10, gap=6, op=0.25, back=True)
    if cracks:
        for _ in range(4):
            x = random.uniform(10, 310)
            p.line([(x, y + 4), (x + random.uniform(-14, 14), y + 14), (x + random.uniform(-20, 20), y + 24)],
                   w=0.7, back=True, op=0.4, passes=1)


def bricks(p, top=8, bottom=150, op=0.22):
    y = top
    row = 0
    while y < bottom:
        hgt = random.uniform(16, 22)
        p.line([(-5, y), (325, y)], w=0.6, back=True, op=op, passes=1, j=1.5)
        x = (row % 2) * 22 - 10
        while x < 330:
            p.line([(x, y), (x + random.uniform(-2, 2), y + hgt)], w=0.6, back=True, op=op, passes=1)
            x += random.uniform(38, 52)
        y += hgt
        row += 1


def arch_frame(p, cx=160, top=18, half=120, bottom=175):
    pts = [(cx - half, bottom)] + ell(cx, top + half * 0.6, half, half * 0.6, 14, math.pi, 2 * math.pi) + [(cx + half, bottom)]
    p.line(pts, w=1.6, back=True, op=0.7)
    outer = [(cx - half - 14, bottom)] + ell(cx, top + half * 0.6, half + 14, half * 0.6 + 14, 14, math.pi, 2 * math.pi) + [(cx + half + 14, bottom)]
    p.line(outer, w=1.2, back=True, op=0.6)
    for i in range(1, 9):
        t = math.pi + math.pi * i / 9
        a = (cx + half * math.cos(t), top + half * 0.6 + half * 0.6 * math.sin(t))
        b = (cx + (half + 14) * math.cos(t), top + half * 0.6 + (half * 0.6 + 14) * math.sin(t))
        p.line([a, b], w=0.9, back=True, op=0.55, passes=1)


def rock(p, cx, cy, r, shade=True):
    pts = [(cx + r * random.uniform(0.75, 1.1) * math.cos(t), cy + r * random.uniform(0.6, 0.9) * math.sin(t))
           for t in [i * 2 * math.pi / 9 for i in range(9)]]
    p.shape(pts, w=1.3, hatch=dict(angle=random.choice([30, 60, 120]), gap=3.5, op=0.45) if shade else None)
    return pts


def torch(p, x, y):
    p.line([(x, y), (x - 2, y + 30)], w=2.5)
    p.glow(x, y - 8, 30)
    flame = [(x, y - 22), (x + 6, y - 8), (x + 3, y), (x - 4, y), (x - 6, y - 9)]
    p.shape(flame, w=1.1)


# ---------------- figure helpers ----------------
def limb(p, pts, width, hatch_op=0.35, w=1.3):
    """Thick limb as an outlined band along a polyline."""
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        a = pts[max(0, i - 1)]
        b = pts[min(len(pts) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        ww = width * (1 - 0.25 * i / max(1, len(pts) - 1)) / 2
        left.append((x + nx * ww, y + ny * ww))
        right.append((x - nx * ww, y - ny * ww))
    band = left + right[::-1]
    p.shape(band, w=w, hatch=dict(angle=random.choice([50, 130]), gap=3.2, op=hatch_op))


def wings(p, sx, sy, span, up=1.0, side=1, ribs=4):
    tip = (sx + side * span, sy - span * 0.55 * up)
    top = [(sx, sy), lerp((sx, sy), tip, 0.45), (tip[0] - side * span * 0.1, tip[1] - span * 0.08), tip]
    bottom = []
    for i in range(ribs + 1):
        t = i / ribs
        bx = tip[0] + (sx - tip[0]) * t
        by = tip[1] + (sy + span * 0.35 - tip[1]) * t
        bottom.append((bx, by))
        if i < ribs:
            mid = lerp((bx, by), (tip[0] + (sx - tip[0]) * (t + 1 / ribs), tip[1] + (sy + span * 0.35 - tip[1]) * (t + 1 / ribs)), 0.5)
            bottom.append((mid[0] - side * span * 0.04, mid[1] - span * 0.1))
    pts = top + bottom[1:]
    p.shape(pts, w=1.3, hatch=dict(angle=70 if side > 0 else 110, gap=3.6, op=0.35))
    for i in range(1, ribs):
        t = i / ribs
        p.line([(sx, sy), (tip[0] + (sx - tip[0]) * t, tip[1] + (sy + span * 0.35 - tip[1]) * t)], w=0.8, passes=1, op=0.6)


def face(p, hx, hy, r, kind='angry', look=0):
    ex = r * 0.38
    ey = hy - r * 0.05
    if kind == 'glow':
        for s in (-1, 1):
            p.el.append(f'<ellipse cx="{f(hx + s * ex + look)}" cy="{f(ey)}" rx="{f(r * 0.17)}" ry="{f(r * 0.1)}" fill="#fffaf0"/>')
        return
    for s in (-1, 1):
        p.dot(hx + s * ex + look, ey, r * 0.11)
        p.line([(hx + s * ex * 1.6 + look, ey - r * 0.28), (hx + s * ex * 0.4 + look, ey - r * 0.14)], w=1.1, passes=1)
    if kind == 'angry':
        teeth = []
        for i in range(7):
            teeth.append((hx - r * 0.42 + i * r * 0.14 + look, hy + r * 0.42 + (r * 0.12 if i % 2 else 0)))
        p.line(teeth, w=1.0, passes=1, j=0.3)
    elif kind == 'grim':
        p.line([(hx - r * 0.35 + look, hy + r * 0.45), (hx + r * 0.35 + look, hy + r * 0.4)], w=1.0, passes=1)


def humanoid(p, cx, g, h, build='normal', head='plain', weapon=None, cloak=False, hunch=0.0, skeleton=False,
             armor=False, tail=False, wing=False, face_kind='angry', legs='normal', robe=False, shade=0.35):
    r = h * (0.1 if build == 'bulky' else 0.115)
    sw = h * {'thin': 0.13, 'normal': 0.17, 'bulky': 0.25}[build]
    hipy = g - h * 0.44
    shy = g - h + 2.3 * r
    hx, hy = cx + hunch * h * 0.25, g - h + r
    hw = sw * 0.72
    p.smudge(cx, g + 2, h * 0.38, 6, op=0.25)
    if wing:
        wings(p, cx - sw * 0.6, shy + 4, h * 0.55, side=-1)
        wings(p, cx + sw * 0.6, shy + 4, h * 0.55, side=1)
    if cloak:
        cl = [(cx - sw * 0.9, shy)] + [(cx - sw * 1.5 - i * 2 + random.uniform(-3, 3), g - 4 - (8 if i % 2 else 0)) for i in range(1)] + \
             [(cx - sw * 0.6 + i * sw * 0.42, g - 2 - (9 if i % 2 else 0)) for i in range(6)] + [(cx + sw * 1.5, g - 6), (cx + sw * 0.9, shy)]
        p.shape(cl, w=1.4, hatch=dict(angle=80, gap=3, op=0.5, cross=1))
    if tail:
        p.line([(cx - hw, hipy + 4), (cx - h * 0.35, hipy + h * 0.2), (cx - h * 0.55, g - 4), (cx - h * 0.7, g - 12)], w=6, passes=1, op=0.5)
        p.line([(cx - hw, hipy + 4), (cx - h * 0.35, hipy + h * 0.2), (cx - h * 0.55, g - 4), (cx - h * 0.7, g - 12)], w=1.2)
    # legs
    lw = h * (0.07 if build != 'bulky' else 0.1)
    if robe:
        rb = [(cx - sw * 0.9, shy + 4), (cx - sw * 1.25, g), (cx + sw * 1.25, g), (cx + sw * 0.9, shy + 4)]
        p.shape(rb, w=1.4, hatch=dict(angle=95, gap=3.2, op=shade))
    elif skeleton:
        for s in (-1, 1):
            p.line([(cx + s * hw * 0.5, hipy), (cx + s * hw * 0.8, (hipy + g) / 2), (cx + s * hw * 1.0, g - 1), (cx + s * hw * 1.0 + s * 7, g)], w=2.0)
            p.dot(cx + s * hw * 0.8, (hipy + g) / 2, 2.4)
    else:
        for s in (-1, 1):
            if legs == 'bird':
                p.line([(cx + s * hw * 0.5, hipy), (cx + s * hw * 0.9, (hipy + g) / 2 - 4), (cx + s * hw * 0.6, g)], w=2.2)
                for k in (-1, 0, 1):
                    p.line([(cx + s * hw * 0.6, g), (cx + s * hw * 0.6 + k * 6, g + 3)], w=1.2, passes=1)
            else:
                limb(p, [(cx + s * hw * 0.55, hipy), (cx + s * hw * 0.85, (hipy + g) / 2), (cx + s * hw * 1.05, g - 2)], lw * 2, hatch_op=shade)
                p.shape([(cx + s * hw * 1.05 - lw, g - 4), (cx + s * hw * 1.05 + s * lw * 1.8, g - 2), (cx + s * hw * 1.05 + s * lw * 1.8, g + 1), (cx + s * hw * 1.05 - lw, g + 1)], w=1.2)
    # torso
    torso = [(cx - sw, shy), (cx + hunch * 6, shy - 3), (cx + sw, shy), (cx + hw * 1.05, (shy + hipy) / 2), (cx + hw, hipy), (cx - hw, hipy), (cx - hw * 1.05, (shy + hipy) / 2)]
    if skeleton:
        p.line([(cx, shy), (cx, hipy)], w=2.2)
        for i in range(5):
            yy = shy + 4 + i * (hipy - shy - 8) / 5
            ww = sw * (0.9 - i * 0.1)
            p.line(ell(cx, yy + 2, ww, 4, 10, math.pi * 1.05, math.pi * 1.95)[::-1] + ell(cx, yy + 2, ww, 4, 10, 0.05 * math.pi, 0.95 * math.pi), w=1.1, passes=1)
        p.line(ell(cx, hipy, hw, 6, 12, 0, math.pi), w=1.4)
    else:
        p.shape(torso, w=1.6, hatch=dict(angle=60, gap=3.0 if armor else 3.6, op=shade + (0.15 if armor else 0), cross=1 if armor else 0))
        p.hatch([(cx + sw * 0.25, shy), (cx + sw, shy), (cx + hw * 1.05, (shy + hipy) / 2), (cx + hw, hipy), (cx + hw * 0.3, hipy)],
                angle=30, gap=2.2, op=0.45)
        if armor:
            p.line([(cx - sw * 0.8, shy + 10), (cx + sw * 0.8, shy + 10)], w=1.0, passes=1)
            p.line([(cx, shy + 2), (cx, hipy - 2)], w=0.9, passes=1)
        p.line([(cx - hw, hipy - 5), (cx + hw, hipy - 5)], w=1.6)  # belt
    # arms
    aw = lw * 1.5
    lhand = (cx - sw - h * 0.06, hipy + h * 0.02)
    rhand = (cx + sw + h * 0.16, shy - h * 0.06) if weapon else (cx + sw + h * 0.06, hipy)
    if skeleton:
        p.line([(cx - sw, shy), (cx - sw - h * 0.05, (shy + hipy) / 2), lhand], w=2.0)
        p.line([(cx + sw, shy), (cx + sw + h * 0.12, shy + h * 0.1), rhand], w=2.0)
    else:
        limb(p, [(cx - sw, shy + 2), (cx - sw - h * 0.06, (shy + hipy) / 2), lhand], aw, hatch_op=shade)
        limb(p, [(cx + sw, shy + 2), (cx + sw + h * 0.13, shy + h * 0.11), rhand], aw, hatch_op=shade)
    for hand in (lhand, rhand):
        p.shape(ell(hand[0], hand[1], aw * 0.55, aw * 0.5, 8), w=1.1)
    if weapon:
        weapon_draw(p, weapon, rhand, h)
    # head
    if head == 'hood':
        hood = [(hx - r * 1.4, hy + r * 1.6), (hx - r * 1.3, hy - r * 0.2), (hx - r * 0.3, hy - r * 1.6), (hx + r * 0.6, hy - r * 1.4),
                (hx + r * 1.4, hy - r * 0.1), (hx + r * 1.5, hy + r * 1.6)]
        p.shape(hood, w=1.5, hatch=dict(angle=70, gap=3, op=0.45))
        hole = ell(hx, hy + r * 0.15, r * 0.8, r * 0.95, 14)
        p.fill(hole, color=INK, op=0.75)
        face(p, hx, hy, r, 'glow')
        return
    if head == 'snout':
        sn = ell(hx + r * 0.5, hy + r * 0.1, r * 1.45, r * 0.85, 18)
        p.shape(sn, w=1.5, hatch=dict(angle=40, gap=3.6, op=shade))
        p.dot(hx + r * 1.7, hy - r * 0.1, 1.4)
        p.dot(hx + r * 0.2, hy - r * 0.35, r * 0.13)
        p.line([(hx + r * 0.6, hy + r * 0.45), (hx + r * 1.8, hy + r * 0.35)], w=1, passes=1)
        for i in range(4):
            p.line([(hx + r * (0.8 + i * 0.25), hy + r * 0.42), (hx + r * (0.9 + i * 0.25), hy + r * 0.62)], w=0.8, passes=1)
        return
    hd = ell(hx, hy, r, r * 1.08, 16)
    if head in ('ears', 'crown') and not skeleton:
        for s in (-1, 1):
            ear = [(hx + s * r * 0.8, hy - r * 0.2), (hx + s * r * 2.1, hy - r * 0.9), (hx + s * r * 0.9, hy + r * 0.35)]
            p.shape(ear, w=1.3, hatch=dict(angle=45, gap=3, op=0.4))
    if head == 'horns':
        for s in (-1, 1):
            hn = [(hx + s * r * 0.5, hy - r * 0.8), (hx + s * r * 1.3, hy - r * 1.7), (hx + s * r * 1.1, hy - r * 2.4),
                  (hx + s * r * 1.6, hy - r * 1.6), (hx + s * r * 0.9, hy - r * 0.6)]
            p.shape(hn, w=1.2, hatch=dict(angle=30, gap=2.6, op=0.5))
    p.shape(hd, w=1.6, hatch=dict(angle=130, gap=4, op=0.25 if not skeleton else 0.1))
    p.hatch(ell(hx, hy, r, r * 1.08, 10, -math.pi / 2, math.pi / 2) + ell(hx + r * 0.25, hy, r * 0.6, r * 1.0, 10, math.pi / 2, -math.pi / 2)[::-1][::-1],
            angle=35, gap=2.0, op=0.4)
    if skeleton:
        for s in (-1, 1):
            sock = ell(hx + s * r * 0.38, hy - r * 0.05, r * 0.24, r * 0.27, 10)
            p.fill(sock, color=INK, op=0.85)
        p.fill([(hx, hy + r * 0.2), (hx - r * 0.12, hy + r * 0.42), (hx + r * 0.12, hy + r * 0.42)], color=INK, op=0.8)
        for i in range(5):
            p.line([(hx - r * 0.4 + i * r * 0.2, hy + r * 0.6), (hx - r * 0.4 + i * r * 0.2, hy + r * 0.85)], w=0.8, passes=1)
    elif head == 'helm':
        p.hatch(hd, angle=20, gap=2.5, op=0.6, cross=1)
        p.fill([(hx - r * 0.7, hy - r * 0.1), (hx + r * 0.7, hy - r * 0.1), (hx + r * 0.7, hy + r * 0.12), (hx - r * 0.7, hy + r * 0.12)], color=INK, op=0.9)
        p.line([(hx, hy - r * 1.05), (hx - r * 0.6, hy - r * 2.2), (hx - r * 1.6, hy - r * 2.0)], w=2.4, passes=2)
    else:
        face(p, hx, hy, r, face_kind, look=hunch * r * 0.3)
    if head == 'crown':
        cw = r * 0.95
        cr = [(hx - cw, hy - r * 0.7), (hx - cw, hy - r * 1.6), (hx - cw * 0.5, hy - r * 1.1), (hx, hy - r * 1.9),
              (hx + cw * 0.5, hy - r * 1.1), (hx + cw, hy - r * 1.6), (hx + cw, hy - r * 0.7)]
        p.shape(cr, w=1.3, hatch=dict(angle=20, gap=2.2, op=0.35))
        p.dot(hx, hy - r * 1.05, 1.8, color=PAPER, op=1)
    if head == 'witch':
        brim = ell(hx, hy - r * 0.75, r * 2.0, r * 0.4, 16)
        p.shape(brim, w=1.3, hatch=dict(angle=10, gap=2.6, op=0.55))
        cone = [(hx - r * 1.0, hy - r * 0.85), (hx - r * 0.2, hy - r * 2.6), (hx + r * 0.8, hy - r * 3.6), (hx + r * 0.5, hy - r * 2.4), (hx + r * 1.0, hy - r * 0.85)]
        p.shape(cone, w=1.4, hatch=dict(angle=70, gap=2.6, op=0.55, cross=1))


def weapon_draw(p, kind, hand, h):
    x, y = hand
    if kind == 'sword':
        p.shape([(x - 2, y + 4), (x - 3, y - h * 0.4), (x, y - h * 0.46), (x + 3, y - h * 0.4), (x + 2, y + 4)], w=1.2)
        p.line([(x - 9, y - 2), (x + 9, y - 3)], w=2.4)
    elif kind == 'club':
        p.shape([(x - 2, y + 6), (x - 7, y - h * 0.36), (x + 3, y - h * 0.4), (x + 9, y - h * 0.34), (x + 2, y + 6)], w=1.4,
                hatch=dict(angle=80, gap=3, op=0.5))
        for i in range(3):
            p.line([(x - 6 + i * 6, y - h * 0.32 - 2), (x - 8 + i * 6, y - h * 0.38)], w=1.2, passes=1)
    elif kind == 'dagger':
        p.shape([(x - 1.5, y + 2), (x - 2, y - h * 0.22), (x, y - h * 0.26), (x + 2, y - h * 0.22), (x + 1.5, y + 2)], w=1.1)
        p.line([(x - 6, y - 1), (x + 6, y - 1)], w=2)
    elif kind in ('staff', 'skullstaff'):
        p.line([(x + 1, y + h * 0.4), (x - 1, y - h * 0.36)], w=2.6)
        top = (x - 1, y - h * 0.41)
        if kind == 'staff':
            p.glow(top[0], top[1], 18)
            p.shape(ell(top[0], top[1], 6, 6, 10), w=1.2)
        else:
            sk = ell(top[0], top[1], 7, 7.5, 12)
            p.shape(sk, w=1.2)
            for s in (-1, 1):
                p.fill(ell(top[0] + s * 2.6, top[1] - 0.5, 1.8, 2.1, 8), color=INK)
    elif kind == 'spear':
        p.line([(x + 2, y + h * 0.35), (x - 2, y - h * 0.38)], w=2.2)
        p.shape([(x - 2, y - h * 0.38), (x - 6, y - h * 0.44), (x - 3, y - h * 0.55), (x + 1, y - h * 0.44)], w=1.2)
    elif kind == 'axe':
        p.line([(x, y + h * 0.1), (x - 1, y - h * 0.5)], w=2.6)
        p.shape([(x - 1, y - h * 0.46), (x + 16, y - h * 0.58), (x + 18, y - h * 0.4), (x + 14, y - h * 0.3), (x - 1, y - h * 0.36)], w=1.3,
                hatch=dict(angle=20, gap=2.5, op=0.4))
    elif kind == 'rope':
        p.line([(x, y)] + [(x + 10 + i * 9, y + 22 + 6 * math.sin(i)) for i in range(5)], w=1.6)
        p.line(ell(x + 60, y + 32, 14, 6, 14), w=1.3, closed=True)


def beast(p, cx, g, L, Ht, kind='wolf'):
    by = g - Ht * 0.55
    rx, ry = L / 2, Ht * 0.3
    p.smudge(cx, g + 2, L * 0.55, 6, op=0.25)
    # tail
    if kind == 'rat':
        p.line([(cx - rx * 0.9, by), (cx - rx * 1.5, by + 8), (cx - rx * 1.9, by - 4), (cx - rx * 2.3, by + 4)], w=1.8)
    else:
        tail = [(cx - rx * 0.85, by - ry * 0.4), (cx - rx * 1.5, by - ry * 1.2), (cx - rx * 1.75, by - ry * 0.4), (cx - rx * 1.45, by + ry * 0.1), (cx - rx * 0.85, by + ry * 0.3)]
        p.shape(tail, w=1.3, hatch=dict(angle=30, gap=3, op=0.45))
    # far legs (darker), near legs
    for i, lx in enumerate([cx - rx * 0.55, cx + rx * 0.55, cx - rx * 0.35, cx + rx * 0.75]):
        dark = i < 2
        knee = (lx + (6 if i % 2 else -4), by + ry + (g - by - ry) * 0.5)
        limb(p, [(lx, by + ry * 0.3), knee, (lx + (2 if i % 2 else -3), g - 1)], Ht * (0.11 if kind == 'wolf' else 0.08), hatch_op=0.6 if dark else 0.3)
    body = ell(cx, by, rx, ry, 22)
    p.shape(body, w=1.6, hatch=dict(angle=150, gap=3.4, op=0.35))
    p.hatch(ell(cx, by, rx, ry, 14, 0.1, math.pi - 0.1) + ell(cx, by + ry * 0.3, rx * 0.85, ry * 0.5, 14, math.pi - 0.1, 0.1),
            angle=60, gap=2.2, op=0.45)
    # fur strokes along back
    for i in range(10):
        t = math.pi * (1.1 + i * 0.08)
        bx, byy = cx + rx * math.cos(t), by + ry * math.sin(t)
        p.line([(bx, byy), (bx - 5, byy + 4)], w=0.8, passes=1, op=0.6)
    hx, hy = cx + rx * 0.95, by - ry * 0.5
    hr = Ht * (0.2 if kind == 'wolf' else 0.17)
    snout_len = hr * (1.7 if kind == 'wolf' else 1.4)
    head = [(hx - hr, hy - hr * 0.6), (hx, hy - hr), (hx + hr * 0.6, hy - hr * 0.5), (hx + snout_len, hy + hr * 0.1),
            (hx + snout_len, hy + hr * 0.45), (hx + hr * 0.4, hy + hr * 0.8), (hx - hr * 0.8, hy + hr * 0.7)]
    if kind == 'wolf':
        for e in (-0.35, 0.2):
            p.shape([(hx + hr * e - 5, hy - hr * 0.8), (hx + hr * e, hy - hr * 2.0), (hx + hr * e + 6, hy - hr * 0.8)], w=1.2,
                    hatch=dict(angle=45, gap=2.5, op=0.5))
    else:
        p.shape(ell(hx - hr * 0.1, hy - hr * 0.95, hr * 0.55, hr * 0.6, 12), w=1.2, hatch=dict(angle=45, gap=2.6, op=0.3))
    p.shape(head, w=1.6, hatch=dict(angle=130, gap=3.4, op=0.3))
    p.dot(hx + hr * 0.3, hy - hr * 0.25, hr * 0.13)
    p.dot(hx + snout_len - 1, hy + hr * 0.15, hr * 0.1)
    if kind == 'wolf':
        for i in range(3):
            fx = hx + hr * 0.8 + i * hr * 0.3
            p.shape([(fx, hy + hr * 0.4), (fx + 2, hy + hr * 0.75), (fx + 4, hy + hr * 0.4)], w=0.9)
    else:
        for s in (-1, 1):
            p.line([(hx + snout_len - 3, hy + hr * 0.3), (hx + snout_len + 12, hy + hr * 0.3 + s * 5)], w=0.6, passes=1)


def blob(p, cx, cy, rx, ry, drips=5, eyes=2, op=0.35):
    pts = []
    for i in range(18):
        t = i * 2 * math.pi / 18
        k = 1 + 0.12 * math.sin(t * 3 + random.uniform(0, 1))
        y = cy + ry * math.sin(t) * k
        if math.sin(t) > 0.6 and i % 3 == 0:
            y += ry * 0.25
        pts.append((cx + rx * math.cos(t) * k, y))
    p.shape(pts, w=1.6, hatch=dict(angle=120, gap=3.2, op=op))
    for _ in range(drips):
        x = cx + random.uniform(-rx * 0.7, rx * 0.7)
        p.line([(x, cy + ry * 0.7), (x + 1, cy + ry * 1.0 + random.uniform(4, 12))], w=1.6, passes=1)
    for i in range(eyes):
        ex = cx + (i - (eyes - 1) / 2) * rx * 0.4
        ey = cy - ry * 0.25 + random.uniform(-4, 4)
        p.shape(ell(ex, ey, 6, 6, 10), w=1.1)
        p.dot(ex + 1, ey + 1, 2.4)


def spider(p, cx, cy, s=1.0):
    for side in (-1, 1):
        for i in range(4):
            a = (-0.6 + i * 0.4)
            kx, ky = cx + side * s * (14 + i * 2), cy - s * (10 - i * 5)
            fx, fy = cx + side * s * (24 + i * 3), cy + s * (12 + a * 6)
            p.line([(cx + side * s * 4, cy + a * 4), (kx, ky), (fx, fy)], w=1.4 * s ** 0.5, passes=1)
    p.shape(ell(cx - s * 10, cy, s * 11, s * 9, 14), w=1.3, hatch=dict(angle=40, gap=2.4, op=0.6, cross=1))
    p.shape(ell(cx + s * 4, cy, s * 6, s * 5, 12), w=1.2, hatch=dict(angle=40, gap=2.4, op=0.5))
    for k in (-1, 1):
        p.dot(cx + s * 8, cy + k * s * 1.6, s * 1.1, color=PAPER, op=1)


def bat(p, cx, cy, s=1.0):
    for side in (-1, 1):
        pts = [(cx, cy - 2 * s), (cx + side * 12 * s, cy - 10 * s), (cx + side * 26 * s, cy - 6 * s), (cx + side * 22 * s, cy + 2 * s),
               (cx + side * 17 * s, cy - 1 * s), (cx + side * 12 * s, cy + 5 * s), (cx + side * 7 * s, cy + 1 * s), (cx, cy + 4 * s)]
        p.shape(pts, w=1.1, hatch=dict(angle=60, gap=2.4, op=0.55))
    p.shape(ell(cx, cy + s, 4 * s, 6 * s, 10), w=1.1, hatch=dict(angle=30, gap=2, op=0.7))
    for k in (-1, 1):
        p.line([(cx + k * 2 * s, cy - 4 * s), (cx + k * 3.5 * s, cy - 9 * s)], w=1.1, passes=1)


def snake(p, x, y, L, s=1.0, up=True):
    pts = []
    for i in range(9):
        t = i / 8
        pts.append((x + math.sin(t * 6) * 10 * s, y - t * L if up else y + t * L))
    p.line(pts, w=6 * s, passes=1, op=0.35)
    p.line(pts, w=1.3)
    hx, hy = pts[-1]
    p.shape(ell(hx, hy, 6 * s, 4 * s, 10), w=1.2, hatch=dict(angle=20, gap=2, op=0.5))
    p.line([(hx + 5 * s, hy), (hx + 10 * s, hy - 1), (hx + 12 * s, hy - 3)], w=0.8, passes=1)
    p.line([(hx + 10 * s, hy - 1), (hx + 12 * s, hy + 2)], w=0.8, passes=1)


def pit(p, cx=160, cy=150, rx=110, ry=30, depth=55):
    rim = ell(cx, cy, rx, ry, 26)
    p.fill(rim, color=PAPER)
    inner = [(cx - rx, cy)] + ell(cx, cy, rx, ry, 13, math.pi, 2 * math.pi) + [(cx + rx, cy), (cx + rx * 0.85, cy + depth * 0.2)] + \
            ell(cx, cy + depth * 0.2, rx * 0.85, ry * 0.8, 13, 0, math.pi)[::-1][::-1][::-1]
    p.hatch(rim, angle=75, gap=2.6, op=0.65, cross=2)
    p.smudge(cx, cy + 4, rx * 0.7, ry * 0.6, op=0.35, back=False)
    p.line(rim, w=1.8, closed=True)
    # stone lip
    for i in range(12):
        t = i * 2 * math.pi / 12
        a = (cx + rx * math.cos(t), cy + ry * math.sin(t))
        b = (cx + (rx + 10) * math.cos(t), cy + (ry + 6) * math.sin(t))
        p.line([a, b], w=0.9, passes=1, op=0.6)
    p.line(ell(cx, cy, rx + 10, ry + 6, 26), w=1.1, closed=True, op=0.6)
    return rim


# ---------------- encounter pictures ----------------
ART = {}


def art(name):
    def deco(fn):
        ART[name] = fn
        return fn
    return deco


@art('Goblin Scout')
def _(p):
    bricks(p); floor(p)
    humanoid(p, 150, 172, 105, build='thin', head='ears', weapon='dagger', hunch=0.4)
    torch(p, 270, 70)


@art('Giant Rat')
def _(p):
    bricks(p); floor(p)
    beast(p, 165, 172, 130, 80, kind='rat')
    for x in (40, 70):
        p.shape([(x, 172), (x + 6, 150), (x + 14, 158), (x + 18, 172)], w=1.0, hatch=dict(angle=45, gap=3, op=0.3))


@art('Rattling Skeleton')
def _(p):
    bricks(p); floor(p)
    humanoid(p, 160, 172, 130, head='plain', skeleton=True, weapon='sword')
    for x in (60, 250):
        p.shape(ell(x, 170, 8, 4, 10), w=1)


@art('Ooze')
def _(p):
    bricks(p); floor(p)
    p.smudge(160, 172, 110, 10, op=0.3)
    blob(p, 160, 128, 95, 45, drips=7, eyes=3)
    for b in range(6):
        p.line(ell(120 + b * 15, 115 + (b % 3) * 12, 4, 4, 8), w=0.8, closed=True, passes=1)
    rock(p, 52, 166, 10)


@art('Road Bandit')
def _(p):
    floor(p, cracks=False)
    for x in (30, 280):
        p.line([(x, 172), (x + 4, 40), (x - 30, 60), (x + 4, 40), (x + 40, 50)], w=1.2, back=True, op=0.5)
    humanoid(p, 160, 172, 125, head='hood', weapon='sword', cloak=True)


@art('Hooded Cultist')
def _(p):
    bricks(p); floor(p)
    for x in (70, 250):
        p.shape([(x - 5, 172), (x - 5, 140), (x + 5, 140), (x + 5, 172)], w=1, hatch=dict(angle=90, gap=2.5, op=0.3))
        p.glow(x, 132, 16); p.shape([(x, 124), (x + 3, 134), (x - 3, 134)], w=0.9)
    humanoid(p, 160, 172, 125, head='hood', weapon='skullstaff', robe=True)
    p.line(ell(160, 176, 70, 10, 26), w=0.9, closed=True, op=0.5)


@art('Kobold Trapper')
def _(p):
    bricks(p); floor(p)
    humanoid(p, 130, 172, 85, build='thin', head='snout', weapon='rope', tail=True)


@art('Orc Brute')
def _(p):
    bricks(p); floor(p)
    humanoid(p, 155, 174, 150, build='bulky', head='plain', weapon='axe', armor=True, face_kind='angry')


@art('Will-o-Wisp')
def _(p):
    bricks(p, op=0.15); floor(p)
    for (x, y, r) in [(160, 90, 50), (90, 120, 18), (240, 110, 14)]:
        p.glow(x, y, r * 1.4)
        fl = [(x, y - r), (x + r * 0.5, y - r * 0.2), (x + r * 0.45, y + r * 0.4), (x, y + r * 0.6), (x - r * 0.45, y + r * 0.4), (x - r * 0.5, y - r * 0.2)]
        p.line(fl, w=1.2, closed=True)
        for k in range(3):
            p.line([(x + random.uniform(-r, r) * 0.5, y + r * 0.6), (x + random.uniform(-r, r), y + r * 1.4)], w=0.7, passes=1, op=0.5)
    p.dot(150, 85, 4); p.dot(170, 85, 4)


@art('Shambler')
def _(p):
    bricks(p); floor(p)
    humanoid(p, 150, 172, 120, head='plain', hunch=0.6, face_kind='grim', shade=0.45)
    for i in range(5):
        x = 120 + i * 14
        p.line([(x, 120), (x + 3, 140)], w=0.8, passes=1, op=0.5)


@art('Dire Wolf')
def _(p):
    floor(p, cracks=False)
    p.glow(260, 40, 26); p.line(ell(260, 40, 16, 16, 16), w=1.0, closed=True)
    for x in (20, 60, 300):
        p.line([(x, 172), (x, 90), (x - 14, 110)], w=1.0, back=True, op=0.45)
    beast(p, 150, 172, 150, 110, kind='wolf')


@art('Spider Swarm')
def _(p):
    bricks(p, op=0.15); floor(p)
    for k in range(8):
        a = k * math.pi / 8
        p.line([(0, 0), (160 * math.cos(a) * 0.9, 160 * math.sin(a) * 0.9)], w=0.5, back=True, op=0.5, passes=1)
    for rr in (30, 60, 95, 130):
        p.line([(rr * math.cos(k * math.pi / 8) * 0.9, rr * math.sin(k * math.pi / 8) * 0.9) for k in range(9)], w=0.5, back=True, op=0.5, passes=1)
    for (x, y, s) in [(160, 130, 2.0), (90, 150, 1.0), (230, 155, 1.2), (250, 100, 0.8), (120, 95, 0.7), (60, 120, 0.6)]:
        spider(p, x, y, s)


@art('Gargoyle')
def _(p):
    bricks(p); floor(p)
    ped = [(110, 172), (110, 150), (210, 150), (210, 172)]
    p.shape(ped, w=1.4, hatch=dict(angle=10, gap=4, op=0.3), sharp=True)
    humanoid(p, 160, 150, 100, build='bulky', head='horns', wing=True, hunch=0.3, shade=0.5)


@art('Cackling Imp')
def _(p):
    bricks(p); floor(p)
    humanoid(p, 160, 160, 80, build='thin', head='horns', wing=True, tail=True, weapon='spear')
    p.smudge(160, 172, 30, 5, op=0.3)


@art('Treasure Mimic')
def _(p):
    bricks(p); floor(p)
    p.smudge(160, 172, 90, 9, op=0.3)
    base = [(90, 172), (90, 120), (230, 120), (230, 172)]
    p.shape(base, w=1.8, hatch=dict(angle=0, gap=5, op=0.35), sharp=True)
    lid = [(90, 120), (80, 70), (110, 50), (215, 48), (240, 66), (230, 120)]
    p.fill(ell(160, 120, 70, 22, 20), color=INK, op=0.85)
    p.shape(lid, w=1.8, hatch=dict(angle=0, gap=5, op=0.35), sharp=True)
    for i in range(9):
        x = 98 + i * 15
        p.shape([(x, 120), (x + 7, 106), (x + 14, 120)], w=1.0)
        p.shape([(x + 3, 70 + 52), (x + 8, 132), (x + 13, 70 + 52)], w=0.9)
    tongue = [(150, 122), (185, 140), (205, 165), (195, 172), (175, 150), (148, 130)]
    p.shape(tongue, w=1.2, hatch=dict(angle=60, gap=2.6, op=0.4))
    for y in (130, 150):
        p.line([(90, y), (230, y)], w=1.0, passes=1)
    p.dot(160, 135, 3)


@art('Marsh Lurker')
def _(p):
    floor(p, y=176, cracks=False)
    for i in range(10):
        x = 10 + i * 32 + random.uniform(-6, 6)
        p.line([(x, 178), (x + random.uniform(-6, 6), 120 + random.uniform(-10, 10))], w=0.9, back=True, op=0.5)
    for k in range(5):
        p.line([(20 + k * 60, 184), (60 + k * 60, 183)], w=0.7, back=True, op=0.5, passes=1)
    humanoid(p, 160, 176, 120, head='snout', weapon='spear', tail=True, shade=0.45)


@art('Bog Witch')
def _(p):
    floor(p, cracks=False)
    humanoid(p, 120, 172, 120, head='witch', weapon='staff', robe=True, hunch=0.2, face_kind='grim')
    pot = ell(235, 150, 38, 26, 20)
    p.shape(pot, w=1.6, hatch=dict(angle=30, gap=2.6, op=0.6, cross=1))
    p.line(ell(235, 128, 38, 7, 20), w=1.4, closed=True)
    for k in range(4):
        p.line([(220 + k * 10, 120), (215 + k * 12, 95), (225 + k * 10, 70)], w=0.9, passes=1, op=0.55)
    for x in (205, 265):
        p.line([(x, 172), (x + (8 if x > 230 else -8), 155)], w=2)


@art('Crypt Ghoul')
def _(p):
    bricks(p); floor(p)
    tomb = [(30, 172), (30, 120), (40, 105), (75, 105), (85, 120), (85, 172)]
    p.shape(tomb, w=1.4, hatch=dict(angle=80, gap=4, op=0.25))
    p.line([(57, 120), (57, 150)], w=1.3); p.line([(47, 130), (67, 130)], w=1.3)
    humanoid(p, 175, 172, 115, build='thin', head='plain', hunch=0.8, face_kind='angry', shade=0.5)


@art('Hobgoblin Captain')
def _(p):
    bricks(p); floor(p)
    p.line([(250, 172), (252, 30)], w=2.2)
    p.shape([(252, 32), (300, 42), (292, 58), (300, 74), (252, 70)], w=1.3, hatch=dict(angle=80, gap=3, op=0.35))
    humanoid(p, 150, 172, 135, head='ears', weapon='sword', armor=True, cloak=True)


@art('Cave Bats')
def _(p):
    for k in range(9):
        x = k * 40 - 10
        p.shape([(x, 0), (x + 20, 0), (x + 12, random.uniform(25, 50))], w=1.1, hatch=dict(angle=80, gap=3, op=0.4), back=True)
    floor(p)
    for (x, y, s) in [(160, 100, 2.4), (80, 70, 1.2), (240, 80, 1.4), (110, 140, 1.0), (220, 140, 0.9), (290, 120, 0.8), (40, 115, 0.8)]:
        bat(p, x, y, s)


@art('Stone Golem')
def _(p):
    bricks(p); floor(p)
    p.smudge(160, 174, 80, 8, op=0.3)
    blocks = [(132, 70, 188, 128), (120, 128, 150, 172), (170, 128, 200, 172), (90, 76, 128, 130), (192, 76, 230, 130), (140, 30, 180, 70)]
    for (x0, y0, x1, y1) in blocks:
        pts = [(x0, y0), (x1, y0 + random.uniform(-3, 3)), (x1 + random.uniform(-3, 3), y1), (x0, y1)]
        p.shape(pts, w=1.8, hatch=dict(angle=random.choice([30, 60, 120]), gap=3.2, op=0.4), sharp=True)
        p.line([(x0 + 6, y0 + 8), ((x0 + x1) / 2, (y0 + y1) / 2), (x1 - 8, y1 - 6)], w=0.8, passes=1, op=0.6)
    for x in (152, 168):
        p.el.append(f'<ellipse cx="{x}" cy="48" rx="4" ry="2.5" fill="#fffaf0"/>')
        p.glow(x, 48, 8)


@art('Wailing Banshee')
def _(p):
    bricks(p, op=0.15); floor(p)
    body = [(160, 40), (190, 55), (200, 100), (215, 140), (230, 172), (205, 160), (190, 175), (172, 158), (155, 178), (140, 160), (118, 172), (122, 140), (130, 95), (135, 55)]
    p.shape(body, w=1.3, hatch=dict(angle=100, gap=4.5, op=0.22))
    for k in range(7):
        x = 140 + k * 6
        p.line([(x, 40), (x - 18 - k * 3, 75), (x - 26 - k * 2, 120)], w=0.8, passes=1, op=0.6)
    p.shape(ell(162, 58, 16, 19, 16), w=1.4)
    for s in (-1, 1):
        p.fill(ell(162 + s * 6, 54, 3.4, 4.5, 10), color=INK)
    p.fill(ell(162, 68, 4.5, 7, 12), color=INK)
    for k in range(4):
        p.line([(190 + k * 8, 60), (215 + k * 12, 48 - k * 4)], w=0.8, passes=1, op=0.45)


@art('Harpy')
def _(p):
    floor(p, cracks=False)
    for x in (40, 270):
        rock(p, x, 160, 26)
    humanoid(p, 160, 165, 110, build='thin', head='plain', wing=True, legs='bird', face_kind='angry')


@art('Necromancer')
def _(p):
    bricks(p); floor(p)
    for x in (70, 95, 230, 255):
        sk = ell(x, 166, 7, 6, 10); p.shape(sk, w=1)
        p.fill(ell(x - 2, 165, 1.6, 1.8, 8), color=INK); p.fill(ell(x + 2, 165, 1.6, 1.8, 8), color=INK)
    p.line(ell(160, 176, 90, 10, 26), w=1.0, closed=True, op=0.6)
    humanoid(p, 160, 172, 130, head='hood', weapon='skullstaff', robe=True, cloak=True)


@art('Bridge Troll')
def _(p):
    floor(p, y=178, cracks=False)
    br = [(0, 40), (320, 40), (320, 58), (0, 58)]
    p.shape(br, w=1.6, hatch=dict(angle=0, gap=5, op=0.3), back=True, sharp=True)
    p.line([(0, 58)] + ell(160, 58, 120, 50, 16, 0, math.pi)[::-1][::-1] + [(320, 58)], w=1.4, back=True, op=0.6)
    humanoid(p, 160, 178, 135, build='bulky', head='plain', weapon='club', face_kind='angry', shade=0.45)
    for k in range(6):
        p.line([(20 + k * 55, 186), (55 + k * 55, 185)], w=0.7, passes=1, op=0.5)


@art('Living Shadow')
def _(p):
    bricks(p); floor(p)
    torch(p, 60, 70)
    body = [(170, 30), (195, 45), (205, 85), (225, 120), (215, 172), (190, 160), (175, 175), (160, 160), (140, 172), (130, 120), (148, 85), (150, 45)]
    p.fill(body, color=INK, op=0.55)
    p.hatch(body, angle=60, gap=2, op=0.7, cross=2)
    p.line(body, w=1.0, closed=True, op=0.5)
    p.el.append('<ellipse cx="166" cy="56" rx="5" ry="2.6" fill="#fffaf0"/><ellipse cx="182" cy="56" rx="5" ry="2.6" fill="#fffaf0"/>')


@art('Ogre')
def _(p):
    bricks(p); floor(p)
    humanoid(p, 165, 174, 160, build='bulky', head='plain', weapon='club', face_kind='angry', hunch=0.15)
    for i in range(3):
        rock(p, 50 + i * 18, 168, 7)


@art('Fire Beetle')
def _(p):
    bricks(p); floor(p)
    cx, cy = 160, 135
    p.smudge(cx, 172, 90, 9, op=0.3)
    for side in (-1, 1):
        for i in range(3):
            x0 = cx - 30 + i * 30
            p.line([(x0, cy + side * 4), (x0 + side * 4, cy + 26 + (8 if side > 0 else 0)), (x0 + side * 10 - 6, 172)], w=1.8)
    shell = ell(cx, cy, 70, 34, 24)
    p.shape(shell, w=1.8, hatch=dict(angle=20, gap=3, op=0.45))
    p.line([(cx - 64, cy), (cx + 60, cy - 2)], w=1.3)
    for k in range(4):
        p.line(ell(cx - 20 + k * 20, cy - 14, 6, 3, 8), closed=True, w=0.8, passes=1)
    head = ell(cx + 78, cy + 4, 18, 15, 14)
    p.shape(head, w=1.6, hatch=dict(angle=60, gap=2.4, op=0.6, cross=1))
    p.line([(cx + 92, cy), (cx + 110, cy - 14), (cx + 108, cy - 24)], w=1.4)
    p.line([(cx + 92, cy + 8), (cx + 112, cy + 10), (cx + 118, cy)], w=1.4)
    for k in range(5):
        x = cx - 40 + k * 20
        fl = [(x, cy - 34), (x + 6, cy - 50), (x + 3, cy - 62 - k * 3), (x + 12, cy - 48), (x + 10, cy - 34)]
        p.glow(x + 6, cy - 46, 14)
        p.line(fl, w=1.0, closed=True, passes=1)


@art('Wraith Knight')
def _(p):
    bricks(p); floor(p)
    p.smudge(160, 120, 60, 70, op=0.12, back=True)
    humanoid(p, 160, 172, 140, head='helm', weapon='sword', armor=True, cloak=True, shade=0.5)
    for k in range(6):
        p.line([(110 + k * 18, 170), (100 + k * 20, 186)], w=0.8, passes=1, op=0.5)


@art('Fungal Creeper')
def _(p):
    bricks(p, op=0.15); floor(p)
    for (x, hgt, w) in [(160, 110, 60), (95, 70, 38), (230, 80, 44), (60, 40, 22), (275, 45, 24), (195, 50, 26)]:
        stem = [(x - w * 0.15, 172), (x - w * 0.12, 172 - hgt), (x + w * 0.12, 172 - hgt), (x + w * 0.18, 172)]
        p.shape(stem, w=1.3, hatch=dict(angle=90, gap=4, op=0.2))
        cap = ell(x, 172 - hgt, w * 0.55, w * 0.32, 18, math.pi, 2 * math.pi) + [(x + w * 0.55, 172 - hgt + 4), (x - w * 0.55, 172 - hgt + 4)]
        p.shape(cap, w=1.5, hatch=dict(angle=30, gap=3, op=0.4))
        for k in range(4):
            p.shape(ell(x - w * 0.3 + k * w * 0.2, 172 - hgt - w * 0.12 - (k % 2) * 4, 3, 2.5, 8), w=0.8)
        for k in range(6):
            gx = x - w * 0.45 + k * w * 0.18
            p.line([(gx, 172 - hgt + 4), (gx, 172 - hgt + 9)], w=0.6, passes=1, op=0.6)
    for k in range(5):
        x0 = 40 + k * 60
        p.line([(x0, 172), (x0 + 15, 182), (x0 + 30, 176), (x0 + 45, 188)], w=1.2, passes=1, op=0.6)
    p.dot(150, 100, 3); p.dot(170, 100, 3)


# perils
@art('Collapsing Floor')
def _(p):
    bricks(p, bottom=110)
    p.fill([(0, 110), (320, 110), (320, 200), (0, 200)], color=INK, op=0.55)
    p.hatch([(0, 110), (320, 110), (320, 200), (0, 200)], angle=70, gap=2.2, op=0.7, cross=2)
    slabs = [[(0, 120), (70, 116), (90, 135), (60, 160), (0, 165)], [(240, 118), (320, 115), (320, 165), (255, 160), (230, 138)],
             [(110, 140), (150, 130), (170, 150), (130, 168)], [(185, 165), (215, 150), (225, 172), (195, 185)]]
    for i, s in enumerate(slabs):
        p.shape(s, w=1.6, hatch=dict(angle=15, gap=4, op=0.3), sharp=True)
        if i >= 2:
            for k in range(3):
                p.line([(s[0][0] + k * 10, s[0][1] - 6), (s[0][0] + k * 10 - 2, s[0][1] - 18)], w=0.8, passes=1, op=0.5)
    for (x, y, r) in [(100, 100, 5), (205, 95, 4), (160, 112, 3), (130, 185, 6)]:
        rock(p, x, y, r, shade=False)


@art('Poison Gas')
def _(p):
    bricks(p); floor(p)
    for (x, y, r) in [(110, 120, 40), (175, 100, 50), (240, 125, 36), (150, 145, 30), (70, 150, 24)]:
        for k in range(3):
            pts = ell(x, y, r - k * 9, (r - k * 9) * 0.7, 18, 0, 1.7 * math.pi)
            p.line(pts, w=1.0, passes=1, op=0.6)
        p.hatch(ell(x, y, r, r * 0.7, 16), angle=random.choice([20, 160]), gap=5, op=0.2)
    sk = ell(175, 100, 16, 17, 14)
    p.line(sk, w=1.1, closed=True)
    for s in (-1, 1):
        p.fill(ell(175 + s * 6, 98, 3.5, 4, 10), color=INK, op=0.8)
    p.line([(165, 110), (185, 110)], w=1, passes=1)
    p.shape([(40, 172), (44, 158), (52, 156), (56, 172)], w=1)


@art('Spike Trap')
def _(p):
    bricks(p, bottom=95)
    floor(p, y=95, cracks=False)
    p.fill([(0, 95), (320, 95), (320, 200), (0, 200)], color=PAPER)
    p.hatch([(0, 95), (320, 95), (320, 200), (0, 200)], angle=8, gap=7, op=0.25)
    rim = pit(p, 160, 145, 118, 36)
    for i in range(11):
        x = 70 + i * 17 + random.uniform(-4, 4)
        base = 150 + random.uniform(-4, 10)
        hgt = random.uniform(28, 46)
        sp = [(x - 5, base), (x, base - hgt), (x + 5, base)]
        p.shape(sp, w=1.3, hatch=dict(angle=80, gap=2.2, op=0.35))
    skull = ell(205, 160, 9, 8, 12)
    p.shape(skull, w=1.1)
    p.fill(ell(202, 159, 2, 2.2, 8), color=INK); p.fill(ell(208, 159, 2, 2.2, 8), color=INK)
    p.line([(110, 165), (135, 158)], w=1.8)
    p.line([(140, 168), (165, 171)], w=1.8)
    torch(p, 290, 40)


@art('Locked Vault')
def _(p):
    bricks(p); floor(p)
    door = ell(160, 100, 72, 72, 30)
    p.shape(door, w=2.0, hatch=dict(angle=45, gap=3.4, op=0.3))
    p.line(ell(160, 100, 58, 58, 30), w=1.3, closed=True)
    for k in range(12):
        t = k * math.pi / 6
        p.shape(ell(160 + 65 * math.cos(t), 100 + 65 * math.sin(t), 3.5, 3.5, 8), w=0.9)
    for k in range(6):
        t = k * math.pi / 3
        p.line([(160, 100), (160 + 34 * math.cos(t), 100 + 34 * math.sin(t))], w=2.4)
    p.shape(ell(160, 100, 10, 10, 12), w=1.4, hatch=dict(angle=45, gap=2, op=0.6))
    lock = [(140, 130), (180, 130), (182, 166), (138, 166)]
    p.line(ell(160, 130, 13, 15, 14, math.pi, 2 * math.pi), w=3.0)
    p.shape(lock, w=1.6, hatch=dict(angle=20, gap=2.6, op=0.5), sharp=True)
    p.fill(ell(160, 146, 3, 4, 8), color=INK)
    p.fill([(158, 148), (162, 148), (161, 158), (159, 158)], color=INK)


@art('Rune Door')
def _(p):
    bricks(p); floor(p)
    arch_frame(p, 160, 20, 70, 172)
    door = [(95, 172), (95, 75)] + ell(160, 75, 65, 50, 14, math.pi, 2 * math.pi) + [(225, 75), (225, 172)]
    p.shape(door, w=1.6, hatch=dict(angle=90, gap=5, op=0.25))
    for x in (125, 160, 195):
        p.line([(x, 172), (x, 45 if x == 160 else 60)], w=0.9, passes=1, op=0.6)
    runes = ['M0,0 l6,-12 l6,12 M2,-4 h8', 'M0,0 v-12 l8,6 l-8,6', 'M0,-12 l10,12 M10,-12 l-10,12', 'M0,0 v-12 h8 v6 h-8', 'M5,0 v-12 M0,-6 l5,-6 l5,6']
    for i, (x, y) in enumerate([(118, 100), (150, 82), (182, 100), (130, 130), (175, 130), (152, 112)]):
        p.glow(x + 5, y - 6, 12)
        p.el.append(f'<path d="{runes[i % len(runes)]}" transform="translate({x},{y})" fill="none" stroke="{INK}" stroke-width="1.6" stroke-linecap="round"/>')
    p.shape(ell(210, 125, 5, 5, 8), w=1.2)


@art('Rushing River')
def _(p):
    for x, y in [(10, 50), (310, 50)]:
        p.shape([(x - 30, 0), (x + 25, 0), (x + 30, 70), (x + 10, 200), (x - 30, 200)], w=1.4, hatch=dict(angle=70, gap=3, op=0.4), back=True)
    for row in range(9):
        y = 70 + row * 15
        pts = [(30 + k * 26, y + 4 * math.sin(k + row)) for k in range(11)]
        p.line(pts, w=0.9, passes=1, op=0.6)
        for k in range(3):
            x = random.uniform(50, 270)
            p.line([(x, y - 3), (x + 6, y - 6), (x + 12, y - 3)], w=0.7, passes=1, op=0.6)
    for (x, y, r) in [(110, 120, 14), (200, 150, 17), (150, 95, 10)]:
        rock(p, x, y, r)
        p.line([(x - r - 6, y + 4), (x - r, y + 2)], w=0.8, passes=1)
    p.line([(40, 60), (110, 72), (180, 70), (280, 58)], w=1.6)
    for k in range(10):
        x = 50 + k * 23
        p.line([(x, 63 + 6 * math.sin(k / 3)), (x + 4, 67 + 6 * math.sin(k / 3))], w=0.8, passes=1)


@art('Cursed Altar')
def _(p):
    bricks(p); floor(p)
    top = [(80, 120), (240, 120), (232, 132), (88, 132)]
    p.shape([(95, 132), (225, 132), (215, 172), (105, 172)], w=1.6, hatch=dict(angle=80, gap=4, op=0.3), sharp=True)
    p.shape(top, w=1.6, hatch=dict(angle=10, gap=3, op=0.3), sharp=True)
    for x in (100, 220):
        p.shape([(x - 5, 120), (x - 5, 95), (x + 5, 95), (x + 5, 120)], w=1.1)
        p.glow(x, 88, 16)
        p.shape([(x, 80), (x + 3, 92), (x - 3, 92)], w=0.9)
    sk = ell(160, 106, 15, 14, 14)
    p.shape(sk, w=1.3)
    for s in (-1, 1):
        p.fill(ell(160 + s * 5.5, 104, 3.4, 3.8, 10), color=INK)
    for k in range(4):
        p.line([(160 + k * 3 - 4, 118), (160 + k * 3 - 4, 121)], w=0.8, passes=1)
    for k in range(6):
        x = 120 + k * 16
        p.line([(x, 118), (x - 8, 90), (x + 6, 60), (x - 4, 30)], w=1.0, passes=1, op=0.55)
    p.line([(135, 160), (160, 145), (185, 160), (160, 168), (135, 160)], w=0.9, passes=1)


@art('Swinging Blades')
def _(p):
    bricks(p); floor(p)
    p.shape([(-5, 10), (325, 10), (325, 22), (-5, 22)], w=1.6, hatch=dict(angle=0, gap=3, op=0.4), sharp=True)
    for x, ang in [(80, -0.42), (165, 0.32), (250, -0.2)]:
        L = 92
        u = (math.sin(ang), math.cos(ang))
        n = (math.cos(ang), -math.sin(ang))
        bx, by = x + L * u[0], 22 + L * u[1]
        p.line([(x, 22), (bx, by)], w=2.2)
        P = lambda a, b: (bx + n[0] * a + u[0] * b, by + n[1] * a + u[1] * b)
        blade = [P(-36, -6), P(-24, 14), P(0, 26), P(24, 14), P(36, -6), P(14, 4), P(0, 8), P(-14, 4)]
        p.shape(blade, w=1.6, hatch=dict(angle=20, gap=2.8, op=0.35))
        p.hatch([P(-36, -6), P(-24, 14), P(0, 26), P(0, 8), P(-14, 4)], angle=60, gap=2, op=0.4)
        p.shape(ell(x, 22, 4, 4, 8), w=1.2)
        side = 1 if ang < 0 else -1
        for k in range(3):
            o = side * (0.12 + k * 0.1)
            p.line([(x + (L + 30) * math.sin(ang + o), 22 + (L + 30) * math.cos(ang + o)),
                    (x + (L + 30) * math.sin(ang + o + side * 0.08), 22 + (L + 30) * math.cos(ang + o + side * 0.08))], w=0.9, passes=1, op=0.5)


@art('Snake Pit')
def _(p):
    bricks(p, bottom=90)
    floor(p, y=90, cracks=False)
    p.fill([(0, 90), (320, 90), (320, 200), (0, 200)], color=PAPER)
    p.hatch([(0, 90), (320, 90), (320, 200), (0, 200)], angle=8, gap=7, op=0.25)
    pit(p, 160, 145, 120, 38)
    for (x, y, L, s) in [(110, 165, 55, 1.0), (165, 168, 75, 1.3), (215, 162, 50, 0.9), (140, 160, 35, 0.7), (240, 158, 30, 0.7)]:
        snake(p, x, y, L, s)


@art('Magical Darkness')
def _(p):
    p.fill([(0, 0), (320, 0), (320, 200), (0, 200)], color=INK, op=0.35)
    p.hatch([(0, 0), (320, 0), (320, 200), (0, 200)], angle=45, gap=2.0, op=0.75, cross=2)
    p.el.append(f'<circle cx="160" cy="110" r="58" fill="{PAPER}" opacity=".9" filter="url(#blur)"/>')
    p.glow(160, 100, 40)
    humanoid(p, 160, 165, 80, head='plain', face_kind='grim')
    torch(p, 186, 92)
    for (x, y) in [(40, 50), (280, 70), (60, 150), (260, 160), (300, 30)]:
        p.el.append(f'<ellipse cx="{x}" cy="{y}" rx="4" ry="2" fill="#fffaf0"/><ellipse cx="{x + 11}" cy="{y}" rx="4" ry="2" fill="#fffaf0"/>')


@art('Rockslide')
def _(p):
    slope = [(0, 30), (320, 172), (320, 200), (0, 200)]
    p.shape(slope, w=1.4, hatch=dict(angle=20, gap=5, op=0.25), back=True)
    for (x, y, r) in [(70, 60, 22), (150, 92, 30), (230, 128, 26), (110, 50, 12), (200, 90, 14), (270, 150, 12), (40, 40, 10)]:
        rock(p, x, y - r * 0.6, r)
        for k in range(2):
            p.line([(x - r - 6 - k * 6, y - r - k * 4), (x - r - 14 - k * 8, y - r - 6 - k * 4)], w=0.8, passes=1, op=0.5)
    for k in range(14):
        x = random.uniform(20, 300)
        p.dot(x, 30 + x * 0.44 + random.uniform(-10, 4), random.uniform(1, 2.5))


@art('Mirror Maze')
def _(p):
    floor(p)
    for i, (x, w_, hgt) in enumerate([(30, 60, 120), (110, 100, 150), (230, 60, 120)]):
        y0 = 172 - hgt
        frame = [(x, 172), (x, y0 + 20), (x + w_ / 2, y0), (x + w_, y0 + 20), (x + w_, 172)]
        p.shape(frame, w=2.2, hatch=dict(angle=100, gap=6, op=0.15))
        inner = [(x + 8, 166), (x + 8, y0 + 24), (x + w_ / 2, y0 + 8), (x + w_ - 8, y0 + 24), (x + w_ - 8, 166)]
        p.line(inner, w=1.0, closed=True)
        for k in range(3):
            p.line([(x + 14 + k * 8, y0 + 40 + k * 6), (x + 24 + k * 8, y0 + 28 + k * 6)], w=0.7, passes=1, op=0.55)
        sc = 0.55 if i != 1 else 0.8
        humanoid(p, x + w_ / 2, 166, hgt * sc, head='plain', face_kind='grim', shade=0.2 + i * 0.1)


# bosses
@art('Goblin King')
def _(p):
    bricks(p); floor(p)
    throne = [(95, 172), (95, 40), (120, 20), (160, 34), (200, 20), (225, 40), (225, 172)]
    p.shape(throne, w=1.8, hatch=dict(angle=80, gap=3.4, op=0.3, cross=1), sharp=True)
    seat = [(105, 172), (105, 120), (215, 120), (215, 172)]
    p.shape(seat, w=1.4, hatch=dict(angle=10, gap=4, op=0.25), sharp=True)
    humanoid(p, 160, 172, 125, head='crown', weapon='sword', cloak=True, face_kind='angry')
    for (x, y) in [(40, 165), (60, 168), (270, 164), (285, 168)]:
        p.shape(ell(x, y, 8, 5, 10), w=1, hatch=dict(angle=0, gap=2, op=0.3))


@art('Bone Tyrant')
def _(p):
    bricks(p); floor(p)
    for x in (40, 280):
        p.shape([(x - 12, 172), (x - 12, 30), (x + 12, 30), (x + 12, 172)], w=1.4, hatch=dict(angle=90, gap=4, op=0.25), sharp=True)
    humanoid(p, 160, 174, 160, build='bulky', head='crown', skeleton=True, weapon='sword', cloak=True)
    for (x, y) in [(90, 168), (230, 170), (210, 165)]:
        p.shape(ell(x, y, 9, 8, 12), w=1)
        p.fill(ell(x - 3, y - 1, 2, 2.4, 8), color=INK); p.fill(ell(x + 3, y - 1, 2, 2.4, 8), color=INK)


@art('Magma Wyrm')
def _(p):
    for k in range(6):
        x = k * 60 - 10
        p.shape([(x, 200), (x + 10, 150 + random.uniform(-10, 10)), (x + 30, 145), (x + 50, 160), (x + 60, 200)], w=1.2,
                hatch=dict(angle=60, gap=3, op=0.35), back=True)
    for (x, y) in [(60, 185), (150, 190), (250, 186)]:
        p.glow(x, y, 26)
        p.line(ell(x, y, 12, 4, 12), w=0.9, closed=True)
    body = [(30, 200), (60, 150), (100, 120), (150, 112), (190, 90), (215, 60), (230, 45)]
    p.line(body, w=24, passes=1, op=0.28)
    p.line([(x, y - 12) for x, y in body], w=1.6)
    p.line([(x, y + 12) for x, y in body], w=1.6)
    for i in range(1, len(body) - 1):
        x, y = body[i]
        p.line([(x - 6, y - 12), (x - 12, y - 24), (x + 4, y - 12)], w=1.2)
        p.line([(x - 8, y + 10), (x, y + 12)], w=0.8, passes=1)
    head = [(215, 30), (250, 22), (288, 34), (300, 46), (280, 54), (255, 62), (225, 60)]
    p.shape(head, w=1.8, hatch=dict(angle=30, gap=2.6, op=0.45, cross=1))
    for s in (0, 1):
        p.shape([(230 + s * 12, 30), (226 + s * 14, 6), (242 + s * 12, 26)], w=1.2, hatch=dict(angle=10, gap=2, op=0.5))
    p.el.append('<ellipse cx="262" cy="36" rx="5" ry="2.6" fill="#fffaf0"/>')
    for k in range(5):
        p.shape([(280 + k * 3, 50), (282 + k * 3, 57), (284 + k * 3, 50)], w=0.8)
    for k in range(4):
        fy = 60 + k * 9
        p.line([(298, 50), (310, fy), (318, fy + 6)], w=1.0, passes=1, op=0.7)
    p.glow(305, 70, 26)
    wing = [(140, 105), (110, 40), (80, 20), (96, 60), (70, 50), (90, 85), (60, 85), (100, 110)]
    p.shape(wing, w=1.4, hatch=dict(angle=70, gap=3, op=0.35))


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in ART.items():
        p = Pic(name)
        fn(p)
        with open(os.path.join(OUT, slug(name) + '.svg'), 'w') as fh:
            fh.write(p.svg())
    print(f'wrote {len(ART)} pictures to {os.path.normpath(OUT)}')


if __name__ == '__main__':
    main()
