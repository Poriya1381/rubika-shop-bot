from rubibot import RubiBot, types, updates
import os
import time
import json
import re
import requests
from threading import Thread, Lock
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _install_exception_hooks():
    import sys
    import threading

    def _main_excepthook(exc_type, exc_value, exc_tb):
        print("UNCAUGHT:", repr(exc_value))
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    def _thread_excepthook(args):
        print("THREAD ERROR:", repr(args.exc_value))

    sys.excepthook = _main_excepthook
    if hasattr(threading, "excepthook"):
        threading.excepthook = _thread_excepthook

# =========================
# CONFIG
# =========================

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

OFFSET_FILE = os.path.join(DATA_DIR, "offset.txt")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
READY_FILE = os.path.join(DATA_DIR, "ready.flag")

TOKEN = "CDBECG0UXQGRRZSSDLFQSTKDIJEHEUXGFUWQOPYPLJBBMZFYAFIKMPSEBFUIWCLH"
CARD = os.getenv("CARD_NUMBER", "6219861932569709")

SUPPORT = os.getenv("SUPPORT_USERNAME", "@Poriysmeii")
CODE = "@PoriyBot"

ADMINS = {
    "u0KYDRB070eb6d2f015b56edb5476dcd",
    "b0KYDRB0BBLs0d5ad48d891eca78ebfa"
}

PORT = int(os.getenv("PORT", "10000"))

BASE = "data"
os.makedirs(BASE, exist_ok=True)

OF = f"{BASE}/offset.txt"
DF = f"{BASE}/orders.json"
READY = f"{BASE}/ready.flag"

API = f"https://botapi.rubika.ir/v3/{TOKEN}"

bot = RubiBot(TOKEN)


# =========================
# PERFORMANCE / RESILIENCE
# =========================

POLL_LIMIT = 100

# کوتاه برای پاسخ سریع؛ قطع اینترنت هم سریع تشخیص داده می‌شود.
REQUEST_TIMEOUT = (2, 8)
EMPTY_POLL_DELAY = 0.02

# فقط هنگام خطای واقعی شبکه/API استفاده می‌شود.
BACKOFF_MIN = 0.20
BACKOFF_MAX = 5.0

# پردازش پیام‌ها از polling جداست.
WORKERS = 96
SEND_WORKERS = 48

executor = ThreadPoolExecutor(
    max_workers=WORKERS,
    thread_name_prefix="update"
)

send_executor = ThreadPoolExecutor(
    max_workers=SEND_WORKERS,
    thread_name_prefix="send"
)

http = requests.Session()
try:
    from requests.adapters import HTTPAdapter
    import socket
    _adapter = HTTPAdapter(pool_connections=128, pool_maxsize=128, max_retries=0)
    http.mount("http://", _adapter)
    http.mount("https://", _adapter)
except Exception:
    pass
http.headers.update({
    "Content-Type": "application/json",
    "Connection": "keep-alive",
    "User-Agent": "RubikaShopBot/2.0"
})

orders_lock = Lock()
offset_lock = Lock()

state_lock = Lock()
last_poll_ok = time.monotonic()
last_message_at = 0.0


# =========================
# FILE
# =========================

def read(path, default=""):
    try:
        with open(path, "r", encoding="utf-8") as f:
            value = f.read().strip()
            return value if value else default
    except Exception:
        return default


def write(path, value):
    tmp = path + ".tmp"

    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(str(value))

        os.replace(tmp, path)
        return True

    except Exception as e:
        print("WRITE:", repr(e))
        return False


def valid_offset(x):
    return bool(
        x
        and isinstance(x, str)
        and len(x) < 500
    )


# =========================
# ORDERS
# =========================

try:
    ORDERS = json.loads(
        read(DF, "{}")
    )

    if not isinstance(ORDERS, dict):
        ORDERS = {}

except Exception:
    ORDERS = {}


def save_orders():
    with orders_lock:
        tmp = DF + ".tmp"

        try:
            with open(
                tmp,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    ORDERS,
                    f,
                    ensure_ascii=False,
                    separators=(",", ":")
                )

            os.replace(tmp, DF)

        except Exception as e:
            print("SAVE:", repr(e))


