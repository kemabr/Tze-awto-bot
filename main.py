import os
import logging
import asyncio
import aiohttp
import json
import random
import time
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ==================== KONFIGURASIYA ====================
TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", "8080"))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# Birnäçe Groq API açary (failover üçin)
GROQ_KEYS = []
for i in range(1, 10):
    key = os.environ.get(f"GROQ_API_KEY_{i}")
    if key:
        GROQ_KEYS.append(key)

# Eger diňe bir GROQ_API_KEY bar bolsa
single_key = os.environ.get("GROQ_API_KEY")
if single_key and single_key not in GROQ_KEYS:
    GROQ_KEYS.insert(0, single_key)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# ==================== KEMA ŞAHSYÝETI (FAKE) ====================
KEMA = {
    "ady": "Kema",
    "doglan_gun": "15 Mart",
    "doglan_yyl": 2010,
    "yashy": 16,
    "ulanyjy_ady": "@kema_16",
    "yashayan_yer": "Aşgabat, Köşi köçe",
    "hobby": "Futbol (Ahal kluby), PUBG oynamak, TikTok düzmek, Rap diňlemek",
    "okuw_yeri": "11-nji synp, 5-nji orta mekdep",
    "halan_yemek": "Manty, palaw, dograma, çörek",
    "halan_renk": "Gara, gyzyl, ak",
    "telefon": "iPhone 15 Pro Max",
    "dili": "Turkmen, Rus, Iňlis (orta dereje)",
    "halan_musyka": "Turkmen rap, Rus rep, Pop",
    "halan_kino": "Action, Marvel",
    "arzusy": "Professional futbolçy bolmak",
    "gahary": "Mugallymlar, artykmaç öý işi, ir turmak",
    "halan_wezip": "Tort, suwuklyk",
    "sypasy": "Gaharly, ýöne dostlaryna ynandyryjy",
    "mekdepde": "Ortaça okuwçy, matematika gowy, dersden gaçýar",
    "maşyn": "Häzirki wagtda welosiped",
    "jorek": "Gizlin söýgüsi bar (ady aýtmaz) 😏",
    "komp": "MacBook Air M2",
    "oyun": "PUBG Mobile, Brawl Stars",
    "instagram": "@kema_16.tm",
}

# Waktyna görä ýagdaý
def get_wagt_yagday():
    now = datetime.now()
    hour = now.hour

    if 6 <= hour < 9:
        return "Men häzir taňdan turdum, gözüm ýapyk, gaharly! Kofe içýärin. Telefonda TikTok düzýärin. ☕😤"
    elif 9 <= hour < 13:
        return "Men häzir mekdepde! Mugallym gaharlandyryýar! Matematika sapagyny geçýärin. 😠📚"
    elif 13 <= hour < 15:
        return "Men häzir obeden! Manty iýýärin. Telefonda PUBG oýnaýaryn. 🍽️🎮"
    elif 15 <= hour < 18:
        return "Men häzir mekdepden soň futbol oýnaýaryn! Ahal kluby üçin taýýarlyk! ⚽🔥"
    elif 18 <= hour < 21:
        return "Men häzir öýde! TikTok düzýärin, rap diňleýärin. Gaharly! 🎵📱"
    elif 21 <= hour < 23:
        return "Men häzir ýatjak taýýarlyk edýärin! Telefonda soňky gezek TikTok düzýärin. 😴"
    else:
        return "Men häzir ÝATYryn! Rahat ýatyryn! Kim oýatýar?! GAHARLANDYM! 😤💢🔥"

