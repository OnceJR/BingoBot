from PIL import Image, ImageDraw, ImageFont
from typing import List, Set, Optional, Tuple
import os, time, math, glob

from config import IMAGES_DIR

# ---------- Fuentes ----------
def _load_font(size: int):
    for name in ["Segoe UI", "Arial", "Roboto", "Ubuntu", "DejaVuSans"]:
        try:
            return ImageFont.truetype(f"{name}.ttf", size)
        except Exception:
            continue
    return ImageFont.load_default()

# ---------- Utils ----------
def _rounded(draw: ImageDraw.ImageDraw, rect, r, fill=None, outline=None, width=1):
    x1, y1, x2, y2 = rect
    draw.rounded_rectangle([x1, y1, x2, y2], r, fill=fill, outline=outline, width=width)

def _center_text(draw, rect, text, font, fill):
    x1, y1, x2, y2 = rect
    w, h = draw.textbbox((0, 0), text, font=font)[2:]
    draw.text((x1 + (x2 - x1 - w) // 2, y1 + (y2 - y1 - h) // 2), text, font=font, fill=fill)

def _badge_size(draw, text: str, font, pad_x=14, pad_y=7) -> Tuple[int,int]:
    w, h = draw.textbbox((0,0), text, font=font)[2:]
    return (w + 2*pad_x, h + 2*pad_y)

def _badge(draw, xy, text, font, fill, fg=(14,17,23), pad_x=14, pad_y=7):
    x, y = xy
    w, h = draw.textbbox((0,0), text, font=font)[2:]
    rect = (x, y, x + w + 2*pad_x, y + h + 2*pad_y)
    _rounded(draw, rect, 14, fill=fill)
    draw.text((x + pad_x, y + pad_y), text, font=font, fill=fg)
    return rect  # (x1,y1,x2,y2)

def _soft_shadow_rect(size, radius=16, opacity=40):
    w, h = size
    shadow = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle([4, 4, w + 4, h + 4], radius, fill=(0, 0, 0, opacity))
    return shadow

# ---------- Limpieza automática (1 día) ----------
def _cleanup_images(directory: str, max_age_sec: int = 86400):
    """Borra PNGs en 'directory' con antigüedad mayor a max_age_sec (default: 24h)."""
    now = time.time()
    for f in glob.glob(os.path.join(directory, "*.png")):
        try:
            if now - os.path.getmtime(f) > max_age_sec:
                os.remove(f)
        except Exception:
            pass

# ---------- Tablero 1..90 ----------
def _draw_board(draw, origin, size, called: Set[int], last: Optional[int], fonts):
    x, y = origin
    w, h = size
    elev = (26,31,41); border = (42,49,64)
    text = (230,234,242); primary = (92,200,250)

    _rounded(draw, (x, y, x+w, y+h), 20, fill=elev, outline=border)
    cols, rows = 10, 9
    pad = 16
    cell_w = (w - 2*pad) // cols
    cell_h = (h - 2*pad) // rows
    bx, by = x + pad, y + pad
    num_font = fonts["num"]

    for i in range(90):
        n = i + 1
        c = i % cols
        r = i // cols
        x1 = bx + c*cell_w + 4
        y1 = by + r*cell_h + 4
        x2 = x1 + cell_w - 8
        y2 = y1 + cell_h - 8

        base = (21,25,35)
        fill = base
        outline = border
        if n == last:
            fill = (50,38,18)
            outline = (222,167,58)
            num_color = (252,220,160)
        elif n in called:
            fill = (18,36,48)
            outline = (58,167,222)
            num_color = primary
        else:
            num_color = text

        _rounded(draw, (x1, y1, x2, y2), 10, fill=fill, outline=outline)
        _center_text(draw, (x1, y1, x2, y2), str(n), num_font, num_color)

# ---------- Cartón (mejorado) ----------
def _draw_card(im: Image.Image, draw, origin, size, numbers: List[int], called: Set[int],
               label: str, highlight: bool, last: Optional[int], fonts):
    x, y = origin
    w, h = size

    elev = (26,31,41)
    border = (42,49,64)
    text = (230,234,242)
    accent = (119,227,156)     # verde aciertos
    primary = (92,200,250)     # azul info
    ring = (222,167,58)        # dorado último

    # Sombra del cartón
    card_shadow = _soft_shadow_rect((w, h), radius=22, opacity=50)
    im.paste(card_shadow, (x-4, y-4), card_shadow)

    # Contenedor
    outline = (17,143,88) if highlight else border
    _rounded(draw, (x, y, x+w, y+h), 18, fill=elev, outline=outline, width=3 if highlight else 1)

    # Padding interno del cartón
    PAD = 16
    HEADER_H = 92   # título + badges + barra
    GRID_TOP = y + HEADER_H

    # Header
    small = fonts["small"]; badge_f = fonts["badge"]
    draw.text((x + PAD, y + 12), label, fill=text, font=small)

    hits = len([n for n in numbers if n in called])
    faltan = max(0, 15 - hits)
    b1_text = f"✅ Aciertos {hits}/15"
    b2_text = f"⏳ Faltan {faltan}"

    b1_w, _ = _badge_size(draw, b1_text, badge_f)
    b2_w, _ = _badge_size(draw, b2_text, badge_f)
    GAP = 8
    bx = x + w - PAD - (b1_w + GAP + b2_w)
    by = y + 10

    _badge(draw, (bx, by), b1_text, badge_f, accent)
    _badge(draw, (bx + b1_w + GAP, by), b2_text, badge_f, primary)

    # Barra de progreso (debajo de badges)
    bar_x = x + PAD
    bar_y = y + 50
    bar_w = w - 2*PAD
    bar_h = 10
    _rounded(draw, (bar_x, bar_y, bar_x+bar_w, bar_y+bar_h), 6, fill=(35,40,52))
    pct = hits / 15.0
    _rounded(draw, (bar_x, bar_y, bar_x+int(bar_w*pct), bar_y+bar_h), 6, fill=(46,160,110))

    # Grid 3x5 (chips grandes con sombra)
    nums = sorted(set(numbers))[:]
    while len(nums) < 15:
        nums.append(None)

    cols, rows = 5, 3
    grid_x = x + PAD
    grid_y = GRID_TOP
    cw = (w - 2*PAD) // cols
    ch = (h - (GRID_TOP - y) - PAD) // rows

    chip_font = fonts["chip"]

    for idx, val in enumerate(nums):
        c = idx % cols
        r = idx // cols
        x1 = grid_x + c*cw + 6
        y1 = grid_y + r*ch + 8
        x2 = x1 + cw - 12
        y2 = y1 + ch - 16

        # sombra del chip
        chip_shadow = _soft_shadow_rect((x2 - x1, y2 - y1), radius=18, opacity=45)
        im.paste(chip_shadow, (x1-4, y1-4), chip_shadow)

        base = (31,35,45)
        fill = base
        outline_cell = (50,58,72)
        color = text
        width = 1

        if val is not None and val in called:
            fill = (18,50,38)
            outline_cell = (17,143,88)
            color = accent
            width = 2

        _rounded(draw, (x1, y1, x2, y2), 18, fill=fill, outline=outline_cell, width=width)

        txt = "—" if val is None else str(val)
        _center_text(draw, (x1, y1, x2, y2), txt, chip_font, color)

        if val is not None and val == last:
            _rounded(draw, (x1-3, y1-3, x2+3, y2+3), 20, fill=None, outline=ring, width=3)

# ---------- Render principal ----------
def render(state, chat_id: int) -> str:
    called: Set[int] = set(state.get("called") or [])
    cards: List[List[int]] = state.get("cards") or [[]]
    active = max(0, min(state.get("active", 0), len(cards)-1))
    last = state.get("last")

    # Lienzo
    W, H = 1400, 900
    bg = (14,17,23)
    text = (230,234,242); primary = (92,200,250)

    im = Image.new("RGBA", (W, H), bg + (255,))
    draw = ImageDraw.Draw(im, "RGBA")

    fonts = {
        "title": _load_font(40),
        "small": _load_font(22),
        "num": _load_font(28),
        "badge": _load_font(20),
        "chip": _load_font(36),
    }

    # Header
    title = "🎱 Bingo — Multi-cartones"
    subtitle = f"Cantados: {len(called)}/90"
    if last:
        subtitle += f"  |  Último: {last}"
    draw.text((24, 20), title, fill=text, font=fonts["title"])
    draw.text((24, 70), subtitle, fill=primary, font=fonts["small"])

    # Tablero
    board_rect = (24, 110, 820, 820)
    _draw_board(draw, (board_rect[0], board_rect[1]),
                (board_rect[2]-board_rect[0], board_rect[3]-board_rect[1]),
                called, last, fonts)

    # Cartones (6 por página)
    page = state.get("cards_page", 0)
    per_page = 6
    total = len(cards)
    pages = max(1, math.ceil(total / per_page))
    if page >= pages:
        page = pages - 1

    start = page * per_page
    end = min(start + per_page, total)
    subset = list(enumerate(cards))[start:end]

    cols = 3; rows = 2
    area_x, area_y = 860, 110
    area_w, area_h = W - area_x - 24, 820 - 110
    gap = 18
    card_w = (area_w - gap*(cols-1)) // cols
    card_h = (area_h - gap*(rows-1)) // rows

    hits_idx = set()
    if last is not None:
        for idx, nums in enumerate(cards):
            if last in nums:
                hits_idx.add(idx)

    for i, (idx, nums) in enumerate(subset):
        r = i // cols
        c = i % cols
        x = area_x + c*(card_w + gap)
        y = area_y + r*(card_h + gap)
        label = f"Cartón #{idx+1}{' (Activo)' if idx == active else ''}"
        _draw_card(im, draw, (x, y), (card_w, card_h), nums, called, label, idx in hits_idx, last, fonts)

    # Footer
    footer = f"Cartones {start+1}-{end} de {total}  |  Página {page+1}/{pages}"
    draw.text((860, 840), footer, fill=text, font=fonts["small"])

    # Guardar + limpieza
    path = os.path.join(IMAGES_DIR, f"board_{chat_id}_{int(time.time()*1000)}.png")
    im.convert("RGB").save(path, "PNG")

    # 🔥 borrar imágenes viejas (24h)
    _cleanup_images(IMAGES_DIR, max_age_sec=86400)

    return path
