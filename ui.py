from telethon.tl.custom import Button

def main_menu(clean_mode: bool = True):
    toggle = "🧽 Chat limpio: ON" if clean_mode else "🧽 Chat limpio: OFF"
    return [
        [Button.inline("➕ Añadir cartón", b"card:add"), Button.inline("📄 Duplicar", b"card:dup"), Button.inline("🗑️ Eliminar", b"card:del")],
        [Button.inline("🎯 Anotar número", b"num:menu"), Button.inline("↩️ Deshacer", b"num:undo"), Button.inline("🧹 Reiniciar", b"num:reset")],
        [Button.inline("✏️ Editar cartón", b"card:edit"), Button.inline("🔁 Cambiar activo", b"card:switch")],
        [Button.inline("🗂 Ver cartones", b"cards:view"), Button.inline("📥 Importar CSV", b"card:import"), Button.inline("📤 Exportar CSV", b"card:export")],
        [Button.inline("❓ Ayuda rápida", b"help:quick"), Button.inline("🔄 Refrescar vista", b"view:refresh")],
        [Button.inline(toggle, b"cfg:clean_toggle")]
    ]

def numbers_page(page: int = 0):
    per_page = 30
    start = page*per_page + 1
    end = min((page+1)*per_page, 90)
    rows = []
    row = []
    for n in range(start, end+1):
        row.append(Button.inline(str(n), f"num:add:{n}".encode()))
        if len(row) == 10:
            rows.append(row); row = []
    if row:
        rows.append(row)
    nav = []
    if page > 0:
        nav.append(Button.inline("⬅️ Anteriores", f"num:page:{page-1}".encode()))
    if end < 90:
        nav.append(Button.inline("Siguientes ➡️", f"num:page:{page+1}".encode()))
    if nav:
        rows.append(nav)
    rows.append([Button.inline("🏠 Menú", b"home")])
    return rows

def cards_switch_menu(cards_count: int, active_idx: int):
    rows = []
    row = []
    for i in range(cards_count):
        label = f"#{i+1} {'✅' if i==active_idx else ''}"
        row.append(Button.inline(label, f"card:activate:{i}".encode()))
        if len(row) == 4:
            rows.append(row); row=[]
    if row:
        rows.append(row)
    rows.append([Button.inline("🏠 Menú", b"home")])
    return rows

def cards_paging_controls(has_prev: bool, has_next: bool):
    nav = []
    if has_prev:
        nav.append(Button.inline("⬅️ Página", b"cards:prev"))
    if has_next:
        nav.append(Button.inline("Página ➡️", b"cards:next"))
    nav.append(Button.inline("🏠 Menú", b"home"))
    return [nav]