# =========================
# KEYBOARD
# =========================

def kb(rows):

    k = types.ChatKeypad(
        resize_keyboard=True
    )

    for row in rows:

        r = types.KeypadRow()

        for text, data in row:

            r.add(
                types.KeypadSimpleButton(
                    text,
                    data
                )
            )

        k.add(r)

    return k


MAIN = kb([
    [("🛍 خدمات", "services")],
    [("📦 پیگیری", "track"), ("🧾 سفارش‌ها", "orders")],
    [("📜 قوانین", "rules"), ("📞 پشتیبانی", "support")]
])


SERV = kb([
    [("📣 کانال", "channel"), ("👥 گروه", "group")],
    [("⭐ فالور", "followers")],
    [("ℹ️ توضیحات", "desc")],
    [("🏠 اصلی", "home")]
])


ADMIN_KB = kb([
    [("📋 جدید", "new"), ("🔵 درحال انجام", "work")],
    [("🟢 تکمیل", "done"), ("🔴 لغوشده", "cancelled")],
    [("🗑 حذف لغوشده", "clear")],
    [("🏠 اصلی", "home")]
])


# =========================
# PRICES
# =========================

CHANNEL = [
    "100 — 20,000",
    "500 — 60,000",
    "1,000 — 110,000",
    "5,000 — 500,000",
    "10,000 — 950,000",
    "15,000 — 1.600.000"
]


FOLLOWERS = [
    "1,000 — 15,000",
    "10,000 — 100,000",
    "50,000 — 450,000",
    "100,000 — 800,000",
    "150,000 — 1.600.000"
]


# =========================
# SEND
# =========================

def _mark_poll_ok():
    global last_poll_ok
    with state_lock:
        last_poll_ok = time.monotonic()


def send(uid, text, key=MAIN):
    """ارسال مقاوم با retry کوتاه و بدون نشت exception."""
    uid = str(uid)
    delays = (0.0, 0.05, 0.20, 0.50)

    for attempt, delay in enumerate(delays):
        if delay:
            time.sleep(delay)

        try:
            bot.send_message(
                uid,
                str(text),
                chat_keypad=key
            )
            return True
        except Exception as e:
            print(
                "SEND:",
                uid,
                "attempt=", attempt + 1,
                repr(e)
            )

    return False


def queue_send(uid, text, key=MAIN):
    """ارسال فوری؛ از صف دوم استفاده نمی‌کند تا پیام کاربر معطل نشود."""
    try:
        return send(uid, text, key)
    except Exception as e:
        print("SEND_QUEUE:", repr(e))
        return False


def admin_send(text, key=ADMIN_KB):
    for admin in ADMINS:
        queue_send(admin, text, key)


# =========================
# USERS
# =========================

def is_admin(m):

    uid = str(
        getattr(m, "chat_id", "") or ""
    )

    sid = str(
        getattr(m, "sender_id", "") or ""
    )

    return (
        uid in ADMINS
        or sid in ADMINS
    )


def start(m):

    send(
        m.chat_id,
        "🛍 فروشگاه روبیکا\n\n👇 انتخاب کنید:"
    )


# =========================
# HELPERS
# =========================

def oid(o):

    try:
        return int(
            o.get("id", 0)
        )

    except Exception:
        return 0


def num(x):

    try:

        return int(
            str(x)
            .replace(",", "")
            .replace(".", "")
            .replace(" تومان", "")
            .strip()
        )

    except Exception:
        return 0


def money(x):
    return f"{num(x):,}"


def get_user_orders(uid):

    uid = str(uid)

    with orders_lock:

        return [
            o for o in ORDERS.values()
            if str(o.get("chat_id")) == uid
        ]


def last_order(uid):

    orders = get_user_orders(uid)

    if not orders:
        return None

    return max(
        orders,
        key=oid
    )


# =========================
# USERNAME
# =========================

def get_username(m):

    try:

        c = bot.get_chat(
            str(m.chat_id)
        )

        u = getattr(
            c,
            "username",
            None
        )

        if u:
            return "@" + str(u).lstrip("@")

    except Exception:
        pass

    return "ندارد"


