import re
import math
import random
from telethon import TelegramClient, events, Button
from telethon.errors import MessageNotModifiedError
from config import API_ID, API_HASH, BOT_TOKEN
from storage import Store
from render import render
import ui

# Inicialización
store = Store()
bot = TelegramClient("bingo-bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

def _normalize_card(parts):
    """Extrae números válidos (1-90) de una lista y los devuelve ordenados sin duplicados."""
    nums = set()
    for p in parts:
        try:
            n = int(p.strip())
            if 1 <= n <= 90:
                nums.add(n)
        except ValueError:
            pass
    return sorted(list(nums))

async def _send_view(event, state, caption=""):
    """Renderiza y envía/edita el tablero principal de Bingo."""
    img_bio = render(state, event.chat_id)
    buttons = ui.main_menu(state.get("clean_mode", True))
    caption_str = caption or " "

    if state.get("clean_mode") and state.get("last_msg_id"):
        try:
            await bot.edit_message(
                event.chat_id,
                state["last_msg_id"],
                text=caption_str,
                file=img_bio,
                buttons=buttons,
                parse_mode=None
            )
            return
        except MessageNotModifiedError:
            # Ignorar si nada ha cambiado visualmente
            return
        except Exception:
            # Si falla (ej: el usuario borró el mensaje viejo), manda uno nuevo
            pass

    m = await bot.send_file(
        event.chat_id,
        img_bio,
        caption=caption_str,
        buttons=buttons,
        parse_mode=None
    )
    state["last_msg_id"] = m.id
    await store.set(event.chat_id, state)


# ==========================================
# MANEJADORES DE MENSAJES DE TEXTO Y COMANDOS
# ==========================================

@bot.on(events.NewMessage(pattern=r"^/start$"))
async def start(event):
    st = await store.get(event.chat_id)
    await event.respond(
        "Bienvenido/a 🎱\n"
        "Cargá tu cartón (✏️ o /azar) y anotá números con 🎯 o escribiendo el número.\n"
        "Modo **Chat limpio** activo: el bot edita su último mensaje para no hacer spam.",
        buttons=ui.main_menu(st.get("clean_mode", True)),
        parse_mode="md"
    )
    await _send_view(event, st)

@bot.on(events.NewMessage(pattern=r"^/help$"))
async def help_cmd(event):
    st = await store.get(event.chat_id)
    await event.respond(
        "Ayuda rápida:\n"
        "• ✏️ Editar cartón → pegá 15 números (1–90) o /azar.\n"
        "• 🎯 Anotar número → teclado 1–90 o escribí el número.\n"
        "• 🧽 Chat limpio ON → el bot edita su propia imagen y no llena el chat.\n",
        buttons=ui.main_menu(st.get("clean_mode", True))
    )

@bot.on(events.NewMessage(pattern=r"^\s*(\d{1,2})\s*$"))
async def on_number(event):
    n = int(event.pattern_match.group(1))
    if not (1 <= n <= 90):
        return
    st = await store.get(event.chat_id)
    if n in st["called"]:
        if not st.get("clean_mode", True):
            await event.reply("Número repetido ❌")
        return
    st["called"].append(n)
    st["last"] = n
    await store.set(event.chat_id, st)
    await _send_view(event, st, caption=f"Anotado {n} ✅")

@bot.on(events.NewMessage)
async def text_handler(event):
    # Ignorar comandos explícitos para que no interfieran
    if (event.raw_text or "").strip().startswith("/"):
        if (event.raw_text or "").lower().startswith("/azar"):
            st = await store.get(event.chat_id)
            st["cards"][st["active"]] = sorted(random.sample(range(1,91), 15))
            await store.set(event.chat_id, st)
            await _send_view(event, st, caption="Cartón generado al azar 🎲")
        return
        
    st = await store.get(event.chat_id)
    msg = (event.raw_text or "").strip()
    
    # Detección de lista de números separados por espacios, comas o guiones
    if "," in msg or " " in msg or "-" in msg: 
        parts = re.split(r"[,\s\-]+", msg)
        nums = _normalize_card(parts)
        if len(nums) == 15:
            st["cards"][st["active"]] = sorted(nums)
            await store.set(event.chat_id, st)
            await _send_view(event, st, caption="Cartón actualizado ✅")


# ==========================================
# MANEJADORES DE BOTONES (CALLBACKS)
# ==========================================

@bot.on(events.CallbackQuery(pattern=b"^home$"))
async def cb_home(ev):
    st = await store.get(ev.chat_id)
    await ev.edit(buttons=ui.main_menu(st.get("clean_mode", True)))

@bot.on(events.CallbackQuery(pattern=b"^cfg:clean_toggle$"))
async def cb_clean_toggle(ev):
    st = await store.get(ev.chat_id)
    st["clean_mode"] = not st.get("clean_mode", True)
    await store.set(ev.chat_id, st)
    await ev.answer("Chat limpio ON" if st["clean_mode"] else "Chat limpio OFF", alert=False)
    await _send_view(ev, st, caption="Preferencia actualizada")

@bot.on(events.CallbackQuery(pattern=b"^num:add:(\d+)"))
async def cb_num_add(ev):
    n = int(ev.pattern_match.group(1).decode())
    st = await store.get(ev.chat_id)
    if n in st["called"]:
        await ev.answer("Ya está cantado ❌", alert=False)
    else:
        st["called"].append(n)
        st["last"] = n
        await store.set(ev.chat_id, st)
        await ev.answer(f"Anotado {n} ✅", alert=False)
        try:
            await ev.delete() # Borrar menú temporal de números
        except Exception:
            pass
        await _send_view(ev, st, caption=f"Anotado {n} ✅")

@bot.on(events.CallbackQuery(pattern=b"^num:undo$"))
async def cb_num_undo(ev):
    st = await store.get(ev.chat_id)
    if st["called"]:
        last = st["called"].pop()
        st["last"] = st["called"][-1] if st["called"] else None
        await store.set(ev.chat_id, st)
        await ev.answer(f"Deshecho {last}", alert=False)
        await _send_view(ev, st, caption=f"Deshecho {last} ↩️")
    else:
        await ev.answer("Nada para deshacer", alert=True)

@bot.on(events.CallbackQuery(pattern=b"^num:reset$"))
async def cb_num_reset(ev):
    st = await store.get(ev.chat_id)
    if st["called"]:
        st["called"] = []
        st["last"] = None
        await store.set(ev.chat_id, st)
        await ev.answer("Cantados reiniciados 🧹", alert=False)
        await _send_view(ev, st, caption="Cantados reiniciados 🧹")
    else:
        await ev.answer("No hay cantados", alert=True)

@bot.on(events.CallbackQuery(pattern=b"^card:(add|dup|del)$"))
async def cb_card_manage(ev):
    action = ev.pattern_match.group(1).decode()
    st = await store.get(ev.chat_id)
    
    if action == "add":
        st["cards"].append([])
        st["active"] = len(st["cards"]) - 1
        await store.set(ev.chat_id, st)
        await ev.answer("Cartón añadido ➕", alert=False)
        await _send_view(ev, st, caption=f"Nuevo cartón #{st['active']+1}")
        
    elif action == "dup":
        src = st["cards"][st["active"]][:] if st["cards"] else []
        st["cards"].append(src)
        st["active"] = len(st["cards"]) - 1
        await store.set(ev.chat_id, st)
        await ev.answer("Cartón duplicado 📄", alert=False)
        await _send_view(ev, st, caption=f"Duplicado como #{st['active']+1}")
        
    elif action == "del":
        if len(st["cards"]) <= 1:
            await ev.answer("Debe existir al menos 1 cartón", alert=True)
        else:
            st["cards"].pop(st["active"])
            st["active"] = max(0, st["active"] - 1)
            st["cards_page"] = 0
            await store.set(ev.chat_id, st)
            await ev.answer("Cartón eliminado 🗑️", alert=False)
            await _send_view(ev, st, caption="Cartón eliminado 🗑️")

@bot.on(events.CallbackQuery(pattern=b"^card:activate:(\d+)"))
async def cb_card_activate(ev):
    idx = int(ev.pattern_match.group(1).decode())
    st = await store.get(ev.chat_id)
    if 0 <= idx < len(st["cards"]):
        st["active"] = idx
        await store.set(ev.chat_id, st)
        await ev.answer(f"Activo #{idx+1}", alert=False)
        await _send_view(ev, st, caption=f"Cartón activo #{idx+1} ✅")
    else:
        await ev.answer("Índice inválido", alert=True)

@bot.on(events.CallbackQuery(pattern=b"^cards:(prev|next)$"))
async def cb_cards_pagination(ev):
    action = ev.pattern_match.group(1).decode()
    st = await store.get(ev.chat_id)
    total = len(st["cards"])
    per_page = 6
    pages = max(1, math.ceil(total/per_page))
    
    if action == "prev" and st["cards_page"] > 0:
        st["cards_page"] -= 1
        await store.set(ev.chat_id, st)
        await ev.answer("Página anterior", alert=False)
    elif action == "next" and st["cards_page"] < pages-1:
        st["cards_page"] += 1
        await store.set(ev.chat_id, st)
        await ev.answer("Página siguiente", alert=False)
        
    await _send_view(ev, st)

@bot.on(events.CallbackQuery(pattern=b"^num:menu$"))
async def cb_num_menu(ev):
    await ev.edit("Elegí un número 👇", buttons=ui.numbers_page(0))

@bot.on(events.CallbackQuery(pattern=b"^num:page:(\d+)"))
async def cb_num_page(ev):
    page = int(ev.pattern_match.group(1).decode())
    await ev.edit("Elegí un número 👇", buttons=ui.numbers_page(page))

@bot.on(events.CallbackQuery(pattern=b"^card:switch$"))
async def cb_card_switch(ev):
    st = await store.get(ev.chat_id)
    await ev.edit("Elegí cartón activo:", buttons=ui.cards_switch_menu(len(st["cards"]), st["active"]))

@bot.on(events.CallbackQuery(pattern=b"^view:refresh$"))
async def cb_view_refresh(ev):
    st = await store.get(ev.chat_id)
    await _send_view(ev, st, caption="Vista actualizada 🔄")

@bot.on(events.CallbackQuery(pattern=b"^cards:view$"))
async def cb_cards_view(ev):
    st = await store.get(ev.chat_id)
    total = len(st["cards"])
    pages = max(1, math.ceil(total/6))
    has_prev = st["cards_page"] > 0
    has_next = st["cards_page"] < pages-1
    await ev.edit(f"Mostrando cartones — página {st['cards_page']+1}/{pages}", buttons=ui.cards_paging_controls(has_prev, has_next))
    await _send_view(ev, st)

@bot.on(events.CallbackQuery(pattern=b"^(help:quick|card:edit|card:import|card:export|card:rand)$"))
async def cb_static_menus(ev):
    data = ev.pattern_match.group(1).decode()
    st = await store.get(ev.chat_id)
    
    if data == "help:quick":
        await ev.edit(
            "💡 **Ayuda rápida**\n"
            "1) ✏️ o /azar para tu cartón...\n"
            "2) 🧽 Chat limpio edita la última imagen.", 
            buttons=[[Button.inline("🏠 Menú", b"home")]], 
            parse_mode="md"
        )
    elif data == "card:edit":
        await ev.edit(
            "✏️ **Editar cartón activo**\nPegá 15 números...", 
            buttons=[
                [Button.inline("🎲 Generar al azar", b"card:rand")],
                [Button.inline("🏠 Menú", b"home")]
            ], 
            parse_mode="md"
        )
    elif data == "card:import":
        await ev.edit(
            "📥 **Importar CSV**\nPegá los 15 números...", 
            buttons=[[Button.inline("🏠 Menú", b"home")]], 
            parse_mode="md"
        )
    elif data == "card:export":
        card = st["cards"][st["active"]]
        if len(card) != 15:
            await ev.answer("El cartón debe tener 15 números", alert=True)
        else:
            csv = ",".join(str(n) for n in sorted(card))
            await ev.answer("CSV generado", alert=False)
            await ev.edit(
                f"📤 **CSV del cartón #{st['active']+1}:**\n`{csv}`", 
                parse_mode="md", 
                buttons=[[Button.inline("🏠 Menú", b"home")]]
            )
    elif data == "card:rand":
        st["cards"][st["active"]] = sorted(random.sample(range(1,91), 15))
        await store.set(ev.chat_id, st)
        await ev.answer("Cartón generado 🎲", alert=False)
        await _send_view(ev, st, caption=f"Cartón #{st['active']+1} (azar)")


# ==========================================
# PUNTO DE ENTRADA PRINCIPAL
# ==========================================

def main():
    print("Bingo Bot listo 🎱")
    # Inicializamos la base de datos de manera sincrona en el loop principal
    bot.loop.run_until_complete(store.init_db())
    bot.run_until_disconnected()

if __name__ == "__main__":
    main()