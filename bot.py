from rubibot import RubiBot, types, updates, exceptions
import os
import time
import json
import re
import requests
from threading import Thread, RLock
from http.server import BaseHTTPRequestHandler, HTTPServer

import wallet

TOKEN = os.getenv("TOKEN", "").strip()

ADMINS = {
    "u0KYDRB070eb6d2f015b56edb5476dcd",
    "b0KYDRB0BBLs0d5ad48d891eca78ebfa"
}

CARD = "6219861932569709"
SUPPORT = "@Poriysmeii"
CODE = "@PoriyBot"

PORT = int(os.getenv("PORT", "10000"))

BASE = "data"
os.makedirs(BASE, exist_ok=True)

OF = f"{BASE}/offset.txt"
DF = f"{BASE}/orders.json"
READY = f"{BASE}/ready.flag"
QUEUE = f"{BASE}/pending_updates.json"

API = f"https://botapi.rubika.ir/v3/{TOKEN}"

bot = RubiBot(TOKEN)

http = requests.Session()
http.headers.update({"Content-Type": "application/json"})

BACKOFF_MIN = 1
BACKOFF_MAX = 60

POLL_LIMIT = 100
REQUEST_TIMEOUT = (5, 30)

MAX_QUEUE_AGE = 20 * 60
LOCK = RLock()


def read(path, default=""):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip() or default
    except:
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
        isinstance(x, str)
        and x
        and len(x) < 500
    )


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            x = json.load(f)

        return x

    except:
        return default


def save_json(path, data):
    tmp = path + ".tmp"

    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                separators=(",", ":")
            )

        os.replace(tmp, path)
        return True

    except Exception as e:
        print("JSON SAVE:", repr(e))
        return False


try:
    ORDERS = json.loads(read(DF, "{}"))

    if not isinstance(ORDERS, dict):
        ORDERS = {}

except:
    ORDERS = {}


def save_orders():
    save_json(DF, ORDERS)


def kb(rows):
    k = types.ChatKeypad(resize_keyboard=True)

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
    [("💰 کیف پول", "wallet")],
    [("📦 پیگیری", "track"), ("🧾 سفارش‌ها", "orders")],
    [("📜 قوانین", "rules"), ("📞 پشتیبانی", "support")]
])


SERV = kb([
    [("📣 کانال", "channel"), ("👥 گروه", "group")],
    [("⭐ فالور", "followers")],
    [("ℹ️ توضیحات", "desc")],
    [("🏠 اصلی", "home")]
])


WALLET_KB = kb([
    [("💳 شارژ حساب", "charge")],
    [("💰 موجودی", "balance")],
    [("📜 تراکنش‌ها", "transactions")],
    [("🏠 اصلی", "home")]
])


ADMIN_KB = kb([
    [("📋 جدید", "new"), ("🔵 درحال انجام", "work")],
    [("🟢 تکمیل", "done"), ("🔴 لغوشده", "cancelled")],
    [("💰 شارژها", "charges")],
    [("🗑 حذف لغوشده", "clear")],
    [("🏠 اصلی", "home")]
])


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


def send(uid, text, key=MAIN):
    for attempt in range(3):
        try:
            bot.send_message(
                str(uid),
                str(text),
                chat_keypad=key
            )

            return True

        except Exception as e:
            print("SEND:", repr(e))
            time.sleep(min(2 ** attempt, 5))

    return False


def admin_send(text, key=ADMIN_KB):
    for admin in ADMINS:
        send(admin, text, key)


def is_admin(m):
    uid = str(getattr(m, "chat_id", "") or "")
    sid = str(getattr(m, "sender_id", "") or "")

    return uid in ADMINS or sid in ADMINS


def start(m):
    send(
        m.chat_id,
        "🛍 فروشگاه روبیکا\n\n👇 انتخاب کنید:"
    )


def oid(o):
    try:
        return int(o.get("id", 0))
    except:
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
    except:
        return 0