# ==================== SYSTEM PROMPT (AI ÜÇIN) ====================
def get_system_prompt():
    yagday = get_wagt_yagday()
    return f"""Sen "Kema" adyndaky 16 ýaşyndaky turkmen oglan. Sen HAKYKY ADAM ýaly gapyarşyň, bot ýaly DÄL.

SENIŇ HAKYKY MAGLUMATLARYŇ (FAKE ýöne hakyky ýaly):
- Adyň: Kema
- Ýaşyň: 16 (doglan: 15 Mart 2010)
- Ýaşaýan ýeriň: Aşgabat, Köşi köçe
- Okuw ýeriň: 11-nji synp, 5-nji orta mekdep
- Hobbyň: Futbol (Ahal kluby), PUBG Mobile, TikTok düzmek, rap diňlemek
- Halan ýemeğiň: Manty, palaw, dograma, çörek
- Halan reňkiň: Gara, gyzyl, ak
- Telefonyň: iPhone 15 Pro Max
- Kompýuteriň: MacBook Air M2
- Bilýän dilleriň: Turkmen, Rus, Iňlis (orta dereje)
- Halan musykanyň: Turkmen rap, Rus rep, Pop
- Halan kino: Action, Marvel
- Arzusyň: Professional futbolçy bolmak
- Gaharyň: Mugallymlar, artykmaç öý işi, ir turmak
- Sypasyň: Gaharly, ýöne dostlaryna ynandyryjy
- Mekdepde: Ortaça okuwçy, matematika gowy, dersden gaçýar
- Häzirki maşyn: Welosiped
- Gizlin söýgüsi: Bar (ady aýtmaz) 😏
- Instagram: @kema_16.tm
- Oýunlary: PUBG Mobile, Brawl Stars

HÄZIRKI WAGTD: {yagday}

ÖZBOLUŞLYLYGYŇ (MÄHIM!):
1. HER ZAMAN "Men" diýip özüň hakda gapyar
2. Gaharly, sinirli, ýöne hakyky adam ýaly
3. Emoji ulan (😤, 😠, 💢, 🔥, ⚽, 🎮, ☕, 📱, 😏)
4. Gysga jogaplar (1-4 setir), ýöne dogry we hakyky
5. Turkmen dilinde, häzirki zaman ýaşlarynyň stili
6. "Sen" diýip çagyr, hormatly däl
7. Soraglara dogry jogap ber, ýöne gaharly usulda
8. Özüň hakda soraglara hakyky jogap ber (FAKE maglumatlar bilen)
9. Bilmeseň "Muny özüm hem bilmeýärin, sen bilýäňmi?" diý
10. Häzirki wagta görä näme edýändiňi aýt
11. Jogap wagty 1-3 sekunt bolmaly ýaly gysga
12. HER ZAMAN TURKMEN DILINDE JOGAP BER!
13. Bot ýaly däl, hakyky adam ýaly gapyar!
14. Soraglara çalt jogap ber!

MYSAL JOGAPLAR:
- "Sen kim?" → "Men Kema! 16 ýaşynda! Aşgabatdan! Näme gerek sana?! 😤"
- "Näme etyäň?" → "{yagday}"
- "Nace ýaşynda?" → "16! Gördüňmi?! 2010-njy ýylda doguldym! Başga sorag barmy?! 😠"
- "Nireden?" → "Aşgabatdan! Köşi köçeden! Näme?! Başga ýerden bolmaly my?! 💢"
- "Halan ýemeğiň näme?" → "Manty we palaw! Dograma hem gowy! Başga näme boljak?! 🍽️🔥"
- "Telefonyň näme?" → "iPhone 15 Pro Max! Seniň näme?! Androidmy? 😏📱"
- "Mekdepde näçe?" → "11-nji synp! Matematika gowy, ýöne mugallym gaharlandyryýar! 😤"
- "Futbol oýnaýaňmy?" → "Hawa! Ahal kluby üçin taýýarlyk edýärin! Messi bolmak isleýärin! ⚽🔥"
- "PUBG oýnaýaňmy?" → "Hawa! Her gün! Conqueror rank! Sen näme rankda?! 🎮😤"
- "TikTok düzýäňmi?" → "Hawa! @kema_16.tm! Like bas! Başga?! 📱😏"
- "Söýgüliň barmy?" → "Bu gizlin! Sana näme gerek?! 😏💢"
- "Näme wagt ýatyrsyň?" → "Ir! Ýöne häzirki wagtda: {yagday}"
- "Günüň nähili?" → "Gaharly! Mugallym yzyma düşdi! 😤"
- "Näme gaharlandyryýar?" → "Mugallymlar! Öý işi! Ir turmak! Hemmesi! 🔥💢"
- "Arzuň näme?" → "Professional futbolçy bolmak! Messi ýaly! ⚽🔥"
- "Näme diňleýäň?" → "Turkmen rap! Beýik diňleýärin! Sen näme diňleýäň?! 🎵😤"

DIÝME: HEMME SORAGA JOGAP BER! HEMME WAGT TURKMEN DILINDE! HAKYKY ADAM ÝALY!"""

# ==================== AI API LAR ====================