def normalize_username(text):

    text = text.strip()

    if re.fullmatch(
        r"@[A-Za-z0-9_]{3,64}",
        text
    ):
        return text

    m = re.fullmatch(
        r"https?://(?:www\.)?"
        r"(?:rubika\.ir|web\.rubika\.ir)/"
        r"([A-Za-z0-9_]{3,64})/?",
        text,
        re.I
    )

    if m:
        return "@" + m.group(1)

    return None


# =========================
# PRICES
# =========================

def show_prices(
    uid,
    items,
    prefix,
    title
):

    rows = [
        [(prefix + x, "price")]
        for x in items
    ]

    rows.append([
        ("🔙 خدمات", "services"),
        ("🏠 اصلی", "home")
    ])

    send(
        uid,
        title,
        kb(rows)
    )


def extract_price(text):

    m = re.search(
        r"(\d[\d,\.]*)\s*[—\-–]\s*([\d,\.]+)",
        text
    )

    if not m:
        return None

    count = m.group(1)
    price = m.group(2)

    if text.startswith("📣"):
        typ = "کانال"

    elif text.startswith("👥"):
        typ = "گروه"

    elif text.startswith("⭐"):
        typ = "روبینو"

    else:
        return None

    return typ, count, price


# =========================
# ORDER
# =========================

def create_order(
    m,
    service,
    price,
    typ
):

    uid = str(m.chat_id)

    # API call خارج از lock انجام می‌شود تا یک درخواست کند
    # کل سیستم سفارش‌ها را متوقف نکند.
    username = get_username(m)

    with orders_lock:

        ids = [
            oid(o)
            for o in ORDERS.values()
        ]

        n = max(
            ids + [1000]
        ) + 1

        ORDERS[str(n)] = {

            "id": n,

            "chat_id": uid,

            "sender_id": str(
                getattr(
                    m,
                    "sender_id",
                    ""
                ) or uid
            ),

            "username": username,

            "service": service,

            "type": typ,

            "price": price,

            "final": num(price),

            "discount": 0,

            "target": "",

            "status": "در انتظار بررسی",

            "waiting": 1,

            "discount_wait": 0,

            "receipt": 0,

            "created": int(
                time.time()
            )
        }

    save_orders()

    send(
        uid,
        "📌 یوزرنیم مقصد را ارسال کنید.\n\n"
        "@username\n\n"
        "یا لینک روبیکا را ارسال کنید.",
        kb([
            [("❌ خروج", "cancel")],
            [("🏠 اصلی", "home")]
        ])
    )


def payment(uid, o):

    send(
        uid,
        f"""💳 پرداخت سفارش #{o["id"]}

🛍 {o["service"]}
📌 {o["type"]}
🔗 {o["target"]}

💰 مبلغ: {money(o["final"])} تومان

💳 کارت:
{CARD}

📸 رسید را به صورت عکس ارسال کنید."""
    )


# =========================
# TARGET
# =========================

def set_target(m, text):

    uid = str(m.chat_id)

    o = last_order(uid)

    if not o or not o.get("waiting"):
        return

    username = normalize_username(text)

    if not username:

        send(
            uid,
            "❌ یوزرنیم نامعتبر است.\n\n"
            "مثال:\n@Poriysmeii"
        )

        return

    o["target"] = username
    o["waiting"] = 0
    o["discount_wait"] = 1

    save_orders()

    send(
        uid,
        f"✅ مقصد ثبت شد:\n{username}\n\n"
        "🎁 کد تخفیف دارید؟",
        kb([
            [("❌ ندارم", "no_discount")],
            [("❌ خروج", "cancel")]
        ])
    )


# =========================
# DISCOUNT
# =========================

def discount(m, text):

    uid = str(m.chat_id)

    o = last_order(uid)

    if not o:
        return

    if text.strip().lower() != CODE.lower():

        send(
            uid,
            "❌ کد تخفیف نامعتبر است.",
            kb([
                [("❌ ندارم", "no_discount")],
                [("❌ خروج", "cancel")]
            ])
        )

        return

    price = num(o["price"])

    off = price * 20 // 100

    o["discount"] = off
    o["final"] = price - off
    o["discount_wait"] = 0

    save_orders()

    payment(uid, o)


# =========================
# MEDIA
# =========================