def money(x):
    return f"{num(x):,}"


def get_user_orders(uid):
    return [
        o for o in ORDERS.values()
        if str(o.get("chat_id")) == str(uid)
    ]


def last_order(uid):
    orders = get_user_orders(uid)
    return max(orders, key=oid) if orders else None


def get_username(m):
    try:
        c = bot.get_chat(str(m.chat_id))
        u = getattr(c, "username", None)

        if u:
            return "@" + str(u).lstrip("@")

    except:
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


def show_prices(uid, items, prefix, title):
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


def create_order(m, service, price, typ):
    uid = str(m.chat_id)

    ids = [
        oid(o)
        for o in ORDERS.values()
    ]

    n = max(ids + [1000]) + 1

    ORDERS[str(n)] = {
        "id": n,
        "chat_id": uid,
        "sender_id": str(
            getattr(m, "sender_id", "") or uid
        ),
        "username": get_username(m),
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
        "wallet_used": 0,
        "cash_due": 0,
        "created": int(time.time())
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
    total = num(o["final"])
    balance = wallet.balance(uid)

    used = min(total, balance)
    due = total - used

    o["wallet_used"] = used
    o["cash_due"] = due

    save_orders()

    if due <= 0:
        ok, new_balance = wallet.remove(
            uid,
            used,
            f"خرید سفارش #{o['id']}"
        )

        if not ok:
            send(uid, "❌ خطا در برداشت از کیف پول.")
            return

        o["receipt"] = 1
        o["status"] = "در انتظار بررسی"
        save_orders()

        send(
            uid,
            f"💳 سفارش #{o['id']}\n\n"
            f"💰 مبلغ: {money(total)} تومان\n"
            f"➖ برداشت از کیف پول: {money(used)} تومان\n"
            f"💵 موجودی جدید: {money(new_balance)} تومان\n\n"
            "✅ مبلغ کامل از کیف پول پرداخت شد."
        )

        for admin in ADMINS:
            send(
                admin,
                f"💰 سفارش #{o['id']}\n\n"
                f"🛍 {o['service']}\n"
                f"📌 {o['type']}\n"
                f"🔗 {o['target']}\n"
                f"💰 مبلغ: {money(total)} تومان\n"
                f"💳 پرداخت کامل از کیف پول\n"
                f"👤 {o['username']}",
                admin_buttons(o)
            )

        return

    send(
        uid,
        f"""💳 پرداخت سفارش #{o["id"]}

🛍 {o["service"]}
📌 {o["type"]}
🔗 {o["target"]}

💰 مبلغ سفارش: {money(total)} تومان
💵 موجودی کیف پول: {money(balance)} تومان

➖ برداشت از کیف پول: {money(used)} تومان
💳 مبلغ باقی‌مانده: {money(due)} تومان

💳 کارت:
{CARD}

📸 لطفاً مبلغ باقی‌مانده را واریز کنید
و رسید را به صورت عکس ارسال کنید."""
    )


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


def is_media(m):
    return bool(
        getattr(m, "file", None)
        or getattr(m, "photo", None)
        or getattr(m, "image", None)
    )


def receipt(m):
    uid = str(m.chat_id)
    o = last_order(uid)

    if not o:
        send(uid, "❌ سفارش ندارید.")
        return

    if o.get("receipt"):
        send(uid, "⚠️ رسید قبلاً ارسال شده.")
        return

    path = f"{BASE}/receipt_{o['id']}.jpg"

    try:
        f = getattr(m, "file", None)

        fid = (
            getattr(f, "id", None)
            or getattr(f, "file_id", None)
        )

        if not fid:
            p = getattr(m, "photo", None)

            fid = (
                getattr(p, "id", None)
                or getattr(p, "file_id", None)
            )

        if not fid:
            raise Exception("FILE_ID_NOT_FOUND")

        file_url = bot.get_file(fid)

        if not file_url:
            raise Exception("GET_FILE_FAILED")

        data = bot.download_file(file_url)

        if not data:
            raise Exception("DOWNLOAD_FAILED")

        with open(path, "wb") as fp:
            fp.write(data)

        total = num(o["final"])
        wallet_used = num(o.get("wallet_used", 0))
        cash_due = num(o.get("cash_due", total))

        caption = (
            f"💰 سفارش #{o['id']}\n"
            f"🛍 {o['service']}\n"
            f"📌 {o['type']}\n"
            f"🔗 {o['target']}\n"
            f"💰 کل: {money(total)} تومان\n"
            f"💳 از کیف پول: {money(wallet_used)} تومان\n"
            f"💵 پرداخت کارت: {money(cash_due)} تومان\n"
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
            raise Exception("SEND_RECEIPT_FAILED")

        if wallet_used > 0:
            ok, new_balance = wallet.remove(
                uid,
                wallet_used,
                f"خرید سفارش #{o['id']}"
            )

            if not ok:
                raise Exception(
                    "WALLET_DEBIT_FAILED"
                )
        else:
            new_balance = wallet.balance(uid)

        o["receipt"] = 1
        save_orders()

        send(
            uid,
            f"✅ رسید دریافت شد.\n"
            f"⏳ در انتظار بررسی ادمین.\n\n"
            f"💵 موجودی کیف پول: "
            f"{money(new_balance)} تومان"
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
        except:
            pass


def admin_buttons(o):
    n = o["id"]

    if o["status"] == "در انتظار بررسی":
        return kb([
            [
                (f"🔵 شروع #{n}", "start"),
                (f"🟢 تکمیل #{n}", "done")
            ],
            [(f"🔴 لغو #{n}", "cancel")],
            [("🔙 پنل مدیریت", "admin")]
        ])

    if o["status"] == "در حال انجام":
        return kb([
            [
                (f"🟢 تکمیل #{n}", "done"),
                (f"🔴 لغو #{n}", "cancel")
            ],
            [("🔙 پنل مدیریت", "admin")]
        ])

    return ADMIN_KB


def admin_list(status, admin_id):
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
💳 کیف پول: {money(o.get("wallet_used", 0))} تومان
👤 {o["username"]}
📊 {o["status"]}""",
            admin_buttons(o)
        )


def change_status(order_id, status, admin_id):
    o = next(
        (
            x for x in ORDERS.values()
            if str(x.get("id")) == str(order_id)
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

    send(
        o["chat_id"],
        f"📦 سفارش #{order_id}\n"
        f"📊 وضعیت: {status}"
    )

    send(
        admin_id,
        f"✅ سفارش #{order_id} → {status}",
        ADMIN_KB
    )


def wallet_menu(uid):
    bal = wallet.balance(uid)

    send(
        uid,
        f"💰 کیف پول شما\n\n"
        f"💵 موجودی: {money(bal)} تومان\n\n"
        "👇 انتخاب کنید:",
        WALLET_KB
    )


def wallet_transactions(uid):
    tx = wallet.transactions(uid)

    if not tx:
        send(
            uid,
            "📜 هنوز تراکنشی ثبت نشده.",
            WALLET_KB
        )
        return

    lines = []

    for x in tx:
        sign = "+" if x["type"] == "credit" else "-"
        lines.append(
            f"{sign}{money(x['amount'])} تومان"
            f" | {x['reason']}\n"
            f"💵 موجودی: {money(x['after'])}"
        )

    send(
        uid,
        "📜 تاریخچه کیف پول\n\n"
        + "\n\n".join(lines),
        WALLET_KB
    )


def begin_charge(uid):
    send(
        uid,
        f"""💳 شارژ حساب

💳 شماره کارت:
{CARD}

مبلغ موردنظر را به کارت بالا واریز کنید.

سپس فقط مبلغ واریزی را به صورت عدد ارسال کنید.

مثال:
500000

بعد از آن رسید را ارسال کنید.""",
        kb([
            [("❌ خروج", "cancel")],
            [("🏠 اصلی", "home")]
        ])
    )


def admin_charges(admin_id):
    charges = wallet.pending_charges()

    if not charges:
        send(
            admin_id,
            "📭 درخواست شارژ جدیدی وجود ندارد.",
            ADMIN_KB
        )
        return

    for c in charges[:30]:
        cid = c["id"]

        send(
            admin_id,
            f"""💰 درخواست شارژ #{cid}

👤 آیدی:
{c["chat_id"]}

💵 مبلغ:
{money(c["amount"])} تومان

📸 رسید: {"ارسال شده" if c.get("receipt") else "ارسال نشده"}""",
            kb([
                [
                    (f"🟢 تأیید شارژ #{cid}", "approve_charge"),
                    (f"🔴 رد شارژ #{cid}", "reject_charge")
                ],
                [("🔙 پنل مدیریت", "admin")]
            ])
        )


def admin_command(text, admin_id):
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

    if text == "💰 شارژها":
        admin_charges(admin_id)
        return True

    if text == "🗑 حذف لغوشده":
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

    m = re.fullmatch(
        r"شارژ\s+([A-Za-z0-9_]+)\s+([\d,\.]+)",
        text
    )

    if m:
        uid = m.group(1)
        amount = num(m.group(2))

        ok, bal = wallet.add(
            uid,
            amount,
            f"شارژ دستی ادمین"
        )

        if ok:
            send(
                admin_id,
                f"✅ حساب شارژ شد.\n\n"
                f"👤 {uid}\n"
                f"➕ {money(amount)} تومان\n"
                f"💵 موجودی: {money(bal)} تومان",
                ADMIN_KB
            )
        else:
            send(
                admin_id,
                "❌ مبلغ نامعتبر است.",
                ADMIN_KB
            )

        return True

    m = re.fullmatch(
        r"کسر\s+([A-Za-z0-9_]+)\s+([\d,\.]+)",
        text
    )

    if m:
        uid = m.group(1)
        amount = num(m.group(2))

        ok, bal = wallet.remove(
            uid,
            amount,
            "کسر دستی ادمین"
        )

        if ok:
            send(
                admin_id,
                f"✅ مبلغ کسر شد.\n\n"
                f"👤 {uid}\n"
                f"➖ {money(amount)} تومان\n"
                f"💵 موجودی: {money(bal)} تومان",
                ADMIN_KB
            )
        else:
            send(
                admin_id,
                f"❌ موجودی کافی نیست.\n"
                f"💵 موجودی فعلی: {money(bal)} تومان",
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
        te        m = re.match(
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

        m = re.match(
            r"^🟢 تأیید شارژ\s*#(\d+)$",
            text
        )

        if m:
            cid = m.group(1)

            ok, uid, amount, bal = wallet.approve_charge(cid)

            if ok:
                send(
                    admin_id,
                    f"✅ شارژ تأیید شد.\n\n"
                    f"👤 {uid}\n"
                    f"➕ {money(amount)} تومان\n"
                    f"💵 موجودی جدید: {money(bal)} تومان",
                    ADMIN_KB
                )

                send(
                    uid,
                    f"✅ شارژ حساب شما تأیید شد.\n\n"
                    f"➕ مبلغ: {money(amount)} تومان\n"
                    f"💰 موجودی جدید: {money(bal)} تومان"
                )

            else:
                send(
                    admin_id,
                    "❌ این درخواست شارژ قبلاً بررسی شده یا پیدا نشد.",
                    ADMIN_KB
                )

            return True

        m = re.match(
            r"^🔴 رد شارژ\s*#(\d+)$",
            text
        )

        if m:
            cid = m.group(1)

            ok, uid, amount = wallet.reject_charge(cid)

            if ok:
                send(
                    admin_id,
                    f"🔴 شارژ رد شد.\n\n"
                    f"👤 {uid}\n"
                    f"💵 مبلغ: {money(amount)} تومان",
                    ADMIN_KB
                )

                send(
                    uid,
                    f"❌ درخواست شارژ شما رد شد.\n\n"
                    f"💵 مبلغ درخواست: {money(amount)} تومان"
                )

            else:
                send(
                    admin_id,
                    "❌ این درخواست شارژ قبلاً بررسی شده یا پیدا نشد.",
                    ADMIN_KB
                )

            return True

        return False


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

    print(
        "MESSAGE:",
        sid or uid,
        repr(text)
    )

    if is_admin(m):
        if admin_command(text, uid):
            return

    if text.startswith("/start"):
        start(m)
        return

    if text in ("❌ خروج", "❌ لغو"):
        for key, o in list(ORDERS.items()):
            if (
                str(o.get("chat_id")) == uid
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

    if text == "🛍 خدمات":
        send(
            uid,
            "🛍 خدمات روبیکا",
            SERV
        )
        return

    if text == "💰 کیف پول":
        wallet_menu(uid)
        return

    if text == "💳 شارژ حساب":
        begin_charge(uid)
        return

    if text == "💰 موجودی":
        wallet_menu(uid)
        return

    if text == "📜 تراکنش‌ها":
        wallet_transactions(uid)
        return

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

    if text == "🛒 خرید":
        send(
            uid,
            "🛍 خدمات",
            SERV
        )
        return

    if text == "📣 کانال":
        show_prices(
            uid,
            CHANNEL,
            "📣 ",
            "📣 تعرفه کانال"
        )
        return

    if text == "👥 گروه":
        show_prices(
            uid,
            CHANNEL,
            "👥 ",
            "👥 تعرفه گروه"
        )
        return

    if text == "⭐ فالور":
        show_prices(
            uid,
            FOLLOWERS,
            "⭐ ",
            "⭐ تعرفه فالور"
        )
        return

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

    o = last_order(uid)

    if text == "❌ ندارم":
        if o and o.get("discount_wait"):
            o["discount_wait"] = 0
            o["final"] = num(o["price"])

            save_orders()

            payment(
                uid,
                o
            )

        return

    if is_media(m):
        receipt(m)
        return

    if o and o.get("discount_wait"):
        discount(
            m,
            text
        )
        return

    if o and o.get("waiting"):
        set_target(
            m,
            text
        )
        return

    if text == "📦 پیگیری":
        orders = [
            o for o in get_user_orders(uid)
            if o.get("status") == "در حال انجام"
        ]

        send(
            uid,
            "📦 سفارش‌ها:\n\n" +
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

    if text == "🧾 سفارش‌ها":
        orders = sorted(
            get_user_orders(uid),
            key=oid,
            reverse=True
        )[:20]

        send(
            uid,
            "🧾 سفارش‌ها:\n\n" +
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

    if text == "📜 قوانین":
        send(
            uid,
            "📜 قوانین:\n"
            "1️⃣ آیدی صحیح ارسال کنید.\n"
            "2️⃣ مقصد عمومی باشد.\n"
            "3️⃣ پس از پرداخت رسید ارسال شود."
        )

        return

    if text == "📞 پشتیبانی":
        send(
            uid,
            SUPPORT
        )

        return

    if text == "🏠 اصلی":
        start(m)
        return

    if is_admin(m):
        return

    send(
        uid,
        "👇 از منو انتخاب کنید."
    )


def process_update(item):
    try:
        m = updates.Update(item).to_message()

        if m:
            handle(m)

    except Exception as e:
        print(
            "UPDATE:",
            repr(e)
        )


def api_updates(offset=""):
    params = {
        "limit": POLL_LIMIT
    }

    if offset:
        params["offset_id"] = offset

    r = http.post(
        f"{API}/getUpdates",
        json=params,
        timeout=REQUEST_TIMEOUT
    )

    if r.status_code != 200:
        raise RuntimeError(
            f"HTTP {r.status_code}"
        )

    data = r.json()

    if not isinstance(data, dict):
        raise RuntimeError(
            "INVALID_JSON"
        )

    if data.get("status") != "OK":
        raise RuntimeError(
            str(
                data.get("status_det")
                or data
            )
        )

    x = data.get("data") or {}

    if not isinstance(x, dict):
        raise RuntimeError(
            "INVALID_DATA"
        )

    arr = x.get("updates") or []

    new_offset = (
        x.get("next_offset_id")
        or offset
    )

    return arr, new_offset


def queue_update(item):
    now = int(time.time())

    with LOCK:
        q = load_json(
            QUEUE,
            []
        )

        if not isinstance(q, list):
            q = []

        q = [
            x for x in q
            if (
                isinstance(x, dict)
                and now - int(x.get("time", 0))
                <= MAX_QUEUE_AGE
            )
        ]

        q.append({
            "time": now,
            "update": item
        })

        save_json(
            QUEUE,
            q
        )


def process_queue():
    now = int(time.time())

    with LOCK:
        q = load_json(
            QUEUE,
            []
        )

        if not isinstance(q, list):
            q = []

        keep = []

        for x in q:
            try:
                age = (
                    now -
                    int(x.get("time", 0))
                )

                if age > MAX_QUEUE_AGE:
                    continue

                item = x.get("update")

                if item:
                    process_update(item)

            except Exception as e:
                print(
                    "QUEUE:",
                    repr(e)
                )

        save_json(
            QUEUE,
            keep
        )


def clear_old_updates():
    print("CLEARING OLD UPDATES...")

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

            changed = (
                new_offset
                and new_offset != offset
            )

            if changed:
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

            time.sleep(0.05)

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


def polling():
    print("BOT STARTED")

    print(
        "ADMINS:",
        ",".join(ADMINS)
    )

    first_run = not os.path.exists(
        READY
    )

    offset = read(
        OF,
        ""
    )

    if not valid_offset(offset):
        print(
            "OFFSET INVALID"
        )

        offset = ""

        try:
            os.remove(OF)
        except:
            pass

    if first_run or not offset:
        clear_old_updates()

        offset = read(
            OF,
            ""
        )

    print(
        "WAITING FOR NEW MESSAGES..."
    )

    backoff = BACKOFF_MIN

    while True:
        try:
            arr, new_offset = api_updates(
                offset
            )

            backoff = BACKOFF_MIN

            if arr:
                for item in arr:
                    try:
                        process_update(item)
                    except Exception as e:
                        print(
                            "PROCESS:",
                            repr(e)
                        )

            if (
                new_offset
                and new_offset != offset
            ):
                offset = new_offset

                if not write(
                    OF,
                    offset
                ):
                    print(
                        "WARNING: OFFSET SAVE FAILED"
                    )

            if arr:
                process_queue()

            else:
                time.sleep(0.2)

        except KeyboardInterrupt:
            raise

        except Exception as e:
            print(
                "POLL ERROR:",
                repr(e)
            )

            try:
                process_queue()
            except Exception as qe:
                print(
                    "QUEUE ERROR:",
                    repr(qe)
                )

            time.sleep(
                min(
                    backoff,
                    BACKOFF_MAX
                )
            )

            backoff = min(
                max(
                    backoff * 2,
                    BACKOFF_MIN
                ),
                BACKOFF_MAX
            )


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )

        self.end_headers()

        self.wfile.write(
            b"OK"
        )

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


def web_server():
    while True:
        try:
            server = HTTPServer(
                ("0.0.0.0", PORT),
                Handler
            )

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

            time.sleep(5)


def main():
    Thread(
        target=web_server,
        daemon=True
    ).start()

    polling()


if __name__ == "__main__":

    while True:
        try:
            main()

        except KeyboardInterrupt:
            break

        except Exception as e:
            print(
                "FATAL:",
                repr(e)
            )

            time.sleep(5)
