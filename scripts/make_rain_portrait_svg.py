"""
"Rain reveal" poster: the portrait is drawn as thousands of short vertical
light streaks on black (brighter where the photo is lit), each column falling
into place from the top with a bright drop riding the edge, then holding.
Below it, a metallic title with a slow shimmer. Faint background rain keeps
drifting forever so the card never feels frozen.

Pure SVG (SMIL), no scripts or external assets, so GitHub animates it when
embedded with <img>.

Inputs (both written by prep_photo.py):
    source-prepped.png   grayscale subject on white
    source-mask.png      subject alpha, same crop

    python scripts/make_rain_portrait_svg.py [prepped.png] [mask.png] [out.svg]

Env overrides: TITLE_SMALL, TITLE_BIG, COLS, ROWS, STATIC=1 (frozen frame).
"""
import html
import os
import random
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "source-prepped.png")
MASK = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "source-mask.png")
OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, "rain-portrait.svg")

TITLE_SMALL = os.environ.get("TITLE_SMALL", "SENIOR QA AUTOMATION ENGINEER")
TITLE_BIG = os.environ.get("TITLE_BIG", "PRASANNA VENKATESH")
STATIC = bool(os.environ.get("STATIC"))

# ---- canvas ----------------------------------------------------------------
W, H = 900, 720
PORTRAIT = 460                       # square portrait area, px
PX, PY = (W - PORTRAIT) / 2, 24      # top-left of portrait area
COLS = int(os.environ.get("COLS", 112))
ROWS = int(os.environ.get("ROWS", 150))
PITCH_X = PORTRAIT / COLS
PITCH_Y = PORTRAIT / ROWS
STROKE = max(1.0, PITCH_X * 0.32)

BG = "#000000"
INK = "#e6e6e6"
DROP = "#ffffff"
LEVELS = [0.10, 0.22, 0.36, 0.52, 0.72, 1.0]   # stroke-opacity buckets

# ---- reveal timing (seconds) ---------------------------------------------
COL_DUR = 1.3           # how long one column takes to rain down
MAX_DELAY = 1.6         # columns start at random times in [0, MAX_DELAY]
TITLE_AT = MAX_DELAY + COL_DUR * 0.6

random.seed(29)

# ---- 1. sample photo + mask into a COLS x ROWS brightness grid -----------
im = Image.open(SRC).convert("L").resize((COLS, ROWS), Image.LANCZOS)
mk = Image.open(MASK).convert("L").resize((COLS, ROWS), Image.LANCZOS)
px, mpx = im.load(), mk.load()

columns = []   # per column: list of (y, length, level_index)
for cx in range(COLS):
    segs = []
    for ry in range(ROWS):
        m = mpx[cx, ry] / 255.0
        if m < 0.35:
            continue
        lum = px[cx, ry] / 255.0
        # lit skin -> bright, hair/jacket -> faint but present (keeps the silhouette)
        b = (0.08 + 0.92 * lum ** 1.15) * min(1.0, (m - 0.35) / 0.4)
        lvl = min(len(LEVELS) - 1, int(b * len(LEVELS)))
        length = PITCH_Y * (0.35 + 0.65 * b) * random.uniform(0.8, 1.2)
        segs.append((ry * PITCH_Y, length, lvl))
    columns.append(segs)

# ---- 2. build SVG ----------------------------------------------------------
P = []
P.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
P.append('<defs>')
# metallic fill for the title
P.append('<linearGradient id="metal" x1="0" y1="0" x2="0" y2="1">'
         '<stop offset="0" stop-color="#ffffff"/><stop offset="0.35" stop-color="#d4d4d4"/>'
         '<stop offset="0.5" stop-color="#7a7a7a"/><stop offset="0.55" stop-color="#f2f2f2"/>'
         '<stop offset="0.8" stop-color="#9a9a9a"/><stop offset="1" stop-color="#ffffff"/>'
         '</linearGradient>')
# moving highlight swept across the title
shine_anim = '' if STATIC else (
    '<animate attributeName="x1" values="-1.2;1.4" dur="4s" begin="2s" repeatCount="indefinite"/>'
    '<animate attributeName="x2" values="-0.6;2.0" dur="4s" begin="2s" repeatCount="indefinite"/>')
P.append(f'<linearGradient id="shine" x1="-1.2" y1="0" x2="-0.6" y2="0">'
         f'<stop offset="0" stop-color="#fff" stop-opacity="0"/>'
         f'<stop offset="0.5" stop-color="#fff" stop-opacity="0.55"/>'
         f'<stop offset="1" stop-color="#fff" stop-opacity="0"/>{shine_anim}</linearGradient>')
# fade the bottom of the portrait so it dissolves into the rain
P.append(f'<linearGradient id="fadeg" x1="0" y1="0" x2="0" y2="1">'
         f'<stop offset="0" stop-color="#fff"/><stop offset="0.82" stop-color="#fff"/>'
         f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
         f'<mask id="fade"><rect x="{PX}" y="{PY}" width="{PORTRAIT}" height="{PORTRAIT}" fill="url(#fadeg)"/></mask>')
P.append('<filter id="glow" x="-10%" y="-30%" width="120%" height="160%">'
         '<feGaussianBlur stdDeviation="3"/></filter>')
