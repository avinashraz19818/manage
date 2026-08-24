# ══════════════════════════════════════════════════════════════════════
#   👑 MᴀɴᴀɢᴇX – Aᴅᴠᴀɴᴄᴇᴅ Tᴇʟᴇɢʀᴀᴍ Gʀᴏᴜᴘ Mᴀɴᴀɢᴇᴍᴇɴᴛ Bᴏᴛ 👑
#   Rose Bot + Mention Bot style • Single File • Pyrogram v2
#   ▸ Run:  pip install -r requirements.txt  &&  python3 manage.py
# ══════════════════════════════════════════════════════════════════════

import asyncio
import json
import os
import re
import threading
import time
from collections import deque
from datetime import datetime, timedelta

from pyrogram import Client, enums, filters
from pyrogram.errors import FloodWait, RPCError
from pyrogram.types import (
    ChatPermissions,
    ChatPrivileges,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

import config as cfg

START_TIME = time.time()

# ═══════════════════════ ✨ Fᴏɴᴛ Sᴛʏʟᴇʀ (Sᴍᴀʟʟ Cᴀᴘs) ═══════════════════════

SMALL_CAPS = {
    "a": "ᴀ", "b": "ʙ", "c": "ᴄ", "d": "ᴅ", "e": "ᴇ", "f": "ꜰ", "g": "ɢ",
    "h": "ʜ", "i": "ɪ", "j": "ᴊ", "k": "ᴋ", "l": "ʟ", "m": "ᴍ", "n": "ɴ",
    "o": "ᴏ", "p": "ᴘ", "q": "ǫ", "r": "ʀ", "s": "ѕ", "t": "ᴛ", "u": "ᴜ",
    "v": "ᴠ", "w": "ᴡ", "x": "x", "y": "ʏ", "z": "ᴢ",
}
SKIP = ("http://", "https://", "tg://", "@", "/", "#")


def _word(w: str) -> str:
    lw = w.lower()
    if any(lw.startswith(p) for p in SKIP) or "://" in w or "{" in w or w.startswith("`"):
        return w
    out, first = [], not (w and w[0].isdigit())
    for ch in w:
        if ch.isalpha() and ch.lower() in SMALL_CAPS:
            out.append(ch.upper() if first else SMALL_CAPS[ch.lower()])
            first = False
        else:
            out.append(ch)
    return "".join(out)


def stylize(text: str) -> str:
    """Har word ka pehla letter normal capital, baaki small caps ✨"""
    if not text:
        return text
    return "".join(p if p.isspace() else _word(p) for p in re.split(r"(\s+)", text))


def md(t: str) -> str:
    return re.sub(r"([_*`\[\]])", r"\\\1", t or "")


# ═══════════════════════ 💎 Cᴏʟᴏʀᴇᴅ Bᴜᴛᴛᴏɴ Bᴜɪʟᴅᴇʀ ═══════════════════════

COLORS = {
    "red": "🟥", "green": "🟩", "blue": "🟦", "yellow": "🟨",
    "purple": "🟪", "orange": "🟧", "white": "⬜", "black": "⬛",
}


def B(label, cb=None, url=None, color=None, icon=None):
    ic = icon or COLORS.get(color)
    txt = f"{ic} {stylize(label)}" if ic else stylize(label)
    if url:
        return InlineKeyboardButton(txt, url=url)
    return InlineKeyboardButton(txt, callback_data=cb)


def KB(*rows):
    return InlineKeyboardMarkup([list(r) for r in rows])


# ═══════════════════════ 🗄️ Jꜱᴏɴ Dᴀᴛᴀʙᴀꜱᴇ ═══════════════════════

DB_LOCK = threading.RLock()


def _load():
    try:
        with open(cfg.DB_PATH) as f:
            return json.load(f)
    except Exception:
        return {"chats": {}, "gbans": {}}


DB = _load()


def save_db():
    with DB_LOCK:
        tmp = cfg.DB_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(DB, f, indent=0)
        os.replace(tmp, cfg.DB_PATH)


def chat(cid) -> dict:
    with DB_LOCK:
        return DB["chats"].setdefault(str(cid), {})


def gval(cid, key, default=None):
    return chat(cid).get(key, default)


def sval(cid, key, value):
    chat(cid)[key] = value
    save_db()


def gban_add(uid, reason, by):
    DB["gbans"][str(uid)] = {"reason": reason, "by": by}
    save_db()


def gban_rm(uid):
    DB["gbans"].pop(str(uid), None)
    save_db()


# ═══════════════════════ 🤝 Hᴇʟᴘᴇʀꜱ ═══════════════════════

BOT_USER = None
ADMIN_CACHE = {}


async def bot_user(client):
    global BOT_USER
    if not BOT_USER:
        BOT_USER = await client.get_me()
    return BOT_USER


async def get_admins(client, cid, force=False):
    if not force and cid in ADMIN_CACHE and time.time() - ADMIN_CACHE[cid][0] < 600:
        return ADMIN_CACHE[cid][1]
    ids = set()
    try:
        async for m in client.get_chat_members(
            cid, filter=enums.ChatMembersFilter.ADMINISTRATORS, limit=100
        ):
            ids.add(m.user.id)
    except Exception:
        pass
    ADMIN_CACHE[cid] = (time.time(), ids)
    return ids


async def is_admin(client, cid, uid):
    if uid in cfg.OWNER_IDS:
        return True
    return uid in await get_admins(client, cid)


async def bot_admin(client, cid):
    me = await bot_user(client)
    try:
        m = await client.get_chat_member(cid, me.id)
        return m.status == enums.ChatMemberStatus.ADMINISTRATOR
    except Exception:
        return False


def mention(user):
    name = md(getattr(user, "first_name", None) or "User")
    return f"🔗 [{name}](tg://user?id={getattr(user, 'id', 0)})"


async def get_target(client, message):
    """reply / id / @username se user + reason nikalta hai 🔍"""
    args = message.command
    reply = message.reply_to_message
    if reply and reply.from_user:
        return reply.from_user, " ".join(args[1:]).strip()
    if len(args) > 1:
        tok = args[1]
        reason = " ".join(args[2:]).strip()
        if tok.lstrip("-").isdigit():
            uid = int(tok)
            try:
                u = await client.get_users(uid)
                return u, reason
            except Exception:
                return type("U", (), {"id": uid, "first_name": str(uid), "is_bot": False})(), reason
        if tok.startswith("@"):
            try:
                return await client.get_users(tok), reason
            except Exception:
                return None, None
    return None, None


TIME_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def extract_time(text):
    total, found = 0, False
    for n, u in re.findall(r"(\d+)\s*([smhdw])", (text or "").lower()):
        total += int(n) * TIME_UNITS[u]
        found = True
    return total if found and total > 0 else None


def human_time(seconds):
    seconds = int(seconds)
    out = []
    for unit, sec in (("Wᴇᴇᴋ", 604800), ("Dᴀʏ", 86400), ("Hᴏᴜʀ", 3600), ("Mɪɴᴜᴛᴇ", 60), ("Sᴇᴄᴏɴᴅ", 1)):
        if seconds >= sec:
            n, seconds = divmod(seconds, sec)
            out.append(f"{n} {unit}{'s' if n > 1 else ''}")
    return " ".join(out) or "0 Second"


async def send(client, chat_id, text, buttons=None, reply_to=None):
    return await client.send_message(
        chat_id, stylize(text), reply_markup=buttons,
        reply_to_message_id=reply_to, disable_web_page_preview=True,
    )


async def log_action(client, text):
    if cfg.LOG_CHANNEL:
        try:
            await send(client, cfg.LOG_CHANNEL, f"📡 **Lᴏɢ**\n\n{text}")
        except Exception:
            pass


# ═══════════════════════ 📦 Cᴏɴᴛᴇɴᴛ Cᴀᴘᴛᴜʀᴇ (Fɪʟᴛᴇʀꜱ/Nᴏᴛᴇꜱ/Wᴇʟᴄᴏᴍᴇ) ═══════════════════════

MEDIA_ATTRS = (
    ("photo", "photo"), ("animation", "animation"), ("video", "video"),
    ("audio", "audio"), ("voice", "voice"), ("document", "document"),
    ("sticker", "sticker"), ("video_note", "video_note"),
)


def ser_buttons(rm):
    rows = []
    if rm and getattr(rm, "inline_keyboard", None):
        for row in rm.inline_keyboard:
            r = []
            for b in row:
                d = {"text": b.text}
                if b.url:
                    d["url"] = b.url
                elif b.callback_data:
                    d["callback_data"] = b.callback_data
                r.append(d)
            if r:
                rows.append(r)
    return rows


def capture(msg):
    text = msg.text or msg.caption
    btns = ser_buttons(msg.reply_markup)
    for attr, kind in MEDIA_ATTRS:
        m = getattr(msg, attr, None)
        if m:
            return {"kind": kind, "file_id": m.file_id, "text": text, "buttons": btns}
    if text:
        return {"kind": "text", "text": text, "buttons": btns}
    return None


def rebuild_buttons(rows):
    if not rows:
        return None
    kb = []
    for row in rows:
        kb.append([
            InlineKeyboardButton(
                stylize(d["text"]),
                **({"url": d["url"]} if "url" in d else {"callback_data": d["callback_data"]}),
            ) for d in row
        ])
    return InlineKeyboardMarkup(kb)


async def send_content(client, chat_id, content, text=None, reply_to=None):
    if not content:
        return
    btns = rebuild_buttons(content.get("buttons"))
    text = text if text is not None else content.get("text")
    kind = content["kind"]
    if kind == "text":
        return await send(client, chat_id, text or "✨", btns, reply_to)
    kw = {"reply_markup": btns, "reply_to_message_id": reply_to}
    if kind != "sticker":
        kw["caption"] = stylize(text) if text else None
    try:
        return await getattr(client, f"send_{kind}")(chat_id, content["file_id"], **kw)
    except Exception:
        kw.pop("caption", None)
        kw.pop("reply_markup", None)
        return await getattr(client, f"send_{kind}")(chat_id, content["file_id"], **kw)


def format_text(t, user, chat, client):
    if not t:
        return t
    try:
        count = getattr(chat, "members_count", 0) or 0
    except Exception:
        count = 0
    repl = {
        "{first}": user.first_name or "",
        "{last}": user.last_name or "",
        "{fullname}": " ".join(x for x in [user.first_name, user.last_name] if x),
        "{username}": "@" + user.username if user.username else (user.first_name or ""),
        "{mention}": mention(user),
        "{id}": str(user.id),
        "{chatname}": chat.title or "Group",
        "{count}": str(count),
    }
    for k, v in repl.items():
        t = t.replace(k, v)
    return t


# ═══════════════════════ 🤖 Cʟɪᴇɴᴛ ═══════════════════════

app = Client(
    "managex", api_id=cfg.API_ID, api_hash=cfg.API_HASH,
    bot_token=cfg.BOT_TOKEN, workers=16,
    parse_mode=enums.ParseMode.MARKDOWN,
)

GRPCMD = filters.group

# ═══════════════════════ 🏠 Sᴛᴀʀᴛ / Hᴇʟᴘ / Aʙᴏᴜᴛ ═══════════════════════

HELP = {
    "main": (
        "✨ **Hᴇʏ! I MᴀɴᴀɢᴇX** 💎\n\n"
        "👑 Aᴅᴠᴀɴᴄᴇᴅ Gʀᴏᴜᴘ Mᴀɴᴀɢᴇᴍᴇɴᴛ Bᴏᴛ — Mᴏᴅᴇʀᴀᴛɪᴏɴ, Fɪʟᴛᴇʀꜱ, Lᴏᴄᴋꜱ,\n"
        "Wᴇʟᴄᴏᴍᴇ, Wᴀʀɴꜱ, Aɴᴛɪꜰʟᴏᴏᴅ & Tᴀɢ Aʟʟ Sᴜᴘᴇʀᴘᴏᴡᴇʀꜱ! ❤️‍🔥\n\n"
        "👇 Bᴜᴛᴛᴏɴꜱ Sᴇ Cᴀᴛᴇɢᴏʀʏ Cʜᴏᴏsᴏ ⚡"
    ),
    "admin": (
        "⚔️ **Aᴅᴍɪɴ Cᴏᴍᴍᴀɴᴅꜱ** 👑\n\n"
        "• /promote – ᴀᴅᴍɪɴ ʙᴀɴᴀᴏ ⚡\n• /demote – ᴀᴅᴍɪɴ ᴄʜᴇᴇɴ ᴏ 📉\n"
        "• /ban, /tban, /dban – ʙᴀɴ ᴍᴀᴄʜɪɴᴇ 🚫\n• /unban – ᴋʜᴏʟ ᴅᴏ 🟢\n"
        "• /kick, /dkick – ᴋɪᴄᴋ ᴏᴜᴛ 👟\n• /mute, /tmute, /dmute – ꜱɪʟᴇɴᴄᴇ 🔇\n• /unmute – ᴠᴏɪᴄᴇ ʙᴀᴄᴋ 🔊\n"
        "• /warn, /dwarn – ᴡᴀʀɴɪɴɢ ᴅᴏ ⚠️\n• /warnings, /resetwarn – ᴡᴀʀɴ ʀᴇᴄᴏʀᴅ 📋\n"
        "• /warnlimit, /warnmode – ꜱᴇᴛᴛɪɴɢꜱ ⚙️\n• /purge, /del – ᴄʟᴇᴀɴᴜᴘ ꜱᴘᴀᴀᴀᴍ 🧹\n"
        "• /pin, /unpin, /unpinall – ᴘɪɴ ᴍᴀɴᴀɢᴇʀ 📌\n• /adminlist – ᴀᴅᴍɪɴꜱ ᴋᴀ ᴅᴀʀʙᴀʀ 👑\n• /invitelink – ɪɴᴠɪᴛᴇ ʟɪɴᴋ 🔗\n• /gban, /ungban – ɢʟᴏʙᴀʟ ʙᴀɴ (ᴏᴡɴᴇʀ) 💀"
    ),
    "welcome": (
        "👋 **Wᴇʟᴄᴏᴍᴇ & Rᴜʟᴇꜱ** ✨\n\n"
        "• /setwelcome (reply) – ᴡᴇʟᴄᴏᴍᴇ ᴍꜱɢ ꜱᴇᴛ ᴋᴀʀᴏ 💐\n• /welcome on/off – ꜱᴡɪᴛᴄʜ 🔄\n"
        "• /clearwelcome – ᴅᴇʟᴇᴛᴇ ᴡᴇʟᴄᴏᴍᴇ 🗑️\n• /setgoodbye – ʙʏᴇ ᴍꜱɢ 👋\n"
        "• /goodbye on/off • /cleargoodbye 🚪\n• /cleanservice on/off – ᴊᴏɪɴ/ʟᴇᴀᴠᴇ ᴍꜱɢ ᴄʟᴇᴀʀ 🧹\n"
        "• /setrules, /rules, /clearrules – ɢʀᴏᴜᴘ ᴋᴀ ᴄᴀɴᴏɴ 📜\n\n"
        "💎 Pʟᴀᴄᴇʜᴏʟᴅᴇʀꜱ: {first} {last} {username} {mention} {id} {chatname} {count}"
    ),
    "filters": (
        "🎯 **Fɪʟᴛᴇʀꜱ & Nᴏᴛᴇꜱ** 🧠\n\n"
        "• /filter (keyword) (reply) – ᴀᴜᴛᴏ ʀᴇᴘʟʏ ꜰɪʟᴛᴇʀ ➕\n"
        "• /stop (keyword) – ꜰɪʟᴛᴇʀ ʜᴀᴛᴀᴏ ➖\n• /filters – ʟɪꜱᴛ 📃\n• /stopall – ꜱᴀʙ ʜᴀᴛᴀᴏ 💣\n\n"
        "• /save (name) (reply) – ɴᴏᴛᴇ ꜱᴀᴠᴇ 💾\n• /get (name) / #name – ɴᴏᴛᴇ ʟᴀᴏ 📖\n"
        "• /notes – ʟɪꜱᴛ 📚 • /clear (name) – ʜᴀᴛᴀᴏ 🗑️\n\n"
        "⚡ Text, Photo, Video, Gif, Sticker, Document — ꜱᴀʙ ꜱᴜᴘᴘᴏʀᴛᴇᴅ, ʙᴜᴛᴛᴏɴꜱ ꜱᴀᴛʜ!"
    ),
    "locks": (
        "🔒 **Lᴏᴄᴋꜱ & Sᴇᴄᴜʀɪᴛʏ** 🛡️\n\n"
        "• /lock (type) – ʟᴏᴄᴋ ᴍᴀʀᴏ 🔒\n• /unlock (type) – ᴜɴʟᴏᴄᴋ 🔓\n"
        "• /locks – ᴄᴏʟᴏʀꜰᴜʟ ᴛᴏɢɢʟᴇ ᴘᴀɴᴇʟ 🎛️\n\n"
        "📦 Tʏᴘᴇꜱ: all, messages, media, photo, video, gif, sticker,\n"
        "audio, voice, document, contact, game, poll, location, url,\n"
        "forward, inline, bots\n\n"
        "• /setflood N/off – ᴀɴᴛɪꜰʟᴏᴏᴅ 🌊\n• /blacklist add/rm (word) – ᴡᴏʀᴅ ʙᴀɴ 🏴"
    ),
    "mention": (
        "📣 **Mᴇɴᴛɪᴏɴ Pᴏᴡᴇʀꜱ** (Aᴅᴍɪɴ Oɴʟʏ) 🔥\n\n"
        "• /all ya /tagall (msg) – ᴘᴜʀᴇ ɢʀᴏᴜᴘ ᴛᴀɢ 💥\n"
        "• /tagadmins – ꜱɪʀꜰ ᴀᴅᴍɪɴꜱ ᴛᴀɢ 👑\n• /stopmention – ᴛᴀɢɪɴɢ ʀᴏᴋᴏ ✋\n"
        "• @admin – ʀᴇᴘᴏʀᴛ ꜱʏꜱᴛᴇᴍ 🚨"
    ),
    "misc": (
        "🛠️ **Mɪꜱᴄ** ⚙️\n\n"
        "• /settings – ɢʀᴏᴜᴘ ꜱᴇᴛᴛɪɴɢ ᴘᴀɴᴇʟ 🎛️\n• /id – ɪᴅꜱ ᴅᴇᴋʜᴏ 🪪\n"
        "• /info – ᴜꜱᴇʀ ᴘʀᴏꜰɪʟᴇ 🔍\n• /stats – ʙᴏᴛ ꜱᴛᴀᴛꜱ 📊\n"
        "• /ping – ꜱᴘᴇᴇᴅ ᴛᴇꜱᴛ 💥\n• /github – ꜱᴏᴜʀᴄᴇ ⭐"
    ),
}


def help_buttons(section="main"):
    rows = [
        (B("Admins", cb=f"help|admin", icon="⚔️"), B("Welcome", cb="help|welcome", icon="👋"), B("Filters", cb="help|filters", icon="🎯")),
        (B("Locks", cb="help|locks", icon="🔒"), B("Mention", cb="help|mention", icon="📣"), B("Misc", cb="help|misc", icon="🛠️")),
        (B("Home", cb="help|main", icon="🏠"), B("Close", cb="close", color="red")),
    ]
    return KB(*rows)


@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    me = await bot_user(client)
    uname = me.username or "managex"
    text = (
        f"✨ Hᴇʏ {mention(message.from_user)}! 👋\n\n"
        f"💎 I'ᴍ **{md(me.first_name)}** — Aᴅᴠᴀɴᴄᴇᴅ Gʀᴏᴜᴘ Mᴀɴᴀɢᴇᴍᴇɴᴛ Bᴏᴛ!\n"
        f"❤️‍🔥 Mᴏᴅᴇʀᴀᴛɪᴏɴ, Fɪʟᴛᴇʀꜱ, Lᴏᴄᴋꜱ, Wᴇʟᴄᴏᴍᴇ, Wᴀʀɴꜱ,\n"
        f"🌊 Aɴᴛɪꜰʟᴏᴏᴅ, 📣 Tᴀɢ Aʟʟ & ᴍᴜᴄʜ ᴍᴏʀᴇ...\n\n"
        f"⚡ Aᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ & ᴍᴀᴋᴇ ᴍᴏᴅᴇʀᴀᴛɪᴏɴ ꜱᴜᴘᴇʀ ᴇᴀꜱʏ! 🚀"
    )
    row1 = (B("Add Me", url=f"https://t.me/{uname}?startgroup=true", icon="➕"),
            B("Help", cb="help|main", color="blue"))
    row2 = [B("About", cb="about", color="purple"), B("Source", url=cfg.SOURCE_URL, icon="⭐")]
    if cfg.SUPPORT_CHAT:
        row2.append(B("Support", url=cfg.SUPPORT_CHAT, icon="💬"))
    await send(client, message.chat.id, text, KB(row1, tuple(row2)))


@app.on_message(filters.command("help"))
async def help_cmd(client, message):
    await send(client, message.chat.id, HELP["main"], help_buttons())


@app.on_message(filters.command("about"))
async def about_cmd(client, message):
    me = await bot_user(client)
    up = human_time(time.time() - START_TIME)
    text = (
        f"ℹ️ **Aʙᴏᴜᴛ**\n\n🤖 Nᴀᴍᴇ: {md(me.first_name)}\n"
        f"👑 Oᴡɴᴇʀ: {' '.join(f'[{i}](tg://user?id={i})' for i in cfg.OWNER_IDS) or 'Hᴜᴍᴀɴ'}\n"
        f"💠 Vᴇʀꜱɪᴏɴ: 1.0.0\n🧠 Eɴɢɪɴᴇ: Pyrogram\n"
        f"⏱️ Uᴘᴛɪᴍᴇ: {up}\n\n✨ Mᴀᴅᴇ Wɪᴛʜ ❤️‍🔥 & Pʀᴇᴍɪᴜᴍ Sᴛʏʟᴇ!"
    )
    await send(client, message.chat.id, text, KB(
        (B("Help", cb="help|main", color="blue"), B("Close", cb="close", color="red"))))


@app.on_message(filters.command("github"))
async def github_cmd(client, message):
    await send(client, message.chat.id, "⭐ **Sᴏᴜʀᴄᴇ Cᴏᴅᴇ** — Gᴀᴡᴀ Hᴏ, Sᴛᴀʀ Mᴀʀᴏ! 💎", KB(
        (B("Open Repo", url=cfg.SOURCE_URL, icon="🌐"), B("Close", cb="close", color="red"))))


# ═══════════════════════ ⚔️ Aᴅᴍɪɴ Aᴄᴛɪᴏɴꜱ ═══════════════════════

async def guard(client, message, need_bot_admin=False):
    """🛡️ permission check — returns True if allowed"""
    if not message.from_user or not await is_admin(client, message.chat.id, message.from_user.id):
        await send(client, message.chat.id, "🚫 Yᴇ Cᴏᴍᴍᴀɴᴅ Sɪʀꜰ Aᴅᴍɪɴꜱ Kᴇ Lɪʏᴇ Hᴀɪ! 👑")
        return False
    if need_bot_admin and not await bot_admin(client, message.chat.id):
        await send(client, message.chat.id, "😅 Pᴇʜʟᴇ ᴍᴜᴊʜᴇ Aᴅᴍɪɴ Bᴀɴᴀᴏ (ʀɪɢʜᴛꜱ ᴋᴇ ꜱᴀᴛʜ)! ⚠️")
        return False
    return True


async def protected(client, cid, user):
    me = await bot_user(client)
    if user.id in cfg.OWNER_IDS:
        return "Mʏ Oᴡɴᴇʀ 👑"
    if user.id == me.id:
        return "Mᴇ 😅"
    if await is_admin(client, cid, user.id):
        return "Aɴ Aᴅᴍɪɴ ⚔️"
    return None


async def punish(client, message, act):
    """act: ban/tban/kick/mute/tmute/unban/unmute"""
    cid = message.chat.id
    user, reason = await get_target(client, message)
    if not user:
        await send(client, cid, "🤔 Rᴇᴘʟʏ Kᴀʀᴏ, Uꜱᴇʀ Iᴅ Yᴀ @ᴜꜱᴇʀɴᴀᴍᴇ Dᴏ! 🔍")
        return
    who = await protected(client, cid, user)
    if who:
        await send(client, cid, f"🚫 Cᴀɴ'ᴛ Tᴏᴜᴄʜ {mention(user)} — Hᴇ Iꜱ {who}!")
        return
    reason = reason or "Nᴏ Rᴇᴀꜱᴏɴ"
    temp = extract_time(reason.split()[0]) if reason else None
    dur = ""
    try:
        if act == "ban":
            await client.ban_chat_member(cid, user.id)
            dur = "Fᴏʀᴇᴠᴇʀ 💀"
        elif act == "tban" and temp:
            await client.ban_chat_member(cid, user.id, until_date=datetime.now() + timedelta(seconds=temp))
            dur = human_time(temp)
        elif act == "kick":
            await client.ban_chat_member(cid, user.id)
            await client.unban_chat_member(cid, user.id)
        elif act == "mute":
            await client.restrict_chat_member(cid, user.id, ChatPermissions())
            dur = "Fᴏʀᴇᴠᴇʀ 🔇"
        elif act == "tmute" and temp:
            await client.restrict_chat_member(
                cid, user.id, ChatPermissions(), until_date=datetime.now() + timedelta(seconds=temp))
            dur = human_time(temp)
        elif act == "unban":
            await client.unban_chat_member(cid, user.id)
        elif act == "unmute":
            await client.restrict_chat_member(cid, user.id, ChatPermissions(
                can_send_messages=True, can_send_media_messages=True,
                can_send_other_messages=True, can_add_web_page_previews=True,
                can_send_polls=True, can_invite_users=True))
        else:
            return
    except RPCError as e:
        await send(client, cid, f"🚫 Fᴀɪʟᴇᴅ! Mᴜᴊʜᴇ Fᴜʟʟ Aᴅᴍɪɴ Rɪɢʜᴛꜱ Dᴏ — `{type(e).__name__}` ⚠️")
        return

    icon = {"ban": "🚫", "tban": "⏳", "kick": "👟", "mute": "🔇", "tmute": "⏳", "unban": "🟢", "unmute": "🔊"}[act]
    actn = {"ban": "Bᴀɴɴᴇᴅ", "tban": "Bᴀɴɴᴇᴅ", "kick": "Kɪᴄᴋᴇᴅ", "mute": "Mᴜᴛᴇᴅ",
            "tmute": "Mᴜᴛᴇᴅ", "unban": "Uɴʙᴀɴɴᴇᴅ", "unmute": "Uɴᴍᴜᴛᴇᴅ"}[act]
    text = (f"{icon} **{actn}** {mention(user)} ✅\n"
            f"📝 Rᴇᴀꜱᴏɴ: {md(reason) if act not in ('unban', 'unmute') else '—'}"
            + (f"\n⏰ Dᴜʀᴀᴛɪᴏɴ: {dur}" if dur else ""))
    btns = None
    if act in ("ban", "tban"):
        btns = KB((B("Unban", cb=f"unban|{cid}|{user.id}", color="green"),))
    elif act in ("mute", "tmute"):
        btns = KB((B("Unmute", cb=f"unmute|{cid}|{user.id}", color="green"),))
    await send(client, cid, text, btns)
    await log_action(client, f"{icon} {act.upper()} → {mention(user)} ({user.id}) in {message.chat.title} | {reason}")


@app.on_message(filters.command(["ban", "dban", "tban"]) & GRPCMD)
async def ban_cmd(client, message):
    if not await guard(client, message, need_bot_admin=True):
        return
    if message.command[0] == "dban" and message.reply_to_message:
        try:
            await message.reply_to_message.delete()
        except Exception:
            pass
    await punish(client, message, "tban" if message.command[0] == "tban" else "ban")


@app.on_message(filters.command("unban") & GRPCMD)
async def unban_cmd(client, message):
    if not await guard(client, message, need_bot_admin=True):
        return
    await punish(client, message, "unban")


@app.on_message(filters.command(["kick", "dkick"]) & GRPCMD)
async def kick_cmd(client, message):
    if not await guard(client, message, need_bot_admin=True):
        return
    if message.command[0] == "dkick" and message.reply_to_message:
        try:
            await message.reply_to_message.delete()
        except Exception:
            pass
    await punish(client, message, "kick")


@app.on_message(filters.command(["mute", "tmute", "dmute"]) & GRPCMD)
async def mute_cmd(client, message):
    if not await guard(client, message, need_bot_admin=True):
        return
    if message.command[0] == "dmute" and message.reply_to_message:
        try:
            await message.reply_to_message.delete()
        except Exception:
            pass
    await punish(client, message, "tmute" if message.command[0] == "tmute" else "mute")


@app.on_message(filters.command("unmute") & GRPCMD)
async def unmute_cmd(client, message):
    if not await guard(client, message, need_bot_admin=True):
        return
    await punish(client, message, "unmute")


@app.on_message(filters.command(["promote", "dpromote"]) & GRPCMD)
async def promote_cmd(client, message):
    if not await guard(client, message, need_bot_admin=True):
        return
    cid = message.chat.id
    user, _ = await get_target(client, message)
    if not user:
        return await send(client, cid, "🤔 Rᴇᴘʟʏ Kᴀʀᴏ Yᴀ Uꜱᴇʀ Iᴅ Dᴏ! 🔍")
    if message.command[0] == "promote":
        try:
            await client.promote_chat_member(cid, user.id, privileges=ChatPrivileges(
                can_manage_chat=True, can_delete_messages=True, can_invite_users=True,
                can_pin_messages=True, can_manage_video_chats=True))
            await send(client, cid, f"⚔️ {mention(user)} Iꜱ Nᴏᴡ Aɴ Aᴅᴍɪɴ! 👑✨")
        except RPCError:
            await send(client, cid, "🚫 Pʀᴏᴍᴏᴛᴇ Fᴀɪʟᴇᴅ — Mᴜᴊʜᴇ Pʀᴏᴍᴏᴛᴇ Rɪɢʜᴛ Dᴏ! ⚠️")
    else:
        try:
            await client.promote_chat_member(cid, user.id, privileges=ChatPrivileges())
            await send(client, cid, f"📉 {mention(user)} Iꜱ Nᴏᴡ Jᴜꜱᴛ A Mᴇᴍʙᴇʀ! 😌")
        except RPCError:
            await send(client, cid, "🚫 Dᴇᴍᴏᴛᴇ Fᴀɪʟᴇᴅ! ⚠️")


@app.on_message(filters.command("demote") & GRPCMD)
async def demote_cmd(client, message):
    message.command = ["dpromote"] + message.command[1:]
    await promote_cmd(client, message)


@app.on_message(filters.command(["adminlist", "admins"]) & GRPCMD)
async def adminlist_cmd(client, message):
    cid = message.chat.id
    out = [f"👑 **Aᴅᴍɪɴꜱ — {md(message.chat.title)}**\n"]
    try:
        async for m in client.get_chat_members(cid, filter=enums.ChatMembersFilter.ADMINISTRATORS, limit=100):
            badge = "👑" if m.status == enums.ChatMemberStatus.OWNER else "⚡"
            out.append(f"{badge} {mention(m.user)}")
    except Exception:
        return await send(client, cid, "🚫 Cᴏᴜʟᴅɴ'ᴛ Fᴇᴛᴄʜ Aᴅᴍɪɴꜱ! ⚠️")
    await send(client, cid, "\n".join(out) or "👑 Nᴏ Aᴅᴍɪɴꜱ Fᴏᴜɴᴅ")


@app.on_message(filters.command("admincache") & GRPCMD)
async def admincache_cmd(client, message):
    await get_admins(client, message.chat.id, force=True)
    await send(client, message.chat.id, "♻️ Aᴅᴍɪɴ Cᴀᴄʜᴇ Rᴇꜰʀᴇꜱʜᴇᴅ! ✅")


@app.on_message(filters.command("invitelink") & GRPCMD)
async def invitelink_cmd(client, message):
    if not await guard(client, message, need_bot_admin=True):
        return
    try:
        chat = await client.get_chat(message.chat.id)
        link = chat.invite_link or (await client.create_chat_invite_link(message.chat.id)).invite_link
        await send(client, message.chat.id, f"🔗 **Iɴᴠɪᴛᴇ Lɪɴᴋ:** {link}")
    except Exception:
        await send(client, message.chat.id, "🚫 Iɴᴠɪᴛᴇ Lɪɴᴋ Nᴀʜɪ ʙᴀɴᴀ ꜱᴀᴋᴀ! ⚠️")


# ═══════════════════════ ⚠️ Wᴀʀɴ Sʏꜱᴛᴇᴍ ═══════════════════════

async def do_warn(client, message, delete=False):
    cid = message.chat.id
    user, reason = await get_target(client, message)
    if not user:
        return await send(client, cid, "🤔 Rᴇᴘʟʏ Kᴀʀᴏ Yᴀ Uꜱᴇʀ Iᴅ Dᴏ! 🔍")
    if await protected(client, cid, user):
        return await send(client, cid, "🚫 Aᴅᴍɪɴꜱ Kᴏ Wᴀʀɴ Nᴀʜɪ! ⚔️")
    if delete and message.reply_to_message:
        try:
            await message.reply_to_message.delete()
        except Exception:
            pass
    reason = reason or "Nᴏ Rᴇᴀꜱᴏɴ"
    warns = gval(cid, "warns", {}) or {}
    lst = warns.setdefault(str(user.id), [])
    lst.append(reason)
    sval(cid, "warns", warns)
    limit = gval(cid, "warnlimit", cfg.WARN_LIMIT)
    count = len(lst)
    await send(client, cid,
               f"⚠️ {mention(user)} Wᴀʀɴᴇᴅ! [{count}/{limit}]\n📝 Rᴇᴀꜱᴏɴ: {md(reason)}",
               KB((B(f"Remove Warn", cb=f"rmwarn|{cid}|{user.id}", color="green"),)))
    if count >= limit:
        mode = gval(cid, "warnmode", "kick")
        lst = lst[:-1]
        warns[str(user.id)] = lst
        sval(cid, "warns", warns)
        fake = type("M", (), {"chat": message.chat, "command": [mode, str(user.id), "Max warns reached"], "reply_to_message": None, "from_user": message.from_user})()
        if mode in ("kick", "ban"):
            await punish(client, fake, mode)
        elif mode == "mute":
            await punish(client, fake, "mute")
        if not lst:
            warns.pop(str(user.id), None)
            sval(cid, "warns", warns)


@app.on_message(filters.command(["warn", "dwarn"]) & GRPCMD)
async def warn_cmd(client, message):
    if not await guard(client, message, need_bot_admin=True):
        return
    await do_warn(client, message, delete=message.command[0] == "dwarn")


@app.on_message(filters.command(["warnings", "warns"]) & GRPCMD)
async def warnings_cmd(client, message):
    cid = message.chat.id
    user, _ = await get_target(client, message)
    user = user or message.from_user
    warns = (gval(cid, "warns", {}) or {}).get(str(user.id), [])
    if not warns:
        return await send(client, cid, f"✅ {mention(user)} Kᴀ Pᴀᴛᴀ Sᴀꜰ Hᴀɪ — 0 Wᴀʀɴꜱ! 🧼")
    out = [f"⚠️ **Wᴀʀɴꜱ — {mention(user)}** [{len(warns)}]"]
    for i, w in enumerate(warns, 1):
        out.append(f"{'️'}{i}️⃣ {md(w)}")
    await send(client, cid, "\n".join(out))


@app.on_message(filters.command(["resetwarn", "resetwarnings", "resetwarns"]) & GRPCMD)
async def resetwarn_cmd(client, message):
    if not await guard(client, message):
        return
    cid = message.chat.id
    user, _ = await get_target(client, message)
    user = user or message.from_user
    warns = gval(cid, "warns", {}) or {}
    warns.pop(str(user.id), None)
    sval(cid, "warns", warns)
    await send(client, cid, f"🧼 Wᴀʀɴꜱ Cʟᴇᴀɴᴇᴅ Fᴏʀ {mention(user)}! ✅")


@app.on_message(filters.command("warnlimit") & GRPCMD)
async def warnlimit_cmd(client, message):
    if not await guard(client, message):
        return
    try:
        n = int(message.command[1])
        assert 1 <= n <= 10
        sval(message.chat.id, "warnlimit", n)
        await send(client, message.chat.id, f"⚙️ Wᴀʀɴ Lɪᴍɪᴛ Sᴇᴛ → {n} ⚠️")
    except Exception:
        await send(client, message.chat.id, "💡 /warnlimit 3 (1-10)")


@app.on_message(filters.command("warnmode") & GRPCMD)
async def warnmode_cmd(client, message):
    if not await guard(client, message):
        return
    if len(message.command) > 1 and message.command[1] in ("kick", "ban", "mute"):
        sval(message.chat.id, "warnmode", message.command[1])
        await send(client, message.chat.id, f"⚙️ Wᴀʀɴ Aᴄᴛɪᴏɴ → {message.command[1].title()} {'' if message.command[1] != 'kick' else '👟'}")
    else:
        await send(client, message.chat.id, "💡 /warnmode kick/ban/mute")


# ═══════════════════════ 🧹 Pᴜʀɢᴇ / Pɪɴ ═══════════════════════

@app.on_message(filters.command("purge") & GRPCMD)
async def purge_cmd(client, message):
    if not await guard(client, message, need_bot_admin=True):
        return
    reply = message.reply_to_message
    if not reply:
        return await send(client, message.chat.id, "🤔 Kɪꜱ Mᴇꜱꜱᴀɢᴇ Sᴇ Pᴜʀɢᴇ Kᴀʀᴜ? Rᴇᴘʟʏ Mᴀʀᴏ! 🔍")
    cid, count = message.chat.id, 0
    for end in range(message.id, reply.id - 1, -100):
        ids = list(range(max(reply.id, end - 99), end + 1))
        try:
            await client.delete_messages(cid, ids, revoke=True)
            count += len(ids)
        except Exception:
            pass
        await asyncio.sleep(0.4)
    done = await send(client, cid, f"🧹 Pᴜʀɢᴇᴅ {count} Mᴇꜱꜱᴀɢᴇꜱ! ✨")
    await asyncio.sleep(4)
    try:
        await done.delete()
    except Exception:
        pass


@app.on_message(filters.command("del") & GRPCMD)
async def del_cmd(client, message):
    if not await guard(client, message, need_bot_admin=True):
        return
    reply = message.reply_to_message
    if not reply:
        return await send(client, message.chat.id, "🤔 Kᴀʜɪɴ Rᴇᴘʟʏ Tᴏ Mᴀʀᴏ! 🔍")
    try:
        await client.delete_messages(message.chat.id, [reply.id, message.id], revoke=True)
    except Exception:
        pass


@app.on_message(filters.command("pin") & GRPCMD)
async def pin_cmd(client, message):
    if not await guard(client, message, need_bot_admin=True):
        return
    reply = message.reply_to_message
    if not reply:
        return await send(client, message.chat.id, "🤔 Kᴀʜɪɴ Rᴇᴘʟʏ Tᴏ Mᴀʀᴏ! 🔍")
    try:
        await client.pin_chat_message(message.chat.id, reply.id, both_sides=True)
        await send(client, message.chat.id, "📌 Pɪɴɴᴇᴅ! ✅")
    except Exception:
        await send(client, message.chat.id, "🚫 Pɪɴ Fᴀɪʟᴇᴅ! ⚠️")


@app.on_message(filters.command(["unpinall"]) & GRPCMD)
async def unpinall_cmd(client, message):
    if not await guard(client, message, need_bot_admin=True):
        return
    await send(client, message.chat.id, "💣 Sᴀʀᴇ Pɪɴꜱ Hᴀᴛᴀᴜɴ? Yᴇ Wᴀᴘɪꜱ Nᴀʜɪ Hᴏɴɢᴇ!", KB(
        (B("Yes, Clear All", cb=f"unpinall|{message.chat.id}", color="red"),
         B("Cancel", cb="close", color="green"))))


# ═══════════════════════ 🔒 Lᴏᴄᴋꜱ ═══════════════════════

LOCK_TYPES = {
    "all": "🌐", "messages": "💬", "media": "🖼️", "photo": "📷", "video": "🎥",
    "gif": "🎞️", "sticker": "🧷", "audio": "🎵", "voice": "🎤", "document": "📁",
    "contact": "📞", "game": "🎮", "poll": "📊", "location": "📍", "url": "🔗",
    "forward": "↪️", "inline": "⚡", "bots": "🤖",
}
MEDIA_KINDS = {"photo", "video", "gif", "sticker", "audio", "voice", "document"}


def detect_kind(m):
    if m.photo: return "photo"
    if m.animation: return "gif"
    if m.sticker: return "sticker"
    if m.video: return "video"
    if m.video_note: return "video"
    if m.audio: return "audio"
    if m.voice: return "voice"
    if m.document: return "document"
    if m.contact: return "contact"
    if m.game or m.dice: return "game"
    if m.poll: return "poll"
    if m.location or m.venue: return "location"
    return None


@app.on_message(filters.command("lock") & GRPCMD)
async def lock_cmd(client, message):
    if not await guard(client, message, need_bot_admin=True):
        return
    typ = message.command[1].lower() if len(message.command) > 1 else None
    if typ not in LOCK_TYPES:
        return await send(client, message.chat.id, f"💡 /lock (type)\n📦 {' | '.join(LOCK_TYPES)}")
    locks = gval(message.chat.id, "locks", {}) or {}
    locks[typ] = True
    sval(message.chat.id, "locks", locks)
    await send(client, message.chat.id, f"🔒 {LOCK_TYPES[typ]} {typ.title()} Lᴏᴄᴋᴇᴅ! 🛡️")


@app.on_message(filters.command("unlock") & GRPCMD)
async def unlock_cmd(client, message):
    if not await guard(client, message, need_bot_admin=True):
        return
    typ = message.command[1].lower() if len(message.command) > 1 else None
    if typ not in LOCK_TYPES:
        return await send(client, message.chat.id, f"💡 /unlock (type)\n📦 {' | '.join(LOCK_TYPES)}")
    locks = gval(message.chat.id, "locks", {}) or {}
    locks.pop(typ, None)
    sval(message.chat.id, "locks", locks)
    await send(client, message.chat.id, f"🔓 {LOCK_TYPES[typ]} {typ.title()} Uɴʟᴏᴄᴋᴇᴅ! 🎉")


def locks_panel(cid):
    locks = gval(cid, "locks", {}) or {}
    rows = []
    types = list(LOCK_TYPES.items())
    for i in range(0, len(types), 3):
        row = []
        for t, ic in types[i:i + 3]:
            on = locks.get(t)
            row.append(B(t.title(), cb=f"lock|{cid}|{t}", icon=("🔒" if on else "🔓")))
        rows.append(tuple(row))
    rows.append((B("Close", cb="close", color="red"),))
    return KB(*rows)


@app.on_message(filters.command("locks") & GRPCMD)
async def locks_cmd(client, message):
    if not await guard(client, message):
        return
    await send(client, message.chat.id,
               "🎛️ **Lᴏᴄᴋ Pᴀɴᴇʟ** — Bᴜᴛᴛᴏɴ Pᴇ Dᴀʙᴏ, Oɴ/Oꜰꜰ Hᴏ Jᴀʏᴇɢᴀ ⚡\n🔒 = Lᴏᴄᴋᴇᴅ • 🔓 = Oᴘᴇɴ",
               locks_panel(message.chat.id))


@app.on_message(filters.group & ~filters.service, group=2)
async def lock_watcher(client, message):
    """🛡️ locked cheezein delete karta hai"""
    cid = message.chat.id
    locks = gval(cid, "locks", {}) or {}
    if not locks:
        return
    user = message.from_user
    if user and await is_admin(client, cid, user.id):
        return
    if message.sender_chat and message.sender_chat.id == cid:
        return
    kind = detect_kind(message)
    text = message.text or message.caption or ""
    hit = locks.get("all")
    if not hit and kind and locks.get(kind):
        hit = True
    if not hit and locks.get("messages") and text and not kind:
        hit = True
    if not hit and locks.get("media") and kind in MEDIA_KINDS:
        hit = True
    if not hit and locks.get("url"):
        ents = list(message.entities or []) + list(message.caption_entities or [])
        if getattr(message, "web_page", None) or any(e.type in ("url", "text_link") for e in ents):
            hit = True
    if not hit and locks.get("forward") and (message.forward_from or message.forward_from_chat):
        hit = True
    if not hit and locks.get("inline") and message.via_bot:
        hit = True
    if not hit and locks.get("bots") and message.new_chat_members:
        if any(u.is_bot for u in message.new_chat_members):
            hit = True
    if hit:
        try:
            await message.delete()
        except Exception:
            pass


# ═══════════════════════ 👋 Wᴇʟᴄᴏᴍᴇ / Gᴏᴏᴅʙʏᴇ ═══════════════════════

@app.on_message(filters.command(["setwelcome", "welcome", "clearwelcome"]) & GRPCMD)
async def welcome_cmd(client, message):
    cid = message.chat.id
    cmd = message.command[0]
    w = gval(cid, "welcome", {}) or {}
    if cmd == "setwelcome":
        content = capture(message.reply_to_message) if message.reply_to_message else (
            {"kind": "text", "text": " ".join(message.command[1:]), "buttons": []} if len(message.command) > 1 else None)
        if not content or not content.get("text") and content["kind"] == "text":
            return await send(client, cid, "💡 Kɪꜱɪ Mᴇꜱꜱᴀɢᴇ Pᴇ /setwelcome Rᴇᴘʟʏ Mᴀʀᴏ (ᴏʀ ᴛᴇxᴛ ʟɪᴋʜᴏ)! ✍️")
        w = {"on": True, "content": content}
        sval(cid, "welcome", w)
        await send(client, cid, "💐 Wᴇʟᴄᴏᴍᴇ Mᴇꜱꜱᴀɢᴇ Sᴀᴠᴇᴅ! ✅")
    elif cmd == "clearwelcome":
        sval(cid, "welcome", {})
        await send(client, cid, "🗑️ Wᴇʟᴄᴏᴍᴇ Mᴇꜱꜱᴀɢᴇ Hᴀᴛᴀʏᴀ! ✅")
    else:
        arg = message.command[1].lower() if len(message.command) > 1 else None
        if arg in ("on", "off"):
            w["on"] = arg == "on"
            sval(cid, "welcome", w)
            return await send(client, cid, f"{'🟢' if arg == 'on' else '🔴'} Wᴇʟᴄᴏᴍᴇ {'Oɴ' if arg == 'on' else 'Oꜰꜰ'}!")
        status = "🟢 Oɴ" if w.get("on") and w.get("content") else "🔴 Oꜰꜰ"
        await send(client, cid, f"👋 Wᴇʟᴄᴏᴍᴇ: {status}\n💡 /setwelcome (reply) • /welcome on/off")


@app.on_message(filters.command(["setgoodbye", "goodbye", "cleargoodbye"]) & GRPCMD)
async def goodbye_cmd(client, message):
    cid = message.chat.id
    cmd = message.command[0]
    g = gval(cid, "goodbye", {}) or {}
    if cmd == "setgoodbye":
        content = capture(message.reply_to_message) if message.reply_to_message else (
            {"kind": "text", "text": " ".join(message.command[1:]), "buttons": []} if len(message.command) > 1 else None)
        if not content or not content.get("text") and content["kind"] == "text":
            return await send(client, cid, "💡 Kɪꜱɪ Mᴇꜱꜱᴀɢᴇ Pᴇ /setgoodbye Rᴇᴘʟʏ Mᴀʀᴏ! ✍️")
        g = {"on": True, "content": content}
        sval(cid, "goodbye", g)
        await send(client, cid, "🚪 Gᴏᴏᴅʙʏᴇ Mᴇꜱꜱᴀɢᴇ Sᴀᴠᴇᴅ! ✅")
    elif cmd == "cleargoodbye":
        sval(cid, "goodbye", {})
        await send(client, cid, "🗑️ Gᴏᴏᴅʙʏᴇ Mᴇꜱꜱᴀɢᴇ Hᴀᴛᴀʏᴀ! ✅")
    else:
        arg = message.command[1].lower() if len(message.command) > 1 else None
        if arg in ("on", "off"):
            g["on"] = arg == "on"
            sval(cid, "goodbye", g)
            return await send(client, cid, f"{'🟢' if arg == 'on' else '🔴'} Gᴏᴏᴅʙʏᴇ {'Oɴ' if arg == 'on' else 'Oꜰꜰ'}!")
        status = "🟢 Oɴ" if g.get("on") and g.get("content") else "🔴 Oꜰꜰ"
        await send(client, cid, f"👋 Gᴏᴏᴅʙʏᴇ: {status}\n💡 /setgoodbye (reply) • /goodbye on/off")


@app.on_message(filters.command("cleanservice") & GRPCMD)
async def cleanservice_cmd(client, message):
    if not await guard(client, message):
        return
    arg = message.command[1].lower() if len(message.command) > 1 else None
    if arg in ("on", "off"):
        sval(message.chat.id, "cleanservice", arg == "on")
        await send(client, message.chat.id, f"🧹 Cʟᴇᴀɴ Sᴇʀᴠɪᴄᴇ {'🟢 Oɴ' if arg == 'on' else '🔴 Oꜰꜰ'}!")
    else:
        cur = gval(message.chat.id, "cleanservice", False)
        await send(client, message.chat.id, f"🧹 Cʟᴇᴀɴ Sᴇʀᴠɪᴄᴇ: {'🟢 Oɴ' if cur else '🔴 Oꜰꜰ'}\n💡 /cleanservice on/off")


DEFAULT_WELCOME = "👋 Hey {mention}, welcome to {chatname}! ✨\n💫 We are now {count} members strong!"
DEFAULT_GOODBYE = "🚪 {first} left the group... 👋"


@app.on_message(filters.new_chat_members & filters.group, group=0)
async def greet(client, message):
    cid = message.chat.id
    me = (await bot_user(client)).id
    for member in message.new_chat_members:
        if member.id == me:
            await send(client, cid,
                       "✨ **Tʜᴀɴᴋꜱ Fᴏʀ Aᴅᴅɪɴɢ Mᴇ!** 🎉\n👑 Mᴇɴᴛɪᴏɴ Mᴇ Aꜱ Aᴅᴍɪɴ, Pʜɪʀ /help Dᴀʙᴀᴏ ⚡",
                       help_buttons())
            continue
        if str(member.id) in DB["gbans"]:
            try:
                await client.ban_chat_member(cid, member.id)
                await send(client, cid, f"💀 {mention(member)} Iꜱ Gʟᴏʙᴀʟʟʏ Bᴀɴɴᴇᴅ — Kɪᴄᴋᴇᴅ! 🚫")
            except Exception:
                pass
    w = gval(cid, "welcome", {}) or {}
    if w.get("on") and w.get("content"):
        for member in message.new_chat_members:
            if member.id == me:
                continue
            chat = await client.get_chat(cid)
            text = format_text(w["content"].get("text") or DEFAULT_WELCOME, member, chat, client)
            await send_content(client, cid, w["content"], text=text)
    if gval(cid, "cleanservice", False):
        try:
            await message.delete()
        except Exception:
            pass


@app.on_message(filters.left_chat_member & filters.group, group=0)
async def bye(client, message):
    cid = message.chat.id
    me = (await bot_user(client)).id
    g = gval(cid, "goodbye", {}) or {}
    user = message.left_chat_member
    if user and user.id != me and g.get("on") and g.get("content"):
        text = format_text(g["content"].get("text") or DEFAULT_GOODBYE, user, message.chat, client)
        await send_content(client, cid, g["content"], text=text)
    if gval(cid, "cleanservice", False):
        try:
            await message.delete()
        except Exception:
            pass


# ═══════════════════════ 🎯 Fɪʟᴛᴇʀꜱ / Nᴏᴛᴇꜱ / Rᴜʟᴇꜱ ═══════════════════════

@app.on_message(filters.command("filter") & GRPCMD)
async def filter_cmd(client, message):
    if not await guard(client, message):
        return
    args = message.command
    if len(args) < 2:
        return await send(client, message.chat.id, "💡 /filter (keyword) — reply ke saath! ⚡")
    keys = [k.lower() for k in args[1:6]]
    if message.reply_to_message:
        content = capture(message.reply_to_message)
    else:
        content = {"kind": "text", "text": message.text.split(None, 2)[2] if len(args) > 2 else None, "buttons": []}
        content["text"] = content["text"] or args[1]
    if not content:
        return await send(client, message.chat.id, "🤔 Kᴜᴄʜ Cᴀᴘᴛᴜʀᴇ Nᴀʜɪ Hᴜᴀ! ⚠️")
    f = gval(message.chat.id, "filters", {}) or {}
    for k in keys:
        f[k] = content
    sval(message.chat.id, "filters", f)
    await send(client, message.chat.id, f"🎯 Fɪʟᴛᴇʀꜱ Aᴅᴅᴇᴅ: {', '.join('`' + k + '`' for k in keys)} ✅")


@app.on_message(filters.command(["stop", "removefilter"]) & GRPCMD)
async def stop_filter_cmd(client, message):
    if not await guard(client, message):
        return
    if len(message.command) < 2:
        return await send(client, message.chat.id, "💡 /stop (keyword) 🎯")
    f = gval(message.chat.id, "filters", {}) or {}
    k = message.command[1].lower()
    if k in f:
        f.pop(k)
        sval(message.chat.id, "filters", f)
        await send(client, message.chat.id, f"🗑️ Fɪʟᴛᴇʀ `{k}` Hᴀᴛᴀʏᴀ! ✅")
    else:
        await send(client, message.chat.id, "🤔 Yᴇ Fɪʟᴛᴇʀ Hᴀɪ Hɪ Nᴀʜɪ! 😅")


@app.on_message(filters.command("filters") & GRPCMD)
async def filters_list_cmd(client, message):
    f = gval(message.chat.id, "filters", {}) or {}
    if not f:
        return await send(client, message.chat.id, "📭 Kᴏɪ Fɪʟᴛᴇʀ Nᴀʜɪ — /filter ꜱᴇ ʙᴀɴᴀᴏ! 🎯")
    await send(client, message.chat.id,
               "🎯 **Fɪʟᴛᴇʀꜱ:**\n" + "\n".join(f"• `{k}`" for k in f),
               KB((B("Clear All", cb=f"stopall|{message.chat.id}", color="red"),)))


@app.on_message(filters.command("stopall") & GRPCMD)
async def stopall_cmd(client, message):
    if not await guard(client, message):
        return
    f = gval(message.chat.id, "filters", {}) or {}
    if not f:
        return await send(client, message.chat.id, "📭 Kᴏɪ Fɪʟᴛᴇʀ Hᴀɪ Hɪ Nᴀʜɪ! 😅")
    await send(client, message.chat.id, "💣 Sᴀʙ ꜰɪʟᴛᴇʀꜱ Hᴀᴛᴀᴜɴ? Cᴏɴꜰɪʀᴍ Kᴀʀᴏ!", KB(
        (B("Yes, Nuke Em", cb=f"stopall|{message.chat.id}", color="red"),
         B("Cancel", cb="close", color="green"))))


@app.on_message(filters.command("save") & GRPCMD)
async def save_note_cmd(client, message):
    if not await guard(client, message):
        return
    args = message.command
    if len(args) < 2:
        return await send(client, message.chat.id, "💡 /save (notename) — reply ke saath! 💾")
    name = args[1].lower().lstrip("#")
    if message.reply_to_message:
        content = capture(message.reply_to_message)
    else:
        rest = message.text.split(None, 2)[2] if len(args) > 2 else name
        content = {"kind": "text", "text": rest, "buttons": []}
    n = gval(message.chat.id, "notes", {}) or {}
    n[name] = content
    sval(message.chat.id, "notes", n)
    await send(client, message.chat.id, f"💾 Nᴏᴛᴇ `#{name}` Sᴀᴠᴇᴅ! ✅")


@app.on_message(filters.command(["get", "#"]) & GRPCMD)
async def get_note_cmd(client, message):
    if len(message.command) < 2:
        return
    name = message.command[1].lower().lstrip("#")
    n = gval(message.chat.id, "notes", {}) or {}
    if name in n:
        await send_content(client, message.chat.id, n[name])


@app.on_message(filters.command("notes") & GRPCMD)
async def notes_cmd(client, message):
    n = gval(message.chat.id, "notes", {}) or {}
    if not n:
        return await send(client, message.chat.id, "📭 Kᴏɪ Nᴏᴛᴇ Nᴀʜɪ — /save ꜱᴇ ʙᴀɴᴀᴏ! 💾")
    await send(client, message.chat.id, "📚 **Nᴏᴛᴇꜱ:**\n" + "\n".join(f"• #{k}" for k in n))


@app.on_message(filters.command("clear") & GRPCMD)
async def clear_note_cmd(client, message):
    if not await guard(client, message):
        return
    if len(message.command) < 2:
        return await send(client, message.chat.id, "💡 /clear (notename) 🗑️")
    n = gval(message.chat.id, "notes", {}) or {}
    name = message.command[1].lower().lstrip("#")
    if name in n:
        n.pop(name)
        sval(message.chat.id, "notes", n)
        await send(client, message.chat.id, f"🗑️ Nᴏᴛᴇ `#{name}` Hᴀᴛᴀʏᴀ! ✅")
    else:
        await send(client, message.chat.id, "🤔 Yᴇ Nᴏᴛᴇ Hᴀɪ Hɪ Nᴀʜɪ! 😅")


@app.on_message(filters.command(["setrules", "clearrules", "rules"]) & GRPCMD)
async def rules_cmd(client, message):
    cid = message.chat.id
    cmd = message.command[0]
    if cmd == "setrules":
        if not await guard(client, message):
            return
        text = (message.reply_to_message.text if message.reply_to_message
                else message.text.split(None, 1)[1] if len(message.command) > 1 else None)
        if not text:
            return await send(client, cid, "💡 /setrules (text) ya reply! 📜")
        sval(cid, "rules", text)
        await send(client, cid, "📜 Rᴜʟᴇꜱ Sᴀᴠᴇᴅ! ✅")
    elif cmd == "clearrules":
        if not await guard(client, message):
            return
        sval(cid, "rules", None)
        await send(client, cid, "🗑️ Rᴜʟᴇꜱ Hᴀᴛᴀʏᴇ! ✅")
    else:
        r = gval(cid, "rules")
        if not r:
            return await send(client, cid, "📭 Rᴜʟᴇꜱ Sᴇᴛ Nᴀʜɪ Hᴀɪɴ! 📜")
        await send(client, cid, "📜 **Gʀᴏᴜᴘ Rᴜʟᴇꜱ**", KB((B("View Rules", cb=f"rules|{cid}", icon="📖"),)))


# ═══════════════════════ 🏴 Bʟᴀᴄᴋʟɪꜱᴛ + 🌊 Aɴᴛɪꜰʟᴏᴏᴅ + 💀 GBAN ═══════════════════════

@app.on_message(filters.command("blacklist") & GRPCMD)
async def blacklist_cmd(client, message):
    if not await guard(client, message):
        return
    args = message.command
    bl = gval(message.chat.id, "blacklist", []) or []
    if len(args) >= 3 and args[1].lower() == "add":
        for w in args[2:]:
            if w.lower() not in bl:
                bl.append(w.lower())
        sval(message.chat.id, "blacklist", bl)
        await send(client, message.chat.id, f"🏴 Bʟᴀᴄᴋʟɪꜱᴛᴇᴅ: {', '.join('`' + w + '`' for w in args[2:])} ✅")
    elif len(args) >= 3 and args[1].lower() == "rm":
        bl = [w for w in bl if w not in [x.lower() for x in args[2:]]]
        sval(message.chat.id, "blacklist", bl)
        await send(client, message.chat.id, "🧼 Rᴇᴍᴏᴠᴇᴅ Fʀᴏᴍ Bʟᴀᴄᴋʟɪꜱᴛ! ✅")
    else:
        await send(client, message.chat.id,
                   "🏴 **Bʟᴀᴄᴋʟɪꜱᴛᴇᴅ Wᴏʀᴅꜱ:**\n" + ("\n".join(f"• `{w}`" for w in bl) if bl else "📭 Eᴍᴘᴛʏ!")
                   + "\n\n💡 /blacklist add|rm (word)")


@app.on_message(filters.command("setflood") & GRPCMD)
async def setflood_cmd(client, message):
    if not await guard(client, message):
        return
    arg = message.command[1].lower() if len(message.command) > 1 else None
    if arg in ("off", "0"):
        sval(message.chat.id, "flood", 0)
        await send(client, message.chat.id, "🔴 Aɴᴛɪꜰʟᴏᴏᴅ Oꜰꜰ!")
    elif arg and arg.isdigit() and 3 <= int(arg) <= 50:
        sval(message.chat.id, "flood", int(arg))
        await send(client, message.chat.id, f"🌊 Aɴᴛɪꜰʟᴏᴏᴅ Oɴ — Lɪᴍɪᴛ: {arg} Mꜱɢꜱ/{cfg.FLOOD_WINDOW}s ⚡")
    else:
        cur = gval(message.chat.id, "flood", cfg.FLOOD_LIMIT)
        await send(client, message.chat.id, f"🌊 Cᴜʀʀᴇɴᴛ Lɪᴍɪᴛ: {cur or 'Off'}\n💡 /setflood 10 ya /setflood off")


FLOOD = {}


@app.on_message(filters.group & ~filters.service, group=3)
async def security_watcher(client, message):
    """💀 gban + 🌊 flood + 🏴 blacklist + 🎯 filters/notes + 🚨 reports"""
    cid = message.chat.id
    user = message.from_user
    text = message.text or message.caption or ""
    words = {w.strip(".,!?").lower() for w in text.split()}

    # 💀 global ban
    if user and str(user.id) in DB["gbans"]:
        try:
            await client.ban_chat_member(cid, user.id)
            await send(client, cid, f"💀 {mention(user)} Iꜱ Gʟᴏʙᴀʟʟʏ Bᴀɴɴᴇᴅ — Eᴠɪᴄᴛᴇᴅ! 🚫")
        except Exception:
            pass
        return

    if not user or await is_admin(client, cid, user.id):
        if user and words & {"@admin"} and gval(cid, "reports", True):
            pass
        else:
            return

    # 🚨 @admin report
    if "@admin" in words and gval(cid, "reports", True) and not text.startswith("/"):
        admins = [a for a in await get_admins(client, cid) if a != (await bot_user(client)).id][:10]
        tags = " ".join(f"[⚡](tg://user?id={a})" for a in admins)
        await send(client, cid,
                   f"🚨 **Rᴇᴘᴏʀᴛ!** {mention(user)} Nᴇᴇᴅꜱ Aᴛᴛᴇɴᴛɪᴏɴ!\n{tags}\n👉 Aᴅᴍɪɴꜱ, Dᴇᴋʜᴏ Yᴇ Mᴇꜱꜱᴀɢᴇ!")
        return

    if text.startswith("/"):
        return

    # 🏴 blacklist
    bl = gval(cid, "blacklist", []) or []
    if bl and words & set(bl):
        try:
            await message.delete()
        except Exception:
            pass
        return

    # 🌊 antiflood
    limit = gval(cid, "flood", cfg.FLOOD_LIMIT)
    if limit:
        now = time.time()
        bucket = FLOOD.setdefault(cid, {}).setdefault(user.id, deque())
        while bucket and now - bucket[0][0] > cfg.FLOOD_WINDOW:
            bucket.popleft()
        bucket.append((now, message.id))
        if len(bucket) > limit:
            ids = [mid for _, mid in bucket]
            try:
                await client.delete_messages(cid, ids)
            except Exception:
                pass
            FLOOD[cid].pop(user.id, None)
            try:
                await client.restrict_chat_member(
                    cid, user.id, ChatPermissions(),
                    until_date=datetime.now() + timedelta(seconds=cfg.FLOOD_MUTE))
                await send(client, cid,
                           f"🌊 {mention(user)} Fʟᴏᴏᴅɪɴɢ Kɪʏᴀ! Mᴜᴛᴇᴅ {human_time(cfg.FLOOD_MUTE)} 😤",
                           KB((B("Unmute", cb=f"unmute|{cid}|{user.id}", color="green"),)))
            except Exception:
                pass
            return

    # 🎯 filters + 📚 notes (#name)
    f = gval(cid, "filters", {}) or {}
    hit = (words & set(f)) if f else set()
    if hit:
        await send_content(client, cid, f[list(hit)[0]], reply_to=message.id)
        return
    for w in words:
        if w.startswith("#") and w[1:]:
            n = gval(cid, "notes", {}) or {}
            if w[1:] in n:
                await send_content(client, cid, n[w[1:]])
                break


@app.on_message(filters.command(["gban", "ungban"]) & GRPCMD)
async def gban_cmd(client, message):
    if message.from_user.id not in cfg.OWNER_IDS:
        return await send(client, message.chat.id, "👑 Sɪʀꜰ Oᴡɴᴇʀ Kᴀ Mᴀᴍʟᴀ Hᴀɪ! 🚫")
    user, reason = await get_target(client, message)
    if not user:
        return await send(client, message.chat.id, "🤔 Rᴇᴘʟʏ/ID/@ᴜꜱᴇʀɴᴀᴍᴇ Dᴏ! 🔍")
    reason = reason or "Nᴏ Rᴇᴀꜱᴏɴ"
    if message.command[0] == "gban":
        gban_add(user.id, reason, message.from_user.id)
        await send(client, message.chat.id, f"💀 {mention(user)} Gʟᴏʙᴀʟʟʏ Bᴀɴɴᴇᴅ!\n📝 {md(reason)}")
        await log_action(client, f"💀 GBAN → {user.id} | {reason}")
    else:
        gban_rm(user.id)
        await send(client, message.chat.id, f"🟢 {mention(user)} Gʙᴀɴ Hᴀᴛᴀʏᴀ!")


# ═══════════════════════ 📣 Tᴀɢ Aʟʟ (Mᴇɴᴛɪᴏɴ Bᴏᴛ Sᴛʏʟᴇ) ═══════════════════════

MENTION_TASKS = {}


async def tagger(client, cid, status_id, header):
    count, batch, sends = 0, [], 0
    try:
        async for m in client.get_chat_members(
                cid, filter=enums.ChatMembersFilter.RECENT, limit=cfg.MENTION_LIMIT):
            u = m.user
            if u.is_bot or u.is_deleted:
                continue
            batch.append(mention(u))
            if len(batch) >= cfg.MENTION_BATCH:
                sends += 1
                try:
                    await client.send_message(
                        cid, stylize(f"{header}\n\n" + "\n".join(f"🔗 {x}" for x in batch)))
                except FloodWait as e:
                    await asyncio.sleep(e.value + 1)
                count += len(batch)
                batch = []
                if sends % 5 == 0:
                    try:
                        await client.edit_message_text(cid, status_id, stylize(f"📣 Tᴀɢɢɪɴɢ... {count} Dᴏɴᴇ ⏳"))
                    except Exception:
                        pass
                await asyncio.sleep(cfg.MENTION_DELAY)
        if batch:
            try:
                await client.send_message(cid, stylize("\n".join(f"🔗 {x}" for x in batch)))
                count += len(batch)
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
        await client.edit_message_text(
            cid, status_id,
            stylize(f"✅ Dᴏɴᴇ! {count} Mᴇᴍʙᴇʀꜱ Tᴀɢɢᴇᴅ! 🎉"),
            reply_markup=KB((B("Delete", cb="close", color="red"),)))
    except asyncio.CancelledError:
        try:
            await client.edit_message_text(cid, status_id, stylize(f"✋ Sᴛᴏᴘᴘᴇᴅ! {count} Tᴀɢɢᴇᴅ."))
        except Exception:
            pass
    except Exception:
        pass


@app.on_message(filters.command(["all", "tagall", "mentionall"]) & GRPCMD)
async def tag_all_cmd(client, message):
    cid = message.chat.id
    if not await guard(client, message):
        return
    task = MENTION_TASKS.get(cid)
    if task and not task.done():
        return await send(client, cid, "⏳ Tᴀɢɢɪɴɢ Cʜᴀʟ Rᴀʜɪ Hᴀɪ — /stopmention ꜱᴇ ʀᴏᴋᴏ! ✋")
    text = " ".join(message.command[1:]).strip() or "📣 Attention Everyone!"
    status = await send(client, cid, "📣 Tᴀɢ Aʟʟ Sᴛᴀʀᴛ Hᴜᴀ... ⏳",
                        KB((B("Stop", cb=f"stopmention|{cid}", color="red"),)))
    MENTION_TASKS[cid] = asyncio.create_task(tagger(client, cid, status.id, text))


@app.on_message(filters.command(["stopmention", "stoptag"]) & GRPCMD)
async def stop_mention_cmd(client, message):
    task = MENTION_TASKS.get(message.chat.id)
    if task and not task.done():
        task.cancel()
        await send(client, message.chat.id, "✋ Tᴀɢɢɪɴɢ Rᴏᴋ Dɪ! 🛑")
    else:
        await send(client, message.chat.id, "🤔 Kᴜᴄʜ Tᴀɢɢɪɴɢ Nᴀʜɪ Cʜᴀʟ Rᴀʜɪ! 😅")


@app.on_message(filters.command(["tagadmins", "admintag"]) & GRPCMD)
async def tag_admins_cmd(client, message):
    if not await guard(client, message):
        return
    lines = [f"👑 **Aᴅᴍɪɴꜱ Oꜰ** {md(message.chat.title)}"]
    try:
        async for m in client.get_chat_members(
                message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS, limit=50):
            if m.user.is_bot:
                continue
            badge = "👑" if m.status == enums.ChatMemberStatus.OWNER else "⚡"
            lines.append(f"{badge} {mention(m.user)}")
    except Exception:
        pass
    lines.append("\n📣 Aᴅᴍɪɴꜱ, Kᴀᴀᴍ Hᴀɪ! 😎")
    await send(client, message.chat.id, "\n".join(lines))


# ═══════════════════════ ⚙️ Sᴇᴛᴛɪɴɢꜱ Pᴀɴᴇʟ + Mɪꜱᴄ ═══════════════════════

TOGGLES = {
    "welcome": ("Welcome", "👋"),
    "goodbye": ("Goodbye", "🚪"),
    "cleanservice": ("Clean Service", "🧹"),
    "reports": ("Reports", "🚨"),
}


def settings_panel(cid):
    rows = []
    for key, (label, ic) in TOGGLES.items():
        w = gval(cid, key, {}) or {}
        on = w.get("on", False) if key in ("welcome", "goodbye") else gval(cid, key, key == "reports")
        rows.append((B(label, cb=f"set|{cid}|{key}", icon=("🟢 " if on else "🔴 ") + ic),))
    flood = gval(cid, "flood", cfg.FLOOD_LIMIT)
    rows.append((B(f"Flood: {flood or 'Off'}", cb=f"set|{cid}|flood", icon="🌊"),))
    rows.append((B("Locks Panel", cb=f"locks|{cid}", icon="🔒"), B("Close", cb="close", color="red")))
    return KB(*rows)


@app.on_message(filters.command("settings") & GRPCMD)
async def settings_cmd(client, message):
    if not await guard(client, message):
        return
    await send(client, message.chat.id, "🎛️ **Gʀᴏᴜᴘ Sᴇᴛᴛɪɴɢꜱ** — Tᴏɢɢʟᴇ Kᴀʀᴏ ⚡", settings_panel(message.chat.id))


@app.on_message(filters.command("id"))
async def id_cmd(client, message):
    cid = message.chat.id
    chat_id = str(cid)
    if cid < 0:
        chat_id = f"`-100{str(cid)[4:]}`" if str(cid).startswith("-100") else f"`{cid}`"
    out = [f"🪪 **Iᴅs**\n\n📍 Cʜᴀᴛ: {chat_id}"]
    if message.from_user:
        out.append(f"👤 Yᴏᴜ: `{message.from_user.id}`")
    if message.reply_to_message and message.reply_to_message.from_user:
        out.append(f"🎯 Rᴇᴘʟʏ: `{message.reply_to_message.from_user.id}`")
    await send(client, cid, "\n".join(out))


@app.on_message(filters.command("info"))
async def info_cmd(client, message):
    user, _ = await get_target(client, message)
    user = user or message.from_user
    if not user:
        return
    lines = [
        f"🔍 **Uꜱᴇʀ Iɴꜰᴏ**\n",
        f"👤 Nᴀᴍᴇ: {md(user.first_name or '')} {md(user.last_name or '')}",
        f"🔗 Uꜱᴇʀɴᴀᴍᴇ: @{user.username}" if user.username else "🔗 Uꜱᴇʀɴᴀᴍᴇ: Nᴀʜɪ",
        f"🪪 Iᴅ: `{user.id}`",
        f"💎 Pʀᴇᴍɪᴜᴍ: {'Yᴇꜱ ✨' if getattr(user, 'is_premium', False) else 'Nᴏ'}",
        f"🤖 Bᴏᴛ: {'Yᴇꜱ' if user.is_bot else 'Nᴏ'}",
    ]
    try:
        m = await client.get_chat_member(message.chat.id, user.id)
        stat = str(m.status).split(".")[-1]
        lines.append(f"📍 Sᴛᴀᴛᴜꜱ: {stat.title()}")
    except Exception:
        pass
    await send(client, message.chat.id, "\n".join(lines))


@app.on_message(filters.command("ping"))
async def ping_cmd(client, message):
    t0 = time.time()
    m = await send(client, message.chat.id, "💫 Pɪɴɢ...")
    ms = (time.time() - t0) * 1000
    await client.edit_message_text(
        message.chat.id, m.id,
        stylize(f"💥 Pᴏɴɢ! `{ms:.0f}ᴍs` ⚡"))


@app.on_message(filters.command("stats"))
async def stats_cmd(client, message):
    from pyrogram import __version__ as pv
    chats = len(DB["chats"])
    filts = sum(len(c.get("filters", {})) for c in DB["chats"].values())
    notes = sum(len(c.get("notes", {})) for c in DB["chats"].values())
    text = (
        f"📊 **Bᴏᴛ Sᴛᴀᴛꜱ**\n\n"
        f"💬 Cʜᴀᴛꜱ: {chats}\n🎯 Fɪʟᴛᴇʀꜱ: {filts}\n📚 Nᴏᴛᴇꜱ: {notes}\n"
        f"💀 Gʙᴀɴꜱ: {len(DB['gbans'])}\n🧠 Pʏʀᴏɢʀᴀᴍ: v{pv}\n"
        f"⏱️ Uᴘᴛɪᴍᴇ: {human_time(time.time() - START_TIME)}"
    )
    await send(client, message.chat.id, text)


# ═══════════════════════ ⚡ Iɴʟɪɴᴇ Mᴏᴅᴇ ═══════════════════════

@app.on_inline_query()
async def inline_handler(client, iq):
    try:
        await iq.answer([
            InlineQueryResultArticle(
                title=stylize("ManageX Help"),
                description=stylize("All commands list"),
                input_message_content=InputTextMessageContent(
                    stylize(HELP["main"])),
                reply_markup=help_buttons(),
            ),
            InlineQueryResultArticle(
                title=stylize("About ManageX"),
                description=stylize("Bot info"),
                input_message_content=InputTextMessageContent(
                    stylize("💎 ManageX — Advanced Group Management Bot!\n❤️‍🔥 Rose + Mention Style Power! ⚡")),
                reply_markup=KB((B("Help", cb="help|main", color="blue"),)),
            ),
        ], cache_time=5)
    except Exception:
        pass


# ═══════════════════════ 🖱️ Cᴀʟʟʙᴀᴄᴋ Dɪꜱᴘᴀᴛᴄʜᴇʀ ═══════════════════════

async def cb_edit(client, cq, text, buttons=None):
    try:
        await client.edit_message_text(
            cq.message.chat.id, cq.message.id, stylize(text),
            reply_markup=buttons)
    except RPCError:
        pass


@app.on_callback_query()
async def callbacks(client, cq):
    data = cq.data or ""
    uid = cq.from_user.id

    async def admin_here(cid):
        ok = await is_admin(client, cid, uid)
        if not ok:
            await cq.answer("🚫 Admins Only!", show_alert=True)
        return ok

    if data == "close":
        await cq.answer()
        try:
            await cq.message.delete()
        except Exception:
            pass

    elif data.startswith("help|"):
        await cq.answer()
        await cb_edit(client, cq, HELP[data.split("|", 1)[1]], help_buttons())

    elif data == "about":
        await cq.answer()
        me = await bot_user(client)
        await cb_edit(client, cq,
                      f"ℹ️ **Aʙᴏᴜᴛ**\n\n🤖 {md(me.first_name)}\n💠 Vᴇʀꜱɪᴏɴ: 1.0.0\n"
                      f"⏱️ Uᴘᴛɪᴍᴇ: {human_time(time.time() - START_TIME)}\n\n✨ Mᴀᴅᴇ Wɪᴛʜ ❤️‍🔥!",
                      KB((B("Help", cb="help|main", color="blue"), B("Close", cb="close", color="red"))))

    elif data.startswith("unban|"):
        _, cid, tid = data.split("|")
        cid, tid = int(cid), int(tid)
        if not await admin_here(cid):
            return
        try:
            await client.unban_chat_member(cid, tid)
            await cq.answer("🟢 Unbanned!", show_alert=False)
            await cb_edit(client, cq, "🟢 Uɴʙᴀɴᴇᴅ! ✅")
        except RPCError:
            await cq.answer("🚫 Failed — check my admin rights!", show_alert=True)

    elif data.startswith("unmute|"):
        _, cid, tid = data.split("|")
        cid, tid = int(cid), int(tid)
        if not await admin_here(cid):
            return
        try:
            await client.restrict_chat_member(cid, tid, ChatPermissions(
                can_send_messages=True, can_send_media_messages=True,
                can_send_other_messages=True, can_add_web_page_previews=True,
                can_send_polls=True, can_invite_users=True))
            await cq.answer("🔊 Unmuted!")
            await cb_edit(client, cq, "🔊 Uɴᴍᴜᴛᴇᴅ! ✅")
        except RPCError:
            await cq.answer("🚫 Failed — check my admin rights!", show_alert=True)

    elif data.startswith("rmwarn|"):
        _, cid, tid = data.split("|")
        cid, tid = int(cid), int(tid)
        if not await admin_here(cid):
            return
        warns = gval(cid, "warns", {}) or {}
        lst = warns.get(str(tid), [])
        if lst:
            lst.pop()
            if lst:
                warns[str(tid)] = lst
            else:
                warns.pop(str(tid), None)
            sval(cid, "warns", warns)
            await cq.answer("🧼 1 Warn Removed!")
            await cb_edit(client, cq, f"🧼 Wᴀʀɴ Rᴇᴍᴏᴠᴇᴅ! Rᴇᴍᴀɪɴɪɴɢ: {len(lst)} ✅")
        else:
            await cq.answer("📭 No warns left!")

    elif data.startswith("set|"):
        _, cid, key = data.split("|", 2)
        cid = int(cid)
        if not await admin_here(cid):
            return
        if key == "flood":
            await cq.answer("💡 /setflood 10 ya /setflood off se badlo!")
            return
        if key in ("welcome", "goodbye"):
            w = gval(cid, key, {}) or {}
            if not w.get("content"):
                await cq.answer(f"📭 Pehle /set{key} se message set karo!")
                return
            w["on"] = not w.get("on", False)
            sval(cid, key, w)
        else:
            cur = gval(cid, key, key == "reports")
            sval(cid, key, not cur)
        await cq.answer("✅ Updated!")
        await cb_edit(client, cq, "🎛️ **Gʀᴏᴜᴘ Sᴇᴛᴛɪɴɢꜱ** — Tᴏɢɢʟᴇ Kᴀʀᴏ ⚡", settings_panel(cid))

    elif data.startswith("lock|"):
        _, cid, typ = data.split("|")
        cid = int(cid)
        if not await admin_here(cid):
            return
        locks = gval(cid, "locks", {}) or {}
        if typ in locks:
            locks.pop(typ)
        else:
            locks[typ] = True
        sval(cid, "locks", locks)
        await cq.answer(("🔒 " if typ in gval(cid, "locks", {}) else "🔓 ") + typ.title())
        try:
            await client.edit_message_reply_markup(cid, cq.message.id, reply_markup=locks_panel(cid))
        except RPCError:
            pass

    elif data.startswith("locks|"):
        await cq.answer()
        await cb_edit(client, cq,
                      "🎛️ **Lᴏᴄᴋ Pᴀɴᴇʟ** — Bᴜᴛᴛᴏɴ Pᴇ Dᴀʙᴏ ⚡\n🔒 = Lᴏᴄᴋᴇᴅ • 🔓 = Oᴘᴇɴ",
                      locks_panel(int(data.split("|")[1])))

    elif data.startswith("rules|"):
        await cq.answer()
        r = gval(int(data.split("|")[1]), "rules")
        if r:
            await cb_edit(client, cq, f"📜 **Rᴜʟᴇꜱ**\n\n{r}")

    elif data.startswith("stopall|"):
        cid = int(data.split("|")[1])
        if not await admin_here(cid):
            return
        sval(cid, "filters", {})
        await cq.answer("💣 Nuked!")
        await cb_edit(client, cq, "💣 Sᴀʀᴇ Fɪʟᴛᴇʀꜱ Hᴀᴛᴀ Dɪʏᴇ! ✅")

    elif data.startswith("unpinall|"):
        cid = int(data.split("|")[1])
        if not await admin_here(cid):
            return
        try:
            await client.unpin_all_chat_messages(cid)
            await cq.answer("📌 All pins removed!")
            await cb_edit(client, cq, "📌 Sᴀʀᴇ Pɪɴꜱ Hᴀᴛᴀ Dɪʏᴇ! ✅")
        except RPCError:
            await cq.answer("🚫 Failed!", show_alert=True)

    elif data.startswith("stopmention|"):
        cid = int(data.split("|")[1])
        if not await admin_here(cid):
            return
        task = MENTION_TASKS.get(cid)
        if task and not task.done():
            task.cancel()
            await cq.answer("✋ Stopped!")
        else:
            await cq.answer("🤔 Nothing running!")


# ═══════════════════════ 🚀 Mᴀɪɴ ═══════════════════════

BANNER = r"""
╔══════════════════════════════════════╗
║   👑 M A N A G E X 👑                ║
║   ✨ Advanced Group Management Bot   ║
║   ⚡ Rose + Mention Style Powers ⚡    ║
╚══════════════════════════════════════╝
"""


def main():
    if not cfg.BOT_TOKEN or cfg.BOT_TOKEN.startswith("123456789"):
        print(stylize("🚫 Config.py me apna BOT_TOKEN daalo pehle! @BotFather se lo 🔑"))
        raise SystemExit(1)
    if (not cfg.API_ID or cfg.API_ID == 1234567
            or not cfg.API_HASH or cfg.API_HASH == "abcdef1234567890abcdef1234567890"):
        print(stylize("🚫 Config.py me API_ID aur API_HASH sahi karo — my.telegram.org 🔑"))
        raise SystemExit(1)
    print(BANNER)
    print(stylize("💎 Bot start ho raha hai... dher saare emojis ke saath! ✨"))
    app.run()


if __name__ == "__main__":
    main()
