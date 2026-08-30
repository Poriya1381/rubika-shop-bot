from rubibot import RubiBot,types,updates,exceptions
import requests,os,time,json,re
from http.server import BaseHTTPRequestHandler,HTTPServer
import threading

# Render HTTP Server
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type","text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot is running")

    def log_message(self,*args):
        pass

def start_http_server():
    try:
        port=int(os.getenv("PORT","10000"))
        HTTPServer(("0.0.0.0",port),HealthHandler).serve_forever()
    except Exception as e:
        print("HTTP:",repr(e))

threading.Thread(target=start_http_server,daemon=True).start()

TOKEN="CDABFH0UFMCTTJJSAXMWDOTDORNFGAFFIQYZXZYJLBRVPVFJZTDXGXLSQLYQVMIU"
CARD="6219861932569709"
SUPPORT="@Poriysmeii"
CODE="@PoriyBot"

# مسیر قابل نوشتن در Render
BASE=os.path.dirname(os.path.abspath(__file__))

AF=f"{BASE}/admin_id.txt"
OF=f"{BASE}/rubika_offset.txt"
DF=f"{BASE}/orders.json"

os.makedirs(BASE,exist_ok=True)

bot=RubiBot(TOKEN)

def read(p,d=""):
    try:
        with open(p,encoding="utf8") as f:
            return f.read().strip() or d
    except:
        return d

def save(p=None,v=None):
    try:
        if p:
            with open(p,"w",encoding="utf8") as f:
                f.write(str(v))
        else:
            with open(DF,"w",encoding="utf8") as f:
                json.dump(ORDERS,f,ensure_ascii=False)
    except Exception as e:
        print("SAVE:",repr(e))

ADMIN=read(AF)

try:
    ORDERS=json.loads(read(DF,"{}"))
    if not isinstance(ORDERS,dict):
        ORDERS={}
except:
    ORDERS={}

def num(x):
    try:
        return int(
            str(x)
            .replace(",","")
            .replace(".","")
            .replace(" تومان","")
        )
    except:
        return 0

def money(x):
    return f"{num(x):,}"

def oid(o):
    try:
        return int(o.get("id",0))
    except:
        return 0

def kb(rows):
    k=types.ChatKeypad(resize_keyboard=True)

    for row in rows:
        r=types.KeypadRow()

        for text,data in row:
            r.add(types.KeypadSimpleButton(text,data))

        k.add(r)

    return k

MAIN=kb([
    [("🛍 خدمات روبیکا","services")],
    [("📦 پیگیری سفارش","track"),("🧾 سفارش‌های من","orders")],
    [("📜 قوانین","rules"),("📞 پشتیبانی","support")]
])

SERV=kb([
    [("📣 افزایش کانال","channel"),("👥 افزایش گروه","group")],
    [("⭐ افزایش فالور","followers")],
    [("ℹ️ توضیحات خدمات","desc")],
    [("🏠 منوی اصلی","home")]
])

ADMIN_KB=kb([
    [("📋 سفارش‌های جدید","new")],
    [("🔵 در حال انجام","work")],
    [("🟢 تکمیل‌شده","done")],
    [("🔴 لغوشده‌ها","cancelled")],
    [("🗑 حذف همه لغوشده‌ها","clear")],
    [("🏠 منوی اصلی","home")]
])

CHANNEL=[
    "100 — 20,000",
    "500 — 60,000",
    "1,000 — 110,000",
    "5,000 — 500,000",
    "10,000 — 950,000",
    "15,000 — 1.600.000"
]

GROUP=CHANNEL[:]

FOLLOWERS=[
    "1,000 — 15,000",
    "10,000 — 100,000",
    "50,000 — 450,000",
    "100,000 — 800,000",
    "150,000 — 1.600.000"
]

DESC="""╔════════════════════╗
      ℹ️ توضیحات خدمات
╚════════════════════╝

1️⃣ پنل‌های ما تماما اعلام فعال دارند
که برای سرچ و کانال مناسب هستند.

2️⃣ پنل ما شامل هیچ‌گونه ریزشی نیست
و حتی ۱ دونه ریزش هم ندارد. ✅

3️⃣ پنل ما برای گروه‌ها عالیه، چون
اکانت‌های ما تبلیغاتی نیستند و هیچ
پیام تبلیغاتی در گروه‌ها ارسال نمی‌شود. 🚫

4️⃣ تضمین داریم. 🛡️

5️⃣ پشتیبانی ۲۴ ساعته داریم. 📞

━━━━━━━━━━━━━━━━━━
📞 پشتیبانی:
@Poriysmeii
━━━━━━━━━━━━━━━━━━"""

