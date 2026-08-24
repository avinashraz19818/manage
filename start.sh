#!/usr/bin/env bash
# ══════════════════════════════════════════════════════
#  👑 MᴀɴᴀɢᴇX Bᴏᴛ — Oɴᴇ-Sʜᴏᴛ Sᴛᴀʀᴛ Sᴄʀɪᴘᴛ 🚀
#  ▸ .venv banao → activate → requirements install
#  ▸ purana running bot stop → fresh background start
#  ▸ Usage:  bash start.sh
# ══════════════════════════════════════════════════════

APP="manage.py"
LOG="bot.log"
VENV=".venv"
PID_FILE="bot.pid"

cd "$(dirname "$0")" || exit 1

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════╗"
echo -e "║   👑  M A N A G E X  🚀            ║"
echo -e "║   Oɴᴇ-Sʜᴏᴛ Sᴛᴀʀᴛꜱ Sᴄʀɪᴘᴛ ⚡         ║"
echo -e "╚════════════════════════════════════╝${NC}"

# 1️⃣ Python check 🐍
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${RED}🚫 Python3 nahi mila! Install karo: sudo apt install python3 python3-venv python3-pip${NC}"
    exit 1
fi

# 2️⃣ .venv banao (agar nahi hai) 📦
if [ ! -d "$VENV" ]; then
    echo -e "${YELLOW}📦 Virtual environment ban raha hai...${NC}"
    python3 -m venv "$VENV" 2>/dev/null || {
        echo -e "${RED}🚫 venv fail hua! Ye chalao: sudo apt install python3-venv python3-pip${NC}"
        exit 1
    }
else
    echo -e "${GREEN}✅ .venv mila already${NC}"
fi

# 3️⃣ Activate + requirements install 📥
source "$VENV/bin/activate"
echo -e "${CYAN}📥 Requirements install ho rahi hai... (pehli baar thoda time lagega)${NC}"
pip install --upgrade pip -q 2>/dev/null
if ! pip install -r requirements.txt -q; then
    echo -e "${RED}🚫 Requirements install fail! Internet check karo ya error upar dekho${NC}"
    deactivate 2>/dev/null
    exit 1
fi
echo -e "${GREEN}✅ Dependencies ready${NC}"

# 4️⃣ Purana running bot check + stop 🛑
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo -e "${YELLOW}⏳ Purana bot chal raha hai (PID: $OLD_PID) — rok raha hoon...${NC}"
        kill "$OLD_PID" 2>/dev/null
        for _ in $(seq 1 10); do
            kill -0 "$OLD_PID" 2>/dev/null || break
            sleep 1
        done
        kill -9 "$OLD_PID" 2>/dev/null
        echo -e "${GREEN}🛑 Purana bot stop ho gaya${NC}"
    fi
    rm -f "$PID_FILE"
fi

# Extra safety — koi bhi manage.py process bacha ho 🔍
for P in $(pgrep -f "python.*$APP" 2>/dev/null); do
    kill -9 "$P" 2>/dev/null
done
sleep 1

# 5️⃣ Fresh background start 🚀
echo -e "${CYAN}🚀 Bot fresh start ho raha hai background me...${NC}"
nohup python3 "$APP" > "$LOG" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"
sleep 4

# 6️⃣ Status check ✅
if kill -0 "$NEW_PID" 2>/dev/null; then
    echo -e "${GREEN}✅ Bot START ho gaya! 🎉${NC}"
    echo -e "${CYAN}🪪 PID: $NEW_PID  •  📜 Log: $LOG${NC}"
    echo -e "👉 Live log:   tail -f $LOG"
    echo -e "👉 Stop:       kill \$(cat $PID_FILE)"
    echo -e "👉 Restart:    bash start.sh"
else
    echo -e "${RED}🚫 Bot start nahi ho paya! Error log (last 20 lines):${NC}"
    echo -e "${YELLOW}────────────────────────────${NC}"
    tail -n 20 "$LOG"
    echo -e "${YELLOW}────────────────────────────${NC}"
    echo -e "💡 Zyadatar problem: config.py me BOT_TOKEN / API_ID / API_HASH galat hai"
    rm -f "$PID_FILE"
fi

deactivate 2>/dev/null
exit 0