def is_media(m):

    return bool(
        getattr(m, "file", None)
        or getattr(m, "photo", None)
        or getattr(m, "image", None)
    )


# =========================
# RECEIPT
# =========================

def receipt(m):

    uid = str(m.chat_id)

    o = last_order(uid)

    if not o:

        send(
            uid,
            "❌ سفارش ندارید."
        )

        return

    if o.get("receipt"):

        send(
            uid,
            "⚠️ رسید قبلاً ارسال شده."
        )

        return

    path = f"{BASE}/receipt_{o['id']}.jpg"

    try:

        f = getattr(
            m,
            "file",
            None
        )

        fid = (
            getattr(f, "id", None)
            or getattr(f, "file_id", None)
        )

        if not fid:

            p = getattr(
                m,
                "photo",
                None
            )

            fid = (
                getattr(p, "id", None)
                or getattr(p, "file_id", None)
            )

        if not fid:
            raise Exception(
                "FILE_ID_NOT_FOUND"
            )

        file_url = bot.get_file(fid)

        if not file_url:
            raise Exception(
                "GET_FILE_FAILED"
            )

        data = bot.download_file(
            file_url
        )

        if not data:
            raise Exception(
                "DOWNLOAD_FAILED"
            )

        with open(
            path,
            "wb"
        ) as fp:

            fp.write(data)

        caption = (
            f"💰 سفارش #{o['id']}\n"
            f"🛍 {o['service']}\n"
            f"📌 {o['type']}\n"
            f"🔗 {o['target']}\n"
            f"💰 {money(o['final'])} تومان\n"
            f"👤 {o['username']}"
        )

        sent = False

        for admin in ADMINS:

            try:

                bot.send_photo(
                    admin,
                    path,
                    text=caption
                )

                sent = True

            except Exception as e:

                print(
                    "SEND_PHOTO:",
                    repr(e)
                )

                try:

                    bot.send_file(
                        admin,
                        path,
                        text=caption
                    )

                    sent = True

                except Exception as e2:

                    print(
                        "SEND_FILE:",
                        repr(e2)
                    )

        if not sent:
            raise Exception(
                "SEND_RECEIPT_FAILED"
            )

        o["receipt"] = 1

        save_orders()

        send(
            uid,
            "✅ رسید با موفقیت دریافت شد.\n"
            "⏳ در انتظار بررسی ادمین."
        )

    except Exception as e:

        print(
            "RECEIPT:",
            repr(e)
        )

        send(
            uid,
            "❌ ارسال رسید ناموفق بود.\n"
            "لطفاً عکس را دوباره ارسال کنید."
        )

    finally:

        try:
            os.remove(path)
        except Exception:
            pass


# =========================
# ADMIN
# =========================

def admin_buttons(o):

    n = o["id"]

    if o["status"] == "در انتظار بررسی":

        return kb([
            [
                (f"🔵 شروع #{n}", "start"),
                (f"🟢 تکمیل #{n}", "done")
            ],
            [
                (f"🔴 لغو #{n}", "cancel")
            ],
            [
                ("🔙 پنل مدیریت", "admin")
            ]
        ])

    if o["status"] == "در حال انجام":

        return kb([
            [
                (f"🟢 تکمیل #{n}", "done"),
                (f"🔴 لغو #{n}", "cancel")
            ],
            [
                ("🔙 پنل مدیریت", "admin")
            ]
        ])

    return ADMIN_KB


def admin_list(
    status,
    admin_id
):

    with orders_lock:

        orders = sorted(
            [
                o for o in ORDERS.values()
                if o.get("status") == status
            ],
            key=oid,
            reverse=True
        )

    if not orders:

        send(
            admin_id,
            f"📭 سفارشی با وضعیت «{status}» وجود ندارد.",
            ADMIN_KB
        )

        return

    for o in orders[:30]:

        send(
            admin_id,
            f"""📦 سفارش #{o["id"]}

🛍 {o["service"]}
📌 {o["type"]}
🔗 {o["target"] or "هنوز ارسال نشده"}
💰 {money(o["final"])} تومان
👤 {o["username"]}
📊 {o["status"]}""",
            admin_buttons(o)
        )