def start(m):
    bot.send_message(
        str(m.chat_id),
        """╔════════════════════╗
       🛍 فروشگاه روبیکا
╚════════════════════╝

سلام دوست عزیز 👋🌹

📣 افزایش کانال
👥 افزایش گروه
⭐ افزایش فالور

📦 پیگیری سفارش
🧾 سفارش‌های من

👇 انتخاب کنید:""",
        chat_keypad=MAIN
    )

def get_user(m):
    try:
        u=getattr(
            bot.get_chat(str(m.chat_id)),
            "username",
            None
        )

        return "@"+str(u).lstrip("@") if u else "ندارد"

    except:
        return "ندارد"

def normalize(t):
    t=t.strip()

    if t.startswith("@"):
        u=t[1:]

    else:
        x=re.match(
            r"^https?://(?:www\.)?(?:rubika\.ir|web\.rubika\.ir)/([^/?#\s]+)",
            t,
            re.I
        )

        if not x:
            return None

        u=x.group(1).lstrip("@")

    return (
        "@"+u
        if re.fullmatch(r"[A-Za-z0-9_]{3,64}",u)
        else None
    )

def prices(items,prefix):
    return kb(
        [[(prefix+x,"buy")] for x in items]+
        [[("🔙 خدمات","services"),("🏠 اصلی","home")]]
    )

def user_orders(uid):
    return [
        o for o in ORDERS.values()
        if str(o.get("chat_id"))==str(uid)
    ]

def user_order(uid):
    a=user_orders(uid)
    return max(a,key=oid) if a else None

def new_order(m,service,price,typ):
    uid=str(m.chat_id)

    n=max(
        [oid(x) for x in ORDERS.values()]+[1000]
    )+1

    key=str(n)

    ORDERS[key]={
        "id":key,
        "chat_id":uid,
        "sender_id":str(
            getattr(m,"sender_id","") or uid
        ),
        "username":get_user(m),
        "service":service,
        "type":typ,
        "price":price,
        "final":num(price),
        "discount":0,
        "target":"",
        "status":"در انتظار بررسی",
        "waiting":1,
        "discount_wait":0,
        "receipt":0
    }

    save()

    title={
        "کانال":"📌 آیدی کانال را ارسال کنید",
        "گروه":"📌 آیدی گروه را ارسال کنید",
        "روبینو":"📌 آیدی پیج را وارد کنید"
    }.get(
        typ,
        "📌 آیدی مقصد را ارسال کنید"
    )

    bot.send_message(
        uid,
        f"""╔════════════════════╗
        🛍 ثبت سفارش
╚════════════════════╝

{title}

مثال:
@username

⚠️ فقط آیدی عمومی روبیکا را ارسال کنید.""",
        chat_keypad=kb([
            [("❌ خروج","cancel")],
            [("🏠 منوی اصلی","home")]
        ])
    )

def ask_discount(uid):
    bot.send_message(
        uid,
        """╔════════════════════╗
        🎁 کد تخفیف
╚════════════════════╝

آیا کد تخفیف دارید؟

🎁 اگر دارید کد را ارسال کنید.

اگر ندارید گزینه زیر را بزنید 👇""",
        chat_keypad=kb([
            [("❌ کد تخفیف ندارم","no_discount")],
            [("❌ خروج","cancel")]
        ])
    )

def set_target(m,text):
    uid=str(m.chat_id)
    o=user_order(uid)

    if not o:
        return

    u=normalize(text)

    if not u:
        bot.send_message(
            uid,
            """❌ آیدی نامعتبر است.

📌 مثال صحیح:
@username""",
            chat_keypad=MAIN
        )
        return

    o.update(
        target=u,
        waiting=0,
        discount_wait=1,
        username=get_user(m)
    )

    save()
    ask_discount(uid)

