from PIL import Image, ImageDraw, ImageFont
from typing import List, Set, Optional, Tuple
import os, time, math, glob

from config import IMAGES_DIR

# ---------- Fuentes y Caché ----------
def _load_font(size: int):
    for name in ["Segoe UI", "Arial", "Roboto", "Ubuntu", "DejaVuSans"]:
        try:
            return ImageFont.truetype(f"{name}.ttf", size)
        except Exception:
            continue
    return ImageFont.load_default()

FONTS_CACHE = {}

def _get_fonts():
    if not FONTS_CACHE:
        FONTS_CACHE["title"] = _load_font(40)
        FONTS_CACHE["small"] = _load_font(22)
        FONTS_CACHE["num"] = _load_font(28)
        FONTS_CACHE["badge"] = _load_font(20)
        FONTS_CACHE["chip"] = _load_font(36)
    return FONTS_CACHE

# ---------- Utils ----------
def _rounded(draw: ImageDraw.ImageDraw, rect, r, fill=None, outline=None, width=1):
    x1, y1, x2, y2 = rect
    draw.rounded_rectangle([x1, y1, x2, y2], r, fill=fill, outline=outline, width=width)

def _center_text(draw, rect, text, font, fill):
    x1, y1, x2, y2 = rect
    w, h = draw.textbbox((0, 0), text, font=font)[2:]
    draw.text((x1 + (x2 - x1 - w) // 2, y1 + (y2 - y1 - h) // 2), text, font=font, fill=fill)

def _soft_shadow_rect(size, radius=16, opacity=40):
    w, h = size
    shadow = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle([4, 4, w + 4, h + 4], radius, fill=(0, 0, 0, opacity))
    return shadow

# ---------- Limpieza automática ----------
def cleanup_images(directory: str, max_age_sec: int = 86400):
    now = time.time()
    for f in glob.glob(os.path.join(directory, "*.png")):
        try:
            if now - os.path.getmtime(f) > max_age_sec:
                os.remove(f)
        except Exception:
            pass

# ---------- Tablero Principal (1..90) ----------
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

# ---------- Cartones Laterales Rediseñados ----------
def _draw_card(im: Image.Image, draw, origin, size, numbers: List[int], called: Set[int],
               label: str, highlight: bool, last: Optional[int], fonts):
    x, y = origin
    w, h = size

    elev = (26,31,41)
    border = (42,49,64)
    text_color = (230,234,242)
    accent = (119,227,156)     
    primary = (92,200,250)     
    ring = (222,167,58)        

    # Sombra del cartón
    card_shadow = _soft_shadow_rect((w, h), radius=22, opacity=50)
    im.paste(card_shadow, (x-4, y-4), card_shadow)

    # Borde (verde si tiene el último número, normal si no)
    outline = accent if highlight else border
    _rounded(draw, (x, y, x+w, y+h), 18, fill=elev, outline=outline, width=2 if highlight else 1)

    PAD = 16
    
    # Textos de la cabecera (Title y Aciertos)
    small = fonts["small"]
    badge_f = fonts["badge"]
    
    draw.text((x + PAD, y + PAD), label, fill=text_color, font=small)

    hits = len([n for n in numbers if n in called])
    hits_text = f"{hits}/15 aciertos"
    hw = draw.textbbox((0,0), hits_text, font=badge_f)[2]
    # Si completó los 15, lo pintamos verde, si no, azulito
    draw.text((x + w - PAD - hw, y + PAD + 2), hits_text, fill=primary if hits < 15 else accent, font=badge_f)

    # Barra de progreso estilizada
    bar_y = y + PAD + 32
    bar_h = 6
    _rounded(draw, (x+PAD, bar_y, x+w-PAD, bar_y+bar_h), 3, fill=(35,40,52))
    if hits > 0:
        pct = hits / 15.0
        _rounded(draw, (x+PAD, bar_y, x+PAD+int((w-2*PAD)*pct), bar_y+bar_h), 3, fill=accent)

    # Preparar números del grid
    nums: List[Optional[int]] = list(sorted(set(numbers)))
    while len(nums) < 15:
        nums.append(None)

    # Medidas de la nueva cuadrícula 5x3
    GRID_TOP = bar_y + 20
    cols, rows = 5, 3
    grid_x = x + PAD
    grid_y = GRID_TOP
    cw = (w - 2*PAD) // cols
    ch = (h - (GRID_TOP - y) - PAD) // rows

    # Usamos num_font (más pequeña) porque hay más celdas por fila
    chip_font = fonts["num"] 

    for idx, val in enumerate(nums):
        c = idx % cols
        r = idx // cols
        
        # Generar "margen" interno entre chips
        x1 = grid_x + c*cw + 3
        y1 = grid_y + r*ch + 3
        x2 = grid_x + (c+1)*cw - 3
        y2 = grid_y + (r+1)*ch - 3

        # Sombrita tenue
        chip_shadow = _soft_shadow_rect((x2 - x1, y2 - y1), radius=10, opacity=25)
        im.paste(chip_shadow, (x1-3, y1-3), chip_shadow)

        base = (31,35,45)
        fill = base
        outline_cell = (50,58,72)
        color = text_color
        width = 1

        if val is not None and val in called:
            fill = (18,50,38)
            outline_cell = (17,143,88)
            color = accent
            width = 2

        _rounded(draw, (x1, y1, x2, y2), 8, fill=fill, outline=outline_cell, width=width)

        txt = "—" if val is None else str(val)
        _center_text(draw, (x1, y1, x2, y2), txt, chip_font, color)

        if val is not None and val == last:
            _rounded(draw, (x1-2, y1-2, x2+2, y2+2), 10, fill=None, outline=ring, width=2)

# ---------- Render principal ----------
def render(state, chat_id: int) -> str:
    called: Set[int] = set(state.get("called") or [])
    cards: List[List[int]] = state.get("cards") or [[]]
    active = max(0, min(state.get("active", 0), len(cards)-1))
    last = state.get("last")

    W, H = 1400, 900
    bg = (14,17,23)
    text = (230,234,242); primary = (92,200,250)

    im = Image.new("RGBA", (W, H), bg + (255,))
    draw = ImageDraw.Draw(im, "RGBA")

    fonts = _get_fonts()

    title = "🎱 Bingo — Multi-cartones"
    subtitle = f"Cantados: {len(called)}/90"
    if last:
        subtitle += f"  |  Último: {last}"
    draw.text((24, 20), title, fill=text, font=fonts["title"])
    draw.text((24, 70), subtitle, fill=primary, font=fonts["small"])

    board_rect = (24, 110, 820, 820)
    _draw_board(draw, (board_rect[0], board_rect[1]),
                (board_rect[2]-board_rect[0], board_rect[3]-board_rect[1]),
                called, last, fonts)

    page = state.get("cards_page", 0)
    per_page = 6
    total = len(cards)
    pages = max(1, math.ceil(total / per_page))
    if page >= pages:
        page = pages - 1

    start = page * per_page
    end = min(start + per_page, total)
    subset = list(enumerate(cards))[start:end]

    # NUEVO LAYOUT: 2 columnas x 3 filas
    cols = 2; rows = 3
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

    footer = f"Cartones {start+1}-{end} de {total}  |  Página {page+1}/{pages}"
    draw.text((860, 840), footer, fill=text, font=fonts["small"])

    path = os.path.join(IMAGES_DIR, f"board_{chat_id}_{int(time.time()*1000)}.png")
    im.convert("RGB").save(path, "PNG")

    return path