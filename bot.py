from rubibot import RubiBot, types, updates, exceptions
import requests
import os
import time
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = os.getenv("RUBIKA_BOT_TOKEN", "").strip()
CARD = os.getenv("CARD_NUMBER", "6219861932569709").strip()
SUPPORT = os.getenv("SUPPORT_USERNAME", "@Poriysmeii").strip()
BASE = os.getenv("DATA_DIR", ".")

ADMIN_FILE = f"{BASE}/admin_id.txt"
OFFSET_FILE = f"{BASE}/rubika_offset.txt"
ORDERS_FILE = f"{BASE}/orders.json"

bot = RubiBot(TOKEN) if TOKEN else None
ADMIN_ID = None
ORDERS = {}


def read(path, default=None):
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return f.read().strip() or default
    except Exception:
        pass
    return default


def save(path, value):
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(value))
    except Exception as e:
        print("SAVE ERROR:", repr(e), flush=True)


ADMIN_ID = os.getenv("ADMIN_ID", "").strip() or read(ADMIN_FILE)

try:
    ORDERS = json.loads(read(ORDERS_FILE, "{}"))
    if not isinstance(ORDERS, dict):
        ORDERS = {}
except Exception:
    ORDERS = {}


def save_orders():
    try:
        with open(ORDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(ORDERS, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("ORDERS SAVE ERROR:", repr(e), flush=True)


def get_updates(offset=None):
    params = {"limit": 10}

    if offset:
        params["offset_id"] = offset

    try:
        r = requests.post(
            f"{bot.BASE_URL}/getUpdates",
            json=params,
            timeout=60
        )

        if r.status_code in (502, 503, 504):
            print("RUBIKA SERVER ERROR:", r.status_code, flush=True)
            time.sleep(5)
            return [], offset

        if r.status_code != 200:
            print("HTTP ERROR:", r.status_code, flush=True)
            time.sleep(5)
            return [], offset

        text = r.text.strip()

        if not text:
            print("EMPTY RESPONSE", flush=True)
            time.sleep(3)
            return [], offset

        try:
            data = r.json()
        except Exception:
            print(
                "INVALID RESPONSE:",
                r.status_code,
                repr(text[:200]),
                flush=True
            )
            time.sleep(3)
            return [], offset

        if data.get("status") != "OK":
            print("GET UPDATES ERROR:", data, flush=True)
            time.sleep(3)
            return [], offset

        result = data.get("data") or {}

        if not isinstance(result, dict):
            return [], offset

        arr = result.get("updates") or []

        return (
            [updates.Update(item) for item in arr],
            result.get("next_offset_id") or offset
        )

    except requests.exceptions.Timeout:
        print("GET UPDATES TIMEOUT", flush=True)
        time.sleep(5)
        return [], offset

    except requests.exceptions.ConnectionError:
        print("CONNECTION ERROR", flush=True)
        time.sleep(5)
        return [], offset

    except requests.exceptions.RequestException as e:
        print("REQUEST ERROR:", repr(e), flush=True)
        time.sleep(5)
        return [], offset

    except Exception as e:
        print("GET UPDATES ERROR:", repr(e), flush=True)
        time.sleep(5)
        return [], offset


def kb(rows):
    keyboard = types.ChatKeypad(resize_keyboard=True)

    for row in rows:
        keypad_row = types.KeypadRow()

        for text, data in row:
            keypad_row.add(
                types.KeypadSimpleButton(text, data)
            )

        keyboard.add(keypad_row)

    return keyboard


def main_kb():
    return kb([
        [("🛍 خدمات روبیکا", "services")],
        [("📜 قوانین", "rules")],
        [("📞 پشتیبانی", "support")]
    ])


def services_kb():
    return kb([
        [("📣 افزایش کانال", "channel"),
         ("👥 افزایش گروه", "group")],
        [("⭐ افزایش روبینو", "followers")],
        [("🏠 منوی اصلی", "home")]
    ])


def input_kb():
    return kb([
        [("❌ خروج", "cancel_order")]
    ])


# تعرفه کانال
CHANNEL = [
    "100 — 200",
    "500 — 500",
    "1,000 — 800",
    "5,000 — 1,200",
    "10,000 — 1,400",
    "15,000 — 1,600"
]


# سقف گروه 10 هزار
GROUP = [
    "100 — 200",
    "500 — 500",
    "1,000 — 800",
    "5,000 — 1,200",
    "10,000 — 1,400"
]


# تعرفه روبینو
FOLLOWERS = [
    "1,000 — 500",
    "10,000 — 1,500",
    "50,000 — 5,000",
    "100,000 — 9,500",
    "150,000 — 14,500"
]


def price_kb(items, prefix):
    rows = []

    for item in items:
        rows.append([
            (prefix + item, "price")
        ])

    rows.append([
        ("🔙 خدمات", "services"),
        ("🏠 اصلی", "home")
    ])

    return kb(rows)


def start(m):
    bot.send_message(
        m.chat_id,
        """🛍 فروشگاه خدمات روبیکا

سلام دوست عزیز 👋

📣 افزایش کانال
👥 افزایش گروه
⭐ افزایش روبینو

خدمت موردنظر را انتخاب کنید 👇""",
        chat_keypad=main_kb()
    )


def get_username(m):
    try:
        chat = bot.get_chat(str(m.chat_id))
        username = getattr(chat, "username", None)

        if username:
            return "@" + str(username).lstrip("@")

    except Exception:
        pass

    return "ندارد"


def normalize_link(text):
    text = text.strip()

    if text.startswith("@"):
        username = text[1:].strip()

        if re.fullmatch(r"[A-Za-z0-9_]{3,64}", username):
            return "@" + username

        return None

    match = re.match(
        r"^https?://(?:www\.)?(?:rubika\.ir|web\.rubika\.ir)/([^/?#\s]+)",
        text,
        re.I
    )

    if match:
        username = match.group(1).lstrip("@")

        if re.fullmatch(r"[A-Za-z0-9_]{3,64}", username):
            return "@" + username

    return None


def cancel_order(m):
    uid = str(m.chat_id)

    if uid in ORDERS:
        del ORDERS[uid]
        save_orders()

    bot.send_message(
        uid,
        """❌ ثبت سفارش لغو شد.

به منوی خدمات برگشتید 👇""",
        chat_keypad=services_kb()
    )


def new_order(m, service, price, typ):
    uid = str(m.chat_id)

    ORDERS[uid] = {
        "sender_id": str(
            getattr(m, "sender_id", "") or ""
        ),
        "username": get_username(m),
        "service": service,
        "price": price,
        "type": typ,
        "target": "",
        "waiting": True,
        "receipt": False
    }

    save_orders()

    if typ == "کانال":
        title = "📌 آیدی کانال را ارسال کنید"
        example = "@username"

    elif typ == "گروه":
        title = "📌 آیدی گروه را ارسال کنید"
        example = "@username"

    else:
        title = "📌 آیدی پیج روبینو را ارسال کنید"
        example = "@username"

    bot.send_message(
        uid,
        f"""{title}

مثال:
{example}

⚠️ فقط آیدی عمومی روبیکا را ارسال کنید.

❌ برای لغو ثبت سفارش، دکمه «خروج» را بزنید.""",
        chat_keypad=input_kb()
    )


def set_target(m, text):
    uid = str(m.chat_id)
    order = ORDERS.get(uid)

    if not order:
        return

    link = normalize_link(text)

    if not link:
        if order["type"] == "کانال":
            title = "📌 آیدی کانال را ارسال کنید"

        elif order["type"] == "گروه":
            title = "📌 آیدی گروه را ارسال کنید"

        else:
            title = "📌 آیدی پیج روبینو را ارسال کنید"

        bot.send_message(
            uid,
            f"""❌ آیدی وارد شده نامعتبر است.

{title}

مثال:
@username

⚠️ فقط آیدی عمومی روبیکا را ارسال کنید.

❌ برای لغو، دکمه «خروج» را بزنید.""",
            chat_keypad=input_kb()
        )

        return

    order["target"] = link
    order["waiting"] = False
    order["username"] = get_username(m)

    save_orders()

    bot.send_message(
        uid,
        f"""✅ مقصد با موفقیت ثبت شد.

🛍 خدمت: {order["service"]}
📌 نوع: {order["type"]}
🔗 مقصد: {order["target"]}

💰 مبلغ: {order["price"]} تومان

💳 شماره کارت:
{CARD}

👤 به نام پوریا سمیعی

📸 بعد از واریز، عکس رسید را همینجا ارسال کنید.

⚠️ پس از ارسال رسید، برای ادمین ارسال می‌شود.""",
        chat_keypad=main_kb()
    )


def receipt_text(m, order):
    return f"""💰 سفارش پرداختی جدید

🛍 خدمت: {order["service"]}
📌 نوع: {order["type"]}
💰 مبلغ: {order["price"]} تومان

🔗 آیدی مقصد:
{order["target"]}

👤 یوزرنیم کاربر:
{order.get("username", "ندارد")}

🆔 شناسه کاربر:
{order.get("sender_id", "ندارد")}

🆔 چت کاربر:
{m.chat_id}

📸 رسید دریافت شد."""


def send_admin(m, order):
    if not ADMIN_ID:
        print("ADMIN ID NOT SET", flush=True)
        return False

    try:
        file_obj = getattr(m, "file", None)

        file_id = (
            getattr(file_obj, "id", None)
            or getattr(file_obj, "file_id", None)
        )

        if not file_id:
            print("FILE ID NOT FOUND", flush=True)
            return False

        url = bot.get_file(file_id)
        data = bot.download_file(url)

        if not data:
            print("FILE DOWNLOAD FAILED", flush=True)
            return False

        path = f"{BASE}/receipt.jpg"

        with open(path, "wb") as f:
            f.write(data)

        with open(path, "rb") as f:
            bot.send_photo(
                ADMIN_ID,
                f,
                text=receipt_text(m, order)
            )

        try:
            os.remove(path)
        except Exception:
            pass

        print("RECEIPT SENT TO ADMIN", flush=True)
        return True

    except Exception as e:
        print("RECEIPT ERROR:", repr(e), flush=True)
        return False


def is_media(m):
    try:
        if getattr(m, "file", None):
            return True

        if getattr(m, "photo", None):
            return True

        if getattr(m, "image", None):
            return True

    except Exception:
        pass

    return False


def file_received(m):
    uid = str(m.chat_id)
    order = ORDERS.get(uid)

    if not order:
        bot.send_message(
            uid,
            "❌ سفارش فعالی ندارید.",
            chat_keypad=main_kb()
        )
        return

    if not order.get("target"):
        bot.send_message(
            uid,
            "❌ ابتدا آیدی مقصد را ارسال کنید.",
            chat_keypad=input_kb()
        )
        return

    if order.get("receipt"):
        bot.send_message(
            uid,
            "⚠️ این رسید قبلاً دریافت شده است.",
            chat_keypad=main_kb()
        )
        return

    if send_admin(m, order):

        order["receipt"] = True
        order["receipt_message_id"] = str(
            getattr(m, "message_id", "")
        )

        save_orders()

        bot.send_message(
            uid,
            """✅ رسید دریافت شد و برای ادمین ارسال شد.

⏳ منتظر بررسی سفارش باشید.""",
            chat_keypad=main_kb()
        )

    else:
        bot.send_message(
            uid,
            f"""❌ عکس رسید ارسال نشد.

📸 لطفاً عکس رسید پرداخت را دوباره ارسال کنید.

اگر مشکل ادامه داشت:

📞 پشتیبانی:
{SUPPORT}""",
            chat_keypad=main_kb()
        )


def handle(m):
    global ADMIN_ID

    if not m:
        return

    uid = str(m.chat_id)
    text = (getattr(m, "text", "") or "").strip()

    # ادمین
    if text.startswith("/admin"):

        if ADMIN_ID and uid != str(ADMIN_ID):
            bot.send_message(
                uid,
                "❌ دسترسی ندارید."
            )
            return

        ADMIN_ID = uid
        save(ADMIN_FILE, uid)

        bot.send_message(
            uid,
            "✅ ادمین ذخیره شد."
        )
        return

    # استارت
    if text.startswith("/start"):

        if not ADMIN_ID:
            ADMIN_ID = uid
            save(ADMIN_FILE, uid)

        # اگر سفارش قبلی نیمه‌کاره بوده، پاک نشود
        # تا کاربر بتواند ادامه دهد.
        start(m)
        return

    # خروج از ثبت سفارش
    if text == "❌ خروج":
        cancel_order(m)
        return

    # اگر عکس/فایل است
    if is_media(m):
        file_received(m)
        return

    order = ORDERS.get(uid)

    # کاربر در مرحله ورود آیدی است
    if order and order.get("waiting"):

        if text:
            set_target(m, text)

        return

    # خدمات
    if text == "🛍 خدمات روبیکا":
        bot.send_message(
            uid,
            "🛍 خدمات روبیکا\n\nخدمت موردنظر را انتخاب کنید 👇",
            chat_keypad=services_kb()
        )
        return

    # کانال
    if text == "📣 افزایش کانال":
        bot.send_message(
            uid,
            """📣 تعرفه افزایش کانال

⚠️ مقصد باید کانال عمومی باشد.""",
            chat_keypad=price_kb(CHANNEL, "📣 ")
        )
        return

    # گروه
    if text == "👥 افزایش گروه":
        bot.send_message(
            uid,
            """👥 تعرفه افزایش گروه

⚠️ سقف سفارش گروه ۱۰,۰۰۰ عضو است.""",
            chat_keypad=price_kb(GROUP, "👥 ")
        )
        return

    # روبینو
    if text == "⭐ افزایش روبینو":
        bot.send_message(
            uid,
            """⭐ تعرفه افزایش روبینو

⚠️ مقصد باید پیج عمومی روبینو باشد.""",
            chat_keypad=price_kb(FOLLOWERS, "⭐ ")
        )
        return

    # قوانین
    if text == "📜 قوانین":
        bot.send_message(
            uid,
            f"""📜 قوانین ثبت سفارش

1️⃣ پس از ثبت سفارش، امکان لغو یا تغییر سفارش نیست.
2️⃣ آیدی صحیح مقصد را ارسال کنید.
3️⃣ مقصد باید عمومی باشد.
4️⃣ زمان انجام سفارش متغیر است.
5️⃣ پس از پرداخت، رسید را ارسال کنید.

📞 آیدی ادمین جهت مشکلات:
{SUPPORT}

🙏 باتشکر""",
            chat_keypad=main_kb()
        )
        return

    # پشتیبانی
    if text == "📞 پشتیبانی":
        bot.send_message(
            uid,
            f"""📞 پشتیبانی

👤 آیدی پشتیبانی:
{SUPPORT}""",
            chat_keypad=main_kb()
        )
        return

    # خدمات
    if text == "🔙 خدمات":
        bot.send_message(
            uid,
            "🛍 خدمات روبیکا",
            chat_keypad=services_kb()
        )
        return

    # اصلی
    if text == "🏠 منوی اصلی":
        start(m)
        return

    # انتخاب قیمت
    for prefix, typ in [
        ("📣 ", "کانال"),
        ("👥 ", "گروه"),
        ("⭐ ", "روبینو")
    ]:

        if text.startswith(prefix) and " — " in text:

            service, price = text[len(prefix):].split(
                " — ",
                1
            )

            new_order(
                m,
                service,
                price,
                typ
            )

            return

    bot.send_message(
        uid,
        "از دکمه‌های منو استفاده کنید 👇",
        chat_keypad=main_kb()
    )


def start_health_server():
    port = int(os.getenv("PORT", "10000"))

    class Handler(BaseHTTPRequestHandler):

        def do_GET(self):
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/plain; charset=utf-8"
            )
            self.end_headers()

            self.wfile.write(
                b"Rubika bot is running"
            )

        def log_message(self, format, *args):
            return

    server = HTTPServer(
        ("0.0.0.0", port),
        Handler
    )

    threading.Thread(
        target=server.serve_forever,
        daemon=True
    ).start()

    print(
        "HEALTH SERVER:",
        port,
        flush=True
    )


def run():
    if not TOKEN:
        raise RuntimeError(
            "RUBIKA_BOT_TOKEN is not set"
        )

    if bot is None:
        raise RuntimeError(
            "Bot could not be initialized"
        )

    start_health_server()

    print("================================", flush=True)
    print("BOT STARTED", flush=True)
    print(
        "ADMIN ID:",
        ADMIN_ID or "NOT SET",
        flush=True
    )
    print(
        "API:",
        bot.BASE_URL,
        flush=True
    )
    print("================================", flush=True)

    offset = read(OFFSET_FILE)

    while True:

        try:
            received, next_offset = get_updates(offset)

            if next_offset and next_offset != offset:
                offset = next_offset
                save(OFFSET_FILE, offset)

            for update in received:
                try:
                    message = update.to_message()

                    if message:
                        handle(message)

                except Exception as e:
                    print(
                        "UPDATE ERROR:",
                        repr(e),
                        flush=True
                    )

            if not received:
                time.sleep(1)

        except exceptions.RubiBotAccessError:
            print(
                "INVALID_ACCESS",
                flush=True
            )
            time.sleep(10)

        except KeyboardInterrupt:
            print(
                "BOT STOPPED",
                flush=True
            )
            break

        except Exception as e:
            print(
                "MAIN ERROR:",
                repr(e),
                flush=True
            )
            time.sleep(5)


if __name__ == "__main__":

    while True:
        try:
            run()

        except KeyboardInterrupt:
            print(
                "BOT STOPPED",
                flush=True
            )
            break

        except Exception as e:
            print(
                "RESTARTING:",
                repr(e),
                flush=True
            )
            time.sleep(5)