# one top-down clip per column drives the rain-in reveal
if not STATIC:
    for cx in range(COLS):
        if not columns[cx]:
            continue
        delay = random.uniform(0, MAX_DELAY)
        x = PX + cx * PITCH_X
        P.append(f'<clipPath id="c{cx}"><rect x="{x - PITCH_X:.2f}" y="{PY}" width="{PITCH_X * 2:.2f}" height="0">'
                 f'<animate attributeName="height" from="0" to="{PORTRAIT}" begin="{delay:.2f}s" '
                 f'dur="{COL_DUR}s" fill="freeze"/></rect></clipPath>')
        columns[cx] = (delay, columns[cx])
    columns = [c if isinstance(c, tuple) else (0.0, c) for c in columns]
else:
    columns = [(0.0, c) for c in columns]
P.append('</defs>')

P.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')

# ---- faint background rain, looping forever --------------------------------
P.append(f'<g stroke="{INK}" stroke-width="1" stroke-linecap="round">')
for _ in range(70):
    x = random.uniform(0, W)
    ln = random.uniform(40, 260)
    op = random.uniform(0.04, 0.13)
    y0 = random.uniform(-H, H)
    dur = random.uniform(7, 16)
    anim = '' if STATIC else (f'<animateTransform attributeName="transform" type="translate" '
                              f'from="0 {-H}" to="0 {H}" dur="{dur:.1f}s" begin="{random.uniform(-dur, 0):.1f}s" '
                              f'repeatCount="indefinite"/>')
    P.append(f'<line x1="{x:.1f}" y1="{y0:.1f}" x2="{x:.1f}" y2="{y0 + ln:.1f}" stroke-opacity="{op:.2f}">{anim}</line>')
P.append('</g>')

# ---- the portrait: per column, one path per brightness level ----------------
P.append(f'<g mask="url(#fade)" stroke="{INK}" stroke-width="{STROKE:.2f}" stroke-linecap="round" fill="none">')
for cx, (delay, segs) in enumerate(columns):
    if not segs:
        continue
    x = PX + cx * PITCH_X + PITCH_X / 2
    by_level = {}
    for y, ln, lvl in segs:
        by_level.setdefault(lvl, []).append(f'M{x:.1f} {PY + y:.1f}v{ln:.1f}')
    clip = '' if STATIC else f' clip-path="url(#c{cx})"'
    P.append(f'<g{clip}>')
    for lvl, ds in sorted(by_level.items()):
        P.append(f'<path stroke-opacity="{LEVELS[lvl]}" d="{"".join(ds)}"/>')
    P.append('</g>')
    if not STATIC:
        # bright drop riding the reveal edge
        P.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{PY - 22}" y2="{PY}" stroke="{DROP}" stroke-opacity="0" stroke-width="{STROKE:.2f}">'
                 f'<animateTransform attributeName="transform" type="translate" from="0 0" to="0 {PORTRAIT + 22}" '
                 f'begin="{delay:.2f}s" dur="{COL_DUR}s" fill="freeze"/>'
                 f'<set attributeName="stroke-opacity" to="0.9" begin="{delay:.2f}s"/>'
                 f'<set attributeName="stroke-opacity" to="0" begin="{delay + COL_DUR:.2f}s"/></line>')
P.append('</g>')

# ---- title -----------------------------------------------------------------
small_y = PY + PORTRAIT + 68
big_y = small_y + 92
# keep the natural width of the big title UNDER textLength so lengthAdjust="spacing"
# stretches letters apart instead of crushing them (Georgia bold ~0.72em/char)
BIG_LEN = W * 0.86
BIG_SIZE = int(min(84, BIG_LEN / (len(TITLE_BIG) * 0.74)))
BIG_SPACING = 2
font = "Georgia, 'Times New Roman', 'DejaVu Serif', serif"
fade_in = '' if STATIC else f'<animate attributeName="opacity" from="0" to="1" begin="{TITLE_AT:.2f}s" dur="1.2s" fill="freeze"/>'
P.append(f'<g opacity="{1 if STATIC else 0}" font-family="{font}" font-weight="700" text-anchor="middle">{fade_in}')
small = html.escape(TITLE_SMALL)
big = html.escape(TITLE_BIG)
P.append(f'<text x="{W/2}" y="{small_y}" font-size="26" letter-spacing="9" fill="url(#metal)" '
         f'stroke="#3a3a3a" stroke-width="0.6" paint-order="stroke">{small}</text>')
# soft glow behind the big title, then the metal text, then the shine pass
P.append(f'<text x="{W/2}" y="{big_y}" font-size="{BIG_SIZE}" letter-spacing="{BIG_SPACING}" fill="#ffffff" opacity="0.35" '
         f'filter="url(#glow)" textLength="{BIG_LEN:.0f}" lengthAdjust="spacing">{big}</text>')
P.append(f'<text x="{W/2}" y="{big_y}" font-size="{BIG_SIZE}" letter-spacing="{BIG_SPACING}" fill="url(#metal)" '
         f'stroke="#2a2a2a" stroke-width="1.2" paint-order="stroke" '
         f'textLength="{BIG_LEN:.0f}" lengthAdjust="spacing">{big}</text>')
P.append(f'<text x="{W/2}" y="{big_y}" font-size="{BIG_SIZE}" letter-spacing="{BIG_SPACING}" fill="url(#shine)" '
         f'textLength="{BIG_LEN:.0f}" lengthAdjust="spacing">{big}</text>')
P.append('</g>')

P.append('</svg>')
svg = "".join(P)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)
segs_total = sum(len(s) for _, s in columns)
print(f"wrote {OUT}: {W}x{H}, {segs_total} streaks, {len(svg) // 1024} KB")