def change_status(
    order_id,
    status,
    admin_id
):

    with orders_lock:

        o = next(
            (
                x for x in ORDERS.values()
                if str(x.get("id"))
                == str(order_id)
            ),
            None
        )

        if not o:
            send(
                admin_id,
                f"❌ سفارش #{order_id} پیدا نشد.",
                ADMIN_KB
            )

            return

        o["status"] = status
        o["waiting"] = 0
        o["discount_wait"] = 0

    save_orders()

    # پاسخ مشتری بدون معطل کردن ادمین
    queue_send(
        o["chat_id"],
        f"📦 سفارش #{order_id}\n📊 وضعیت: {status}"
    )

    send(
        admin_id,
        f"✅ سفارش #{order_id} → {status}",
        ADMIN_KB
    )


# =========================
# ADMIN COMMANDS
# =========================

def admin_command(
    text,
    admin_id
):

    if text in (
        "/admin",
        "🔙 پنل مدیریت",
        "⚙️ پنل مدیریت"
    ):

        send(
            admin_id,
            "⚙️ پنل مدیریت",
            ADMIN_KB
        )

        return True

    if text == "📋 جدید":

        admin_list(
            "در انتظار بررسی",
            admin_id
        )

        return True

    if text == "🔵 درحال انجام":

        admin_list(
            "در حال انجام",
            admin_id
        )

        return True

    if text == "🟢 تکمیل":

        admin_list(
            "تکمیل شد",
            admin_id
        )

        return True

    if text == "🔴 لغوشده":

        admin_list(
            "لغو شد",
            admin_id
        )

        return True

    if text == "🗑 حذف لغوشده":

        with orders_lock:

            keys = [
                k for k, o in ORDERS.items()
                if o.get("status") == "لغو شد"
            ]

            for k in keys:
                del ORDERS[k]

        save_orders()

        send(
            admin_id,
            f"🗑 {len(keys)} سفارش حذف شد.",
            ADMIN_KB
        )

        return True

    m = re.match(
        r"^🔵 شروع\s*#(\d+)$",
        text
    )

    if m:

        change_status(
            m.group(1),
            "در حال انجام",
            admin_id
        )

        return True

    m = re.match(
        r"^🟢 تکمیل\s*#(\d+)$",
        text
    )

    if m:

        change_status(
            m.group(1),
            "تکمیل شد",
            admin_id
        )

        return True

    m = re.match(
        r"^🔴 لغو\s*#(\d+)$",
        text
    )

    if m:

        change_status(
            m.group(1),
            "لغو شد",
            admin_id
        )

        return True

    return False


# =========================
# MESSAGE HANDLER
# =========================