def payment(uid,o):
    bot.send_message(
        uid,
        f"""╔════════════════════╗
       💳 پرداخت سفارش
╚════════════════════╝

📦 سفارش: #{o["id"]}
🛍 خدمت: {o["service"]}
📌 نوع: {o["type"]}

🔗 مقصد:
{o["target"]}

💰 مبلغ اصلی:
{money(o["price"])} تومان

🎁 تخفیف:
{money(o["discount"])} تومان

💳 مبلغ نهایی:
{money(o["final"])} تومان

━━━━━━━━━━━━━━━━━━
💳 شماره کارت:
{CARD}

👤 به نام پوریا سمیعی
━━━━━━━━━━━━━━━━━━

📸 بعد از واریز عکس رسید را همینجا ارسال کنید.""",
        chat_keypad=MAIN
    )

def discount(m,text):
    uid=str(m.chat_id)
    o=user_order(uid)

    if not o:
        return

    if text.strip().lower()!=CODE.lower():
        bot.send_message(
            uid,
            "❌ کد تخفیف نامعتبر است.",
            chat_keypad=kb([
                [("❌ کد تخفیف ندارم","no_discount")],
                [("❌ خروج","cancel")]
            ])
        )
        return

    x=num(o["price"])
    d=x*20//100

    o.update(
        discount=d,
        final=x-d,
        discount_wait=0,
        code=CODE
    )

    save()

    bot.send_message(
        uid,
        f"""🎉 کد تخفیف تأیید شد!

💰 مبلغ اصلی:
{money(x)} تومان

🎁 تخفیف ۲۰٪:
{money(d)} تومان

💳 مبلغ نهایی:
{money(x-d)} تومان"""
    )

    payment(uid,o)

def is_media(m):
    return bool(
        getattr(m,"file",None) or
        getattr(m,"photo",None) or
        getattr(m,"image",None)
    )

def receipt(m):
    uid=str(m.chat_id)
    o=user_order(uid)

    if not o:
        bot.send_message(
            uid,
            "❌ سفارش فعالی ندارید.",
            chat_keypad=MAIN
        )
        return

    if o.get("receipt"):
        bot.send_message(
            uid,
            "⚠️ رسید قبلاً دریافت شده.",
            chat_keypad=MAIN
        )
        return

    try:
        f=getattr(m,"file",None)

        fid=(
            getattr(f,"id",None) or
            getattr(f,"file_id",None)
        )

        if not fid:
            raise Exception("NO FILE")

        data=bot.download_file(
            bot.get_file(fid)
        )

        if not data:
            raise Exception("NO DATA")

        path=f"{BASE}/receipt_{o['id']}.jpg"

        with open(path,"wb") as f:
            f.write(data)

        text=f"""💰 سفارش جدید

📦 #{o["id"]}
🛍 {o["service"]}
📌 {o["type"]}

🔗 مقصد:
{o["target"]}

💰 مبلغ:
{money(o["final"])} تومان

🎁 تخفیف:
{money(o["discount"])} تومان

👤 {o["username"]}
🆔 {o["chat_id"]}

📊 وضعیت:
{o["status"]}

📸 رسید دریافت شد."""

        with open(path,"rb") as f:
            bot.send_photo(
                ADMIN,
                f,
                text=text
            )

        try:
            os.remove(path)
        except:
            pass

        o["receipt"]=1
        save()

        bot.send_message(
            uid,
            """╔════════════════════╗
        ✅ رسید دریافت شد
╚════════════════════╝

🟡 وضعیت:
در انتظار بررسی

⏳ پس از بررسی وضعیت سفارش اعلام می‌شود.""",
            chat_keypad=MAIN
        )

    except Exception as e:
        print("RECEIPT:",repr(e))

        bot.send_message(
            uid,
            f"""❌ ارسال رسید انجام نشد.

📞 پشتیبانی:
{SUPPORT}""",
            chat_keypad=MAIN
        )

def my_orders(uid,status=None):
    arr=[
        o for o in user_orders(uid)
        if status is None or o.get("status")==status
    ]

    if not arr:
        return "📭 سفارشی وجود ندارد."

    arr.sort(key=oid,reverse=True)

    return "\n".join(
        f"""📦 سفارش #{o["id"]}
🛍 {o["service"]}
📌 {o["type"]}
🔗 {o["target"]}
💰 {money(o["final"])} تومان
📊 {o["status"]}

━━━━━━━━━━━━"""
        for o in arr[:20]
    )