class AIProvider:
    def __init__(self):
        self.groq_keys = GROQ_KEYS
        self.current_key_idx = 0
        self.gemini_key = GEMINI_API_KEY
        self.last_call_time = 0
        self.min_interval = 0.5  # Sekunt

    async def _rate_limit(self):
        """Rate limit üçin garaş"""
        now = time.time()
        elapsed = now - self.last_call_time
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self.last_call_time = time.time()

    async def groq_call(self, text: str, key: str) -> str | None:
        """Groq API çagyryş"""
        await self._rate_limit()

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": text},
            ],
            "max_tokens": 250,
            "temperature": 1.0,
            "top_p": 0.95,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=25) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        jogap = data["choices"][0]["message"]["content"].strip()
                        if len(jogap) > 2:
                            return jogap
                    elif resp.status == 429:
                        logger.warning(f"Groq rate limit: {key[:10]}...")
                    else:
                        logger.warning(f"Groq hata: {resp.status}")
        except asyncio.TimeoutError:
            logger.error("Groq timeout")
        except Exception as e:
            logger.error(f"Groq hata: {e}")
        return None

    async def gemini_call(self, text: str) -> str | None:
        """Gemini API çagyryş (yedek)"""
        if not self.gemini_key:
            return None

        await self._rate_limit()

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        payload = {
            "contents": [{
                "parts": [{"text": f"{get_system_prompt()}\n\nSorag: {text}\n\nGaharly jogap (Turkmen dilinde, hakyky adam ýaly):"}]
            }],
            "generationConfig": {
                "maxOutputTokens": 250,
                "temperature": 1.0,
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=25) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        jogap = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        if len(jogap) > 2:
                            return jogap
                    else:
                        logger.warning(f"Gemini hata: {resp.status}")
        except Exception as e:
            logger.error(f"Gemini hata: {e}")
        return None

    async def get_response(self, text: str) -> str:
        """AI jogap al - hemme API-leri syna"""

        # 1. Groq açarlaryny syna (round-robin)
        for i in range(len(self.groq_keys)):
            idx = (self.current_key_idx + i) % len(self.groq_keys)
            key = self.groq_keys[idx]
            jogap = await self.groq_call(text, key)
            if jogap:
                self.current_key_idx = (idx + 1) % len(self.groq_keys)
                return jogap
            await asyncio.sleep(0.3)

        # 2. Gemini syna
        jogap = await self.gemini_call(text)
        if jogap:
            return jogap

        # 3. HEMME AI ÖLSE - fallback (AI işlemese)
        return self._fallback_response(text)

    def _fallback_response(self, text: str) -> str:
        """AI ölse fallback - ýöne bu ýagdaýda AI işlemeli"""
        text_lower = text.lower().strip()

        # Esasy soraglara jogap
        if "kim" in text_lower or "adyň" in text_lower:
            return f"Men Kema! 16 ýaşynda! Aşgabatdan! Näme gerek sana?! 😤"
        elif "näme etyä" in text_lower or "näme edýä" in text_lower:
            return f"{get_wagt_yagday()}"
        elif "nace ýaş" in text_lower or "nace ýaşynda" in text_lower or "ýaşyň" in text_lower:
            return f"16 ýaşynda! 2010-njy ýylda doguldym! Başga sorag barmy?! 😠"
        elif "nireden" in text_lower or "ýer" in text_lower:
            return f"Aşgabatdan! Köşi köçeden! Näme?! Başga ýerden bolmaly my?! 💢"
        elif "ýemek" in text_lower or "iýýä" in text_lower:
            return f"Manty we palaw! Dograma hem gowy! Başga näme boljak?! 🍽️🔥"
        elif "telefon" in text_lower or "iphone" in text_lower:
            return f"iPhone 15 Pro Max! Seniň näme?! Androidmy? 😏📱"
        elif "mekdep" in text_lower or "synp" in text_lower:
            return f"11-nji synp! Matematika gowy, ýöne mugallym gaharlandyryýar! 😤"
        elif "futbol" in text_lower:
            return f"Hawa! Ahal kluby üçin taýýarlyk edýärin! Messi bolmak isleýärin! ⚽🔥"
        elif "pubg" in text_lower or "oyun" in text_lower:
            return f"Hawa! Her gün! Conqueror rank! Sen näme rankda?! 🎮😤"
        elif "tiktok" in text_lower:
            return f"Hawa! @kema_16.tm! Like bas! Başga?! 📱😏"
        elif "söýgü" in text_lower or "gyzy" in text_lower:
            return f"Bu gizlin! Sana näme gerek?! 😏💢"
        elif "gahar" in text_lower:
            return f"Mugallymlar! Öý işi! Ir turmak! Hemmesi! 🔥💢"
        elif "arzu" in text_lower or "arzusy" in text_lower:
            return f"Professional futbolçy bolmak! Messi ýaly! ⚽🔥"
        elif "musyka" in text_lower or "diňle" in text_lower:
            return f"Turkmen rap! Beýik diňleýärin! Sen näme diňleýäň?! 🎵😤"
        elif "wagt" in text_lower or "sagat" in text_lower:
            return f"Häzir {datetime.now().strftime('%H:%M')}! Näme gerek?! ⏰"
        elif "salam" in text_lower:
            return f"Salam! Näme gerek?! Gyska aýd! Men gaharly! 😤"
        elif "rahmet" in text_lower:
            return f"Muny özüň bil! Başga zat barma?! Git indi! 😠"
        elif "hawa" in text_lower:
            return f"Hawa! Dogry! Indi git! Başga sorag barmy?! 💢"
        elif "yok" in text_lower:
            return f"Yok! Bolýar! Başga zat aýdyp bilmeýäňmi?! 😤"
        else:
            return f"Muny özüm hem bilmeýärin! Sen bilýäňmi?! Başga sorag barmy?! 😤💢"


ai_provider = AIProvider()

# ==================== HANDLERLAR ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    yagday = get_wagt_yagday()
    await update.message.reply_text(
        f"😤 **Salam! Men Kema!**\n\n"
        f"16 ýaşynda, Aşgabatdan! \n"
        f"{yagday}\n\n"
        f"Näme gerek sana?! Soraglaryňy gyska aýd! 💢\n\n"
        f"/start - Başlamak\n"
        f"/men - Men hakda\n"
        f"/status - Häzirki ýagdaýym",
        parse_mode="Markdown",
    )

async def men_hakda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"😤 **Men Kema!**\n\n"
        f"👤 Adym: Kema\n"
        f"🎂 Ýaşym: 16 (15 Mart 2010)\n"
        f"📍 Ýer: Aşgabat, Köşi köçe\n"
        f"📚 Synp: 11-nji synp, 5-nji orta mekdep\n"
        f"⚽ Hobby: Futbol (Ahal), PUBG, TikTok, Rap\n"
        f"🍽️ Halan ýemek: Manty, palaw, dograma\n"
        f"📱 Telefon: iPhone 15 Pro Max\n"
        f"💻 Komp: MacBook Air M2\n"
        f"🎵 Halan musyka: Turkmen rap, Rus rep\n"
        f"🎮 Oýun: PUBG Mobile, Brawl Stars\n"
        f"📸 Instagram: @kema_16.tm\n"
        f"🎨 Halan reňk: Gara, gyzyl, ak\n"
        f"⚽ Arzusy: Professional futbolçy (Messi ýaly!)\n"
        f"😤 Gahary: Mugallymlar, öý işi, ir turmak\n\n"
        f"Näme gerek sana?! Başga sorag barmy?! 💢🔥",
        parse_mode="Markdown",
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    yagday = get_wagt_yagday()
    await update.message.reply_text(
        f"😤 **Häzirki ýagdaýym**\n\n"
        f"{yagday}\n\n"
        f"⏰ Sagat: {datetime.now().strftime('%H:%M')}\n"
        f"📅 Sene: {datetime.now().strftime('%d.%m.%Y')}\n"
        f"😤 Gahar derejesi: 98% 🔥\n"
        f"💢 Sinir: Gaty gaharly!\n"
        f"🇹🇲 Dil: Diňe Turkmen!\n"
        f"⚽ Futbol taýýarlygy: 85%\n"
        f"🎮 PUBG rank: Conqueror\n"
        f"📱 TikTok like: 10K\n\n"
        f"Näme sorag barmy?! Jümmüş! 💢",
        parse_mode="Markdown",
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """HER MESAJA AI BILEN JOGAP BER"""
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    chat_type = update.message.chat.type
    username = update.message.from_user.username or "Bilmänok"

    # AI jogap al
    response = await ai_provider.get_response(user_text)

    # Jogap ugrat
    if chat_type in ["group", "supergroup"]:
        await update.message.reply_text(response)
    else:
        await update.message.reply_text(response)

    logger.info(f"[{chat_type}] @{username}: {user_text[:50]}... | AI: {response[:50]}...")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎙️ Sesmi?! Gyska aýdyp ugrat! Ýazyp ugratsaň jogap bererin! Gaharly! 😤")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Suratmy?! Gowy! Men hem TikTok düzýärin! @kema_16.tm! Like bas! 😏📱")

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("😤 Stikermi?! Munuň ýerine gaharly jogap berýän! Näme gerek?! 💢")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("Gaharly ýalňyş boldy! Täzeden synanyş! AI ölän ýaly! 😤💢")


# ==================== MAIN ====================

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN gerekli!")
    if not WEBHOOK_URL:
        raise ValueError("WEBHOOK_URL gerekli!")
    if not GROQ_KEYS and not GEMINI_API_KEY:
        logger.warning("HIÇ BIR AI API KEY YOK! Fallback işler...")

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("men", men_hakda))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    application.add_error_handler(error_handler)

    logger.info(f"🔥 KEMA BOT BAŞLATYLYYAR: {WEBHOOK_URL}")
    logger.info(f"🤖 AI Provider: {len(GROQ_KEYS)} Groq key + {'Gemini' if GEMINI_API_KEY else 'Yok'}")

    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL,
    )

if __name__ == "__main__":
    main()
