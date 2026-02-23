import re, math
from telethon import TelegramClient, events, Button
from config import API_ID, API_HASH, BOT_TOKEN
from storage import Store
from render import render
import ui

store = Store()
bot = TelegramClient("bingo-bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

def _normalize_card(card):
    nums = []
    seen = set()
    for x in card:
        try:
            n = int(x)
            if 1 <= n <= 90 and n not in seen:
                nums.append(n); seen.add(n)
        except Exception:
            continue
        if len(nums) == 15:
            break
    return nums

async def _send_view(event, state, caption=""):
    """
    Renderiza la imagen y la publica. Si 'chat limpio' está ON, intenta
    editar el último mensaje del bot; si no puede, envía uno nuevo con send_file.
    (parse_mode desactivado para evitar ValueError: Failed to parse message)
    """
    img = render(state, event.chat_id)
    buttons = ui.main_menu(state.get("clean_mode", True))
    caption_str = caption or " "

    # 1) Intentar editar (chat limpio)
    if state.get("clean_mode") and state.get("last_msg_id"):
        try:
            await bot.edit_message(
                event.chat_id,
                state["last_msg_id"],
                text=caption_str,
                file=img,
                buttons=buttons,
                parse_mode=None   # <- importantísimo
            )
            return
        except Exception:
            pass  # si no se puede editar, mandamos uno nuevo

    # 2) Enviar imagen nueva (send_file soporta caption)
    m = await bot.send_file(
        event.chat_id,
        img,
        caption=caption_str,
        buttons=buttons,
        parse_mode=None       # <- importantísimo
    )
    state["last_msg_id"] = m.id
    store.set(event.chat_id, state)

def _hit_count(state):
    active = state["active"]
    card = set(state["cards"][active]) if state["cards"] else set()
    called = set(state["called"])
    return len(card & called)

@bot.on(events.NewMessage(pattern=r"^/start$"))
async def start(event):
    st = store.get(event.chat_id)
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
    st = store.get(event.chat_id)
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
    st = store.get(event.chat_id)
    if n in st["called"]:
        # No spameamos si está en clean_mode
        if not st.get("clean_mode", True):
            await event.reply("Número repetido ❌")
        return
    st["called"].append(n)
    st["last"] = n
    store.set(event.chat_id, st)
    await _send_view(event, st, caption=f"Anotado {n} ✅")

@bot.on(events.CallbackQuery)
async def callbacks(ev):
    data = ev.data.decode()
    st = store.get(ev.chat_id)

    if data == "home":
        await ev.edit(buttons=ui.main_menu(st.get("clean_mode", True)))
        return

    if data == "cfg:clean_toggle":
        st["clean_mode"] = not st.get("clean_mode", True)
        store.set(ev.chat_id, st)
        await ev.answer("Chat limpio ON" if st["clean_mode"] else "Chat limpio OFF", alert=False)
        await _send_view(ev, st, caption="Preferencia actualizada")
        return

    if data == "help:quick":
        await ev.edit(
            "💡 **Ayuda rápida**\n"
            "1) ✏️ o /azar para tu cartón (15 números).\n"
            "2) 🎯 o escribí el número para anotarlo.\n"
            "3) El tablero resalta el último; los cartones que lo contienen llevan borde verde.\n"
            "4) 🧽 Chat limpio edita la última imagen en vez de mandar varias.",
            buttons=[[Button.inline("🏠 Menú", b"home")]],
            parse_mode="md"
        )
        return

    if data == "num:menu":
        await ev.edit("Elegí un número 👇", buttons=ui.numbers_page(0))
        return
    m = re.match(r"num:page:(\d+)", data)
    if m:
        page = int(m.group(1))
        await ev.edit("Elegí un número 👇", buttons=ui.numbers_page(page))
        return
    m = re.match(r"num:add:(\d+)", data)
    if m:
        n = int(m.group(1))
        if n in st["called"]:
            await ev.answer("Ya está cantado ❌", alert=False)
        else:
            st["called"].append(n)
            st["last"] = n
            store.set(ev.chat_id, st)
            await ev.answer(f"Anotado {n} ✅", alert=False)
            try:
                await ev.delete()
            except Exception:
                pass
            await _send_view(ev, st, caption=f"Anotado {n} ✅")
        return

    if data == "num:undo":
        if st["called"]:
            last = st["called"].pop()
            st["last"] = st["called"][-1] if st["called"] else None
            store.set(ev.chat_id, st)
            await ev.answer(f"Deshecho {last}", alert=False)
            await _send_view(ev, st, caption=f"Deshecho {last} ↩️")
        else:
            await ev.answer("Nada para deshacer", alert=True)
        return
    if data == "num:reset":
        if st["called"]:
            st["called"] = []
            st["last"] = None
            store.set(ev.chat_id, st)
            await ev.answer("Cantados reiniciados 🧹", alert=False)
            await _send_view(ev, st, caption="Cantados reiniciados 🧹")
        else:
            await ev.answer("No hay cantados", alert=True)
        return

    if data == "card:add":
        st["cards"].append([])
        st["active"] = len(st["cards"]) - 1
        store.set(ev.chat_id, st)
        await ev.answer("Cartón añadido ➕", alert=False)
        await _send_view(ev, st, caption=f"Nuevo cartón #{st['active']+1}")
        return
    if data == "card:dup":
        src = st["cards"][st["active"]][:] if st["cards"] else []
        st["cards"].append(src)
        st["active"] = len(st["cards"]) - 1
        store.set(ev.chat_id, st)
        await ev.answer("Cartón duplicado 📄", alert=False)
        await _send_view(ev, st, caption=f"Duplicado como #{st['active']+1}")
        return
    if data == "card:del":
        if len(st["cards"]) <= 1:
            await ev.answer("Debe existir al menos 1 cartón", alert=True)
        else:
            st["cards"].pop(st["active"])
            st["active"] = max(0, st["active"] - 1)
            st["cards_page"] = 0
            store.set(ev.chat_id, st)
            await ev.answer("Cartón eliminado 🗑️", alert=False)
            await _send_view(ev, st, caption="Cartón eliminado 🗑️")
        return

    if data == "card:edit":
        await ev.edit(
            "✏️ **Editar cartón activo**\n"
            "Pegá 15 números únicos (1–90) separados por coma, ej:\n"
            "`2,7,10,14,23,28,35,42,50,57,61,70,74,83,90`\n\n"
            "O usá /azar para generar 15 al azar.",
            buttons=[[Button.inline("🎲 Generar al azar", b"card:rand")],[Button.inline("🏠 Menú", b"home")]],
            parse_mode="md"
        )
        return
    if data == "card:rand":
        import random
        nums = sorted(random.sample(range(1,91), 15))
        st["cards"][st["active"]] = nums
        store.set(ev.chat_id, st)
        await ev.answer("Cartón generado 🎲", alert=False)
        await _send_view(ev, st, caption=f"Cartón #{st['active']+1} (azar)")
        return

    if data == "card:switch":
        await ev.edit("Elegí cartón activo:", buttons=ui.cards_switch_menu(len(st["cards"]), st["active"]))
        return
    m = re.match(r"card:activate:(\d+)", data)
    if m:
        idx = int(m.group(1))
        if 0 <= idx < len(st["cards"]):
            st["active"] = idx
            store.set(ev.chat_id, st)
            await ev.answer(f"Activo #{idx+1}", alert=False)
            await _send_view(ev, st, caption=f"Cartón activo #{idx+1} ✅")
        else:
            await ev.answer("Índice inválido", alert=True)
        return

    if data == "card:import":
        await ev.edit(
            "📥 **Importar CSV del cartón activo**\nPegá los 15 números separados por coma (1–90, únicos).",
            buttons=[[Button.inline("🏠 Menú", b"home")]],
            parse_mode="md"
        )
        return
    if data == "card:export":
        card = st["cards"][st["active"]]
        if len(card) != 15:
            await ev.answer("El cartón activo debe tener 15 números", alert=True)
        else:
            csv = ",".join(str(n) for n in sorted(card))
            await ev.answer("CSV generado", alert=False)
            await ev.edit(f"📤 **CSV del cartón #{st['active']+1}:**\n`{csv}`", parse_mode="md", buttons=[[Button.inline("🏠 Menú", b"home")]])
        return

    if data == "view:refresh":
        await _send_view(ev, st, caption="Vista actualizada 🔄")
        return

    if data == "cards:view":
        total = len(st["cards"])
        per_page = 6
        pages = max(1, math.ceil(total/per_page))
        has_prev = st["cards_page"] > 0
        has_next = st["cards_page"] < pages-1
        await ev.edit(f"Mostrando cartones — página {st['cards_page']+1}/{pages}", buttons=ui.cards_paging_controls(has_prev, has_next))
        await _send_view(ev, st)
        return
    if data == "cards:prev":
        if st["cards_page"] > 0:
            st["cards_page"] -= 1
            store.set(ev.chat_id, st)
            await ev.answer("Página anterior", alert=False)
        await _send_view(ev, st)
        return
    if data == "cards:next":
        total = len(st["cards"])
        per_page = 6
        pages = max(1, math.ceil(total/per_page))
        if st["cards_page"] < pages-1:
            st["cards_page"] += 1
            store.set(ev.chat_id, st)
            await ev.answer("Página siguiente", alert=False)
        await _send_view(ev, st)
        return

@bot.on(events.NewMessage)
async def text_handler(event):
    st = store.get(event.chat_id)
    msg = (event.raw_text or "").strip()
    if "," in msg:
        parts = re.split(r"[,\\s]+", msg)
        nums = _normalize_card(parts)
        if len(nums) == 15:
            st["cards"][st["active"]] = sorted(nums)
            store.set(event.chat_id, st)
            await _send_view(event, st, caption="Cartón actualizado ✅")
            return

    if msg.lower().startswith("/azar"):
        import random
        st["cards"][st["active"]] = sorted(random.sample(range(1,91), 15))
        store.set(event.chat_id, st)
        await _send_view(event, st, caption="Cartón generado al azar 🎲")
        return

def main():
    print("Bingo Bot listo 🎱")
    bot.run_until_disconnected()

if __name__ == "__main__":
    main()