def admin_buttons(o):
    n=o["id"]
    s=o["status"]

    if s=="در انتظار بررسی":
        return kb([
            [
                (f"🔵 شروع #{n}","start"),
                (f"🟢 تکمیل #{n}","done")
            ],
            [(f"🔴 لغو #{n}","cancel")]
        ])

    if s=="در حال انجام":
        return kb([
            [
                (f"🟢 تکمیل #{n}","done"),
                (f"🔴 لغو #{n}","cancel")
            ]
        ])

    return ADMIN_KB

def admin_list(status):
    arr=[
        o for o in ORDERS.values()
        if o.get("status")==status
    ]

    arr.sort(key=oid,reverse=True)

    if not arr:
        bot.send_message(
            ADMIN,
            f"📭 سفارشی با وضعیت «{status}» وجود ندارد.",
            chat_keypad=ADMIN_KB
        )
        return

    bot.send_message(
        ADMIN,
        f"""📋 {status}

📦 تعداد سفارش‌ها: {len(arr)}""",
        chat_keypad=ADMIN_KB
    )

    for o in arr[:30]:

        text=f"""📦 سفارش #{o["id"]}

🛍 خدمت:
{o["service"]}

📌 نوع:
{o["type"]}

🔗 مقصد:
{o["target"]}

💰 مبلغ:
{money(o["final"])} تومان

🎁 تخفیف:
{money(o["discount"])} تومان

👤 کاربر:
{o["username"]}

🆔 شناسه:
{o["chat_id"]}

📊 وضعیت:
{o["status"]}"""

        bot.send_message(
            ADMIN,
            text,
            chat_keypad=admin_buttons(o)
        )

def find_order(n):
    n=str(n).strip().replace("#","")

    return next(
        (
            o for o in ORDERS.values()
            if str(o.get("id"))==n
        ),
        None
    )

def status_message(o,status):
    n=o["id"]

    if status=="در حال انجام":
        return f"""🔵 سفارش #{n} در حال تکمیل شدن است.

🛍 {o["service"]}
📌 نوع: {o["type"]}

🔗 مقصد:
{o["target"]}

⏳ سفارش شما در حال انجام است."""

    if status=="تکمیل شد":
        return f"""╔════════════════════╗
       🟢 سفارش تکمیل شد
╚════════════════════╝

📦 سفارش #{n}

🛍 {o["service"]}
📌 نوع: {o["type"]}

🔗 مقصد:
{o["target"]}

✅ سفارش شما با موفقیت تکمیل شد."""

    if status=="لغو شد":
        return f"""╔════════════════════╗
          🔴 سفارش لغو شد
╚════════════════════╝

📦 سفارش #{n}

🛍 {o["service"]}

🔗 مقصد:
{o["target"]}

❌ سفارش شما لغو شد.

📞 پشتیبانی:
{SUPPORT}"""

    return f"📊 وضعیت سفارش #{n} تغییر کرد:\n{status}"

def change_status(n,status):
    o=find_order(n)

    if not o:
        return None

    o.update(
        status=status,
        waiting=0,
        discount_wait=0
    )

    save()

    try:
        bot.send_message(
            str(o["chat_id"]),
            status_message(o,status)
        )

        o["status_sent"]=1

    except Exception as e:
        o["status_sent"]=0
        print("USER STATUS:",repr(e))

    save()
    return o

def admin_operation(n,status):
    o=change_status(n,status)

    if not o:
        bot.send_message(
            ADMIN,
            f"❌ سفارش #{n} پیدا نشد.",
            chat_keypad=ADMIN_KB
        )
        return

    icon={
        "در حال انجام":"🔵",
        "تکمیل شد":"🟢",
        "لغو شد":"🔴"
    }.get(status,"📊")

    sent=(
        "✅ پیام وضعیت برای مشتری ارسال شد."
        if o.get("status_sent")
        else
        "⚠️ وضعیت ذخیره شد ولی ارسال پیام به مشتری ناموفق بود."
    )

    bot.send_message(
        ADMIN,
        f"""╔════════════════════╗
      {icon} عملیات انجام شد
╚════════════════════╝

📦 سفارش:
#{n}

📊 وضعیت جدید:
{status}

👤 مشتری:
{o["username"]}

🔗 مقصد:
{o["target"]}

{sent}

👇 پنل مدیریت همچنان فعال است:""",
        chat_keypad=ADMIN_KB
    )