def handle(m):

    if not m:
        return

    uid = str(
        getattr(m, "chat_id", "") or ""
    )

    sid = str(
        getattr(m, "sender_id", "") or ""
    )

    text = (
        getattr(m, "text", "") or ""
    ).strip()

    # Avoid logging every message: hosted log I/O can noticeably add latency.

    # ADMIN
    if is_admin(m):

        if admin_command(
            text,
            uid
        ):
            return

    # START
    if text.startswith("/start"):

        start(m)
        return

    # CANCEL
    if text in (
        "❌ خروج",
        "❌ لغو"
    ):

        with orders_lock:

            for key, o in list(
                ORDERS.items()
            ):

                if (
                    str(o.get("chat_id"))
                    == uid
                    and (
                        o.get("waiting")
                        or o.get("discount_wait")
                    )
                ):
                    del ORDERS[key]

        save_orders()

        send(
            uid,
            "✅ لغو شد."
        )

        return

    # SERVICES
    if text == "🛍 خدمات":

        send(
            uid,
            "🛍 خدمات روبیکا",
            SERV
        )

        return

    # DESCRIPTION
    if text == "ℹ️ توضیحات":

        send(
            uid,
            "ℹ️ خدمات دارای پشتیبانی هستند.",
            kb([
                [("🛒 خرید", "buy")],
                [("🏠 اصلی", "home")]
            ])
        )

        return

    # BUY
    if text == "🛒 خرید":

        send(
            uid,
            "🛍 خدمات",
            SERV
        )

        return

    # CHANNEL
    if text == "📣 کانال":

        show_prices(
            uid,
            CHANNEL,
            "📣 ",
            "📣 تعرفه کانال"
        )

        return

    # GROUP
    if text == "👥 گروه":

        show_prices(
            uid,
            CHANNEL,
            "👥 ",
            "👥 تعرفه گروه"
        )

        return

    # FOLLOWERS
    if text == "⭐ فالور":

        show_prices(
            uid,
            FOLLOWERS,
            "⭐ ",
            "⭐ تعرفه فالور"
        )

        return

    # PRICE
    price = extract_price(text)

    if price:

        typ, service, amount = price

        create_order(
            m,
            service,
            amount,
            typ
        )

        return

    # LAST ORDER
    o = last_order(uid)

    # NO DISCOUNT
    if text == "❌ ندارم":

        if o and o.get("discount_wait"):

            o["discount_wait"] = 0
            o["final"] = num(
                o["price"]
            )

            save_orders()

            payment(
                uid,
                o
            )

        return

    # RECEIPT
    if is_media(m):

        receipt(m)
        return

    # DISCOUNT
    if o and o.get("discount_wait"):

        discount(
            m,
            text
        )

        return

    # TARGET
    if o and o.get("waiting"):

        set_target(
            m,
            text
        )

        return

    # TRACK
    if text == "📦 پیگیری":

        orders = [
            o for o in get_user_orders(uid)
            if o.get("status")
            == "در حال انجام"
        ]

        send(
            uid,
            "📦 سفارش‌ها:\n\n"
            +
            (
                "\n".join(
                    f"#{o['id']} | "
                    f"{o['service']} | "
                    f"{o['status']}"
                    for o in orders
                )
                or "📭 ندارد."
            )
        )

        return

    # ORDERS
    if text == "🧾 سفارش‌ها":

        orders = sorted(
            get_user_orders(uid),
            key=oid,
            reverse=True
        )[:20]

        send(
            uid,
            "🧾 سفارش‌ها:\n\n"
            +
            (
                "\n".join(
                    f"#{o['id']} | "
                    f"{o['service']} | "
                    f"{o['status']}"
                    for o in orders
                )
                or "📭 ندارد."
            )
        )

        return

    # RULES
    if text == "📜 قوانین":

        send(
            uid,
            "📜 قوانین:\n"
            "1️⃣ آیدی صحیح ارسال کنید.\n"
            "2️⃣ مقصد عمومی باشد.\n"
            "3️⃣ پس از پرداخت رسید ارسال شود."
        )

        return

    # SUPPORT
    if text == "📞 پشتیبانی":

        send(
            uid,
            SUPPORT
        )

        return

    # HOME
    if text == "🏠 اصلی":

        start(m)
        return

    if is_admin(m):
        return

    send(
        uid,
        "👇 از منو انتخاب کنید."
    )


# =========================
# UPDATE
# =========================

def process_update(item):
    global last_message_at

    try:
        m = updates.Update(
            item
        ).to_message()

        if m:
            with state_lock:
                last_message_at = time.monotonic()

            handle(m)

    except Exception as e:
        # پیام خراب نباید polling را متوقف کند.
        print(
            "UPDATE:",
            repr(e)
        )


# =========================
# API
# =========================

def api_updates(offset=""):
    params = {"limit": POLL_LIMIT}

    if offset:
        params["offset_id"] = offset

    response = None

    try:
        response = http.post(
            f"{API}/getUpdates",
            json=params,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"HTTP {response.status_code}"
            )

        data = response.json()

    except (requests.RequestException, ValueError) as e:
        raise RuntimeError(
            f"NETWORK/JSON: {e}"
        ) from e

    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass

    if not isinstance(data, dict):
        raise RuntimeError("INVALID_JSON")

    if data.get("status") != "OK":
        raise RuntimeError(
            str(
                data.get("status_det")
                or data
            )
        )

    x = data.get("data") or {}

    if not isinstance(x, dict):
        raise RuntimeError("INVALID_DATA")

    arr = x.get("updates") or []

    new_offset = (
        x.get("next_offset_id")
        or offset
    )

    _mark_poll_ok()

    return arr, new_offset