def admin_panel():
    bot.send_message(
        ADMIN,
        """╔════════════════════╗
        ⚙️ پنل مدیریت
╚════════════════════╝

📋 مدیریت سفارش‌ها

👇 یک گزینه را انتخاب کنید:""",
        chat_keypad=ADMIN_KB
    )

def admin_cmd(t):

    if t=="/admin":
        admin_panel()
        return True

    mp={
        "📋 سفارش‌های جدید":"در انتظار بررسی",
        "🔵 در حال انجام":"در حال انجام",
        "🟢 تکمیل‌شده":"تکمیل شد",
        "🔴 لغوشده‌ها":"لغو شد"
    }

    if t in mp:
        admin_list(mp[t])
        return True

    if t=="🗑 حذف همه لغوشده‌ها":

        keys=[
            k for k,v in ORDERS.items()
            if v.get("status")=="لغو شد"
        ]

        for k in keys:
            del ORDERS[k]

        save()

        bot.send_message(
            ADMIN,
            f"""╔════════════════════╗
        🗑 حذف لغوشده‌ها
╚════════════════════╝

✅ حذف انجام شد.

📦 تعداد حذف‌شده:
{len(keys)}

📋 پنل مدیریت:""",
            chat_keypad=ADMIN_KB
        )

        return True

    m=re.match(
        r"^(🔵 شروع|🟢 تکمیل|🔴 لغو) #(\d+)$",
        t
    )

    if m:
        action,n=m.groups()

        status={
            "🔵 شروع":"در حال انجام",
            "🟢 تکمیل":"تکمیل شد",
            "🔴 لغو":"لغو شد"
        }[action]

        admin_operation(n,status)
        return True

    for pattern,status in [
        (r"^/start_work\s+(\d+)$","در حال انجام"),
        (r"^/complete\s+(\d+)$","تکمیل شد"),
        (r"^/cancel_order\s+(\d+)$","لغو شد")
    ]:

        m=re.match(pattern,t)

        if m:
            admin_operation(
                m.group(1),
                status
            )
            return True

    return False

def handle(m):

    if not m:
        return

    uid=str(m.chat_id)
    t=(getattr(m,"text","") or "").strip()

    if uid==str(ADMIN):

        if admin_cmd(t):
            return

    if t=="/admin":
        bot.send_message(
            uid,
            "❌ شما دسترسی ادمین ندارید."
        )
        return

    if t.startswith("/start"):
        start(m)
        return

    if t in ("❌ خروج","❌ لغو"):

        keys=[
            k for k,o in ORDERS.items()
            if str(o.get("chat_id"))==uid and
            (
                o.get("waiting") or
                o.get("discount_wait")
            )
        ]

        for k in keys:
            del ORDERS[k]

        save()

        bot.send_message(
            uid,
            "✅ از مرحله ثبت سفارش خارج شدید.",
            chat_keypad=MAIN
        )
        return

    if t=="🛍 خدمات روبیکا":

        bot.send_message(
            uid,
            """🔒 قبل از خرید لطفاً توضیحات خدمات را مطالعه کنید.

ℹ️ ابتدا توضیحات خدمات را بخوانید 👇""",
            chat_keypad=kb([
                [("ℹ️ توضیحات خدمات","desc")],
                [("🏠 منوی اصلی","home")]
            ])
        )
        return

    if t=="ℹ️ توضیحات خدمات":

        bot.send_message(
            uid,
            DESC,
            chat_keypad=kb([
                [("🛒 ورود به بخش خرید","buy")],
                [("🏠 منوی اصلی","home")]
            ])
        )
        return

    if t=="🛒 ورود به بخش خرید":

        bot.send_message(
            uid,
            "🛍 خدمات روبیکا\n\n👇 سرویس موردنظر را انتخاب کنید:",
            chat_keypad=SERV
        )
        return

    if t=="📣 افزایش کانال":

        bot.send_message(
            uid,
            "📣 تعرفه افزایش کانال 👇",
            chat_keypad=prices(
                CHANNEL,
                "📣 "
            )
        )
        return

    if t=="👥 افزایش گروه":

        bot.send_message(
            uid,
            "👥 تعرفه افزایش گروه 👇",
            chat_keypad=prices(
                GROUP,
                "👥 "
            )
        )
        return

    if t=="⭐ افزایش فالور":

        bot.send_message(
            uid,
            "⭐ تعرفه افزایش فالور 👇",
            chat_keypad=prices(
                FOLLOWERS,
                "⭐ "
            )
        )
        return

    if t=="📦 پیگیری سفارش":

        bot.send_message(
            uid,
            "📦 سفارش‌های در حال انجام:\n\n"+
            my_orders(uid,"در حال انجام"),
            chat_keypad=MAIN
        )
        return

    if t=="🧾 سفارش‌های من":

        bot.send_message(
            uid,
            "🧾 سوابق سفارش‌های شما:\n\n"+
            my_orders(uid),
            chat_keypad=MAIN
        )
        return

    if t=="📜 قوانین":

        bot.send_message(
            uid,
            f"""📜 قوانین ثبت سفارش

1️⃣ پس از ثبت سفارش امکان لغو یا تغییر نیست.
2️⃣ آیدی صحیح مقصد را ارسال کنید.
3️⃣ مقصد باید عمومی باشد.
4️⃣ زمان انجام سفارش متغیر است.
5️⃣ پس از پرداخت رسید را ارسال کنید.

📞 ادمین:
{SUPPORT}""",
            chat_keypad=MAIN
        )
        return

    if t=="📞 پشتیبانی":

        bot.send_message(
            uid,
            f"""📞 پشتیبانی

👤 آیدی:
{SUPPORT}""",
            chat_keypad=MAIN
        )
        return

    if t in ("🔙 خدمات","🛒 خدمات"):

        bot.send_message(
            uid,
            "🛍 خدمات روبیکا",
            chat_keypad=SERV
        )
        return

    if t=="🏠 منوی اصلی":
        start(m)
        return

    if t=="❌ کد تخفیف ندارم":

        o=user_order(uid)

        if o and o.get("discount_wait"):

            o.update(
                discount_wait=0,
                final=num(o["price"])
            )

            save()
            payment(uid,o)

        return

    o=user_order(uid)

    if is_media(m):
        receipt(m)
        return

    if o and o.get("discount_wait"):
        discount(m,t)
        return

    if o and o.get("waiting"):
        set_target(m,t)
        return

    for p,typ in [
        ("📣 ","کانال"),
        ("👥 ","گروه"),
        ("⭐ ","روبینو")
    ]:

        if t.startswith(p) and " — " in t:

            service,price=t[len(p):].split(
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
        chat_keypad=MAIN
    )

def get_updates(offset):

    try:

        p={"limit":10}

        if offset:
            p["offset_id"]=offset

        r=requests.post(
            f"{bot.BASE_URL}/getUpdates",
            json=p,
            timeout=60
        )

        if r.status_code!=200:
            print("HTTP:",r.status_code)
            return [],offset

        d=r.json()

        if d.get("status")!="OK":
            print("API:",d)
            return [],offset

        x=d.get("data") or {}

        return (
            x.get("updates",[]),
            x.get("next_offset_id") or offset
        )

    except Exception as e:
        print("GET:",repr(e))
        return [],offset

def run():

    print("================================")
    print("BOT STARTED")
    print("ADMIN ID:",ADMIN or "NOT SET")
    print("================================")

    offset=read(OF)

    while True:

        try:

            arr,no=get_updates(offset)

            if no!=offset:
                offset=no
                save(OF,offset)

            for x in arr:

                try:
                    u=updates.Update(x)
                    m=u.to_message()

                    if m:
                        handle(m)

                except Exception as e:
                    print("UPDATE:",repr(e))

            if not arr:
                time.sleep(1)

        except KeyboardInterrupt:
            print("BOT STOPPED")
            return

        except exceptions.RubiBotAccessError:
            print("INVALID_ACCESS")
            time.sleep(10)

        except Exception as e:
            print("MAIN:",repr(e))
            time.sleep(5)

while True:

    try:
        run()

    except KeyboardInterrupt:
        break

    except Exception as e:
        print("RESTART:",repr(e))
        time.sleep(5)