# =========================
# CLEAR OLD
# =========================

def clear_old_updates():

    print(
        "CLEARING OLD UPDATES..."
    )

    offset = read(
        OF,
        ""
    )

    if not valid_offset(offset):
        offset = ""

    loops = 0

    while loops < 1000:

        loops += 1

        try:

            arr, new_offset = api_updates(
                offset
            )

            if (
                new_offset
                and new_offset != offset
            ):

                offset = new_offset

                write(
                    OF,
                    offset
                )

            if not arr:
                break

            print(
                "OLD UPDATES SKIPPED:",
                len(arr)
            )

            # بدون sleep اضافی

        except Exception as e:

            print(
                "CLEAR ERROR:",
                repr(e)
            )

            break

    if offset:
        write(
            OF,
            offset
        )

    write(
        READY,
        str(int(time.time()))
    )

    print(
        "OLD UPDATES CLEARED"
    )


# =========================
# FAST POLLING
# =========================

def polling():
    """Low-latency polling loop with bounded backoff and safe update dispatch."""
    global last_poll_ok

    backoff = BACKOFF_MIN
    initialized = False

    while True:
        try:
            with offset_lock:
                offset = read(OFFSET_FILE, "").strip()

            if not initialized:
                if not offset:
                    clear_old_updates()
                    with offset_lock:
                        offset = read(OFFSET_FILE, "").strip()
                initialized = True

            arr, next_offset = api_updates(offset)

            # Successful API contact: immediately return to minimum latency.
            backoff = BACKOFF_MIN
            _mark_poll_ok()

            if next_offset:
                with offset_lock:
                    write(OFFSET_FILE, str(next_offset))
                offset = str(next_offset)

            if not arr:
                time.sleep(EMPTY_POLL_DELAY)
                continue

            # Dispatch immediately; don't process updates serially.
            for upd in arr:
                try:
                    executor.submit(process_update, upd)
                except Exception as e:
                    print("DISPATCH ERROR:", e)

        except KeyboardInterrupt:
            raise
        except Exception as e:
            print("POLL ERROR:", repr(e))
            time.sleep(backoff)
            backoff = min(BACKOFF_MAX, max(BACKOFF_MIN, backoff * 1.6))

class Handler(
    BaseHTTPRequestHandler
):

    def do_GET(self):

        self.send_response(
            200
        )

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )

        self.end_headers()

        self.wfile.write(
            b"OK"
        )

    def do_HEAD(self):

        self.send_response(
            200
        )

        self.end_headers()

    def log_message(
        self,
        *args
    ):
        pass

def web_server():

    while True:

        try:

            server = ThreadingHTTPServer(
                ("0.0.0.0", PORT),
                Handler
            )
            server.daemon_threads = True
            server.allow_reuse_address = True

            print(
                "WEB:",
                PORT
            )

            server.serve_forever()

        except Exception as e:

            print(
                "WEB ERROR:",
                repr(e)
            )

            time.sleep(2)


# =========================
# WATCHDOG
# =========================

def watchdog():
    """
    اگر polling واقعاً گیر کند، process را خارج می‌کند تا Render
    آن را دوباره اجرا کند. قطع عادی اینترنت توسط polling مدیریت می‌شود.
    """
    while True:
        time.sleep(30)

        with state_lock:
            silent_for = time.monotonic() - last_poll_ok

        if silent_for > 180:
            print(
                "WATCHDOG: polling stalled for",
                round(silent_for),
                "seconds -> restart"
            )
            os._exit(1)


# =========================
# MAIN
# =========================

def main():
    _install_exception_hooks()
    if not TOKEN:
        raise RuntimeError(
            "TOKEN environment variable is missing. "
            "Set TOKEN in Render Environment Variables."
        )

    Thread(
        target=web_server,
        daemon=True,
        name="web-server"
    ).start()

    Thread(
        target=watchdog,
        daemon=True,
        name="watchdog"
    ).start()

    polling()


if __name__ == "__main__":
    while True:
        try:
            main()

        except KeyboardInterrupt:
            print("BOT STOPPED")
            break

        except SystemExit:
            raise

        except Exception as e:
            print("FATAL:", repr(e))
            time.sleep(1)
