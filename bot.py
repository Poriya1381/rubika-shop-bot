from rubibot import RubiBot,types,updates,exceptions
import os,time,json,re,requests
from threading import Thread
from http.server import BaseHTTPRequestHandler,HTTPServer

TOKEN=os.getenv("TOKEN","CDBECG0HQBJVRMBNGUWWXVCPLCHUIYZISYNGPQPKQQAEKZNLVFFWFTUUUJKHLCDZ")
ADMIN="b0KYDRB0BBLs0d5ad48d891eca78ebfa"
CARD="6219861932569709"
SUPPORT="@Poriysmeii"
CODE="@PoriyBot"
PORT=int(os.getenv("PORT","10000"))
DATA="data"

if not TOKEN:
    raise RuntimeError("TOKEN environment variable is not set")

os.makedirs(DATA,exist_ok=True)
bot=RubiBot(TOKEN)
S=requests.Session()

OF=f"{DATA}/offset.txt"
DF=f"{DATA}/orders.json"

def read(p,d=""):
    try:
        with open(p,encoding="utf8") as f:
            return f.read().strip() or d
    except:
        return d

def write(p,x):
    try:
        q=p+".tmp"
        with open(q,"w",encoding="utf8") as f:
            f.write(str(x))
        os.replace(q,p)
    except:
        pass

try:
    ORDERS=json.loads(read(DF,"{}"))
except:
    ORDERS={}

if not isinstance(ORDERS,dict):
    ORDERS={}

def save():
    try:
        q=DF+".tmp"
        with open(q,"w",encoding="utf8") as f:
            json.dump(
                ORDERS,
                f,
                ensure_ascii=False,
                separators=(",",":")
            )
        os.replace(q,DF)
    except Exception as e:
        print("SAVE:",repr(e))

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
            r.add(
                types.KeypadSimpleButton(
                    text,
                    data
                )
            )

        k.add(r)

    return k

MAIN=kb([
    [("🛍 خدمات","services")],
    [("📦 پیگیری","track"),("🧾 سفارش‌ها","orders")],
    [("📜 قوانین","rules"),("📞 پشتیبانی","support")]
])

SERV=kb([
    [("📣 کانال","channel"),("👥 گروه","group")],
    [("⭐ فالور","followers")],
    [("ℹ️ توضیحات","desc")],
    [("🏠 اصلی","home")]
])

ADMIN_KB=kb([
    [("📋 جدید","new"),("🔵 درحال انجام","work")],
    [("🟢 تکمیل","done"),("🔴 لغوشده","cancelled")],
    [("🗑 حذف لغوشده","clear")],
    [("🏠 اصلی","home")]
])

CHANNEL=[
    "100 — 20,000",
    "500 — 60,000",
    "1,000 — 110,000",
    "5,000 — 500,000",
    "10,000 — 950,000",
    "15,000 — 1.600.000"
]

FOLLOWERS=[
    "1,000 — 15,000",
    "10,000 — 100,000",
    "50,000 — 450,000",
    "100,000 — 800,000",
    "150,000 — 1.600.000"
]

def send(uid,text,key=MAIN):
    try:
        bot.send_message(
            str(uid),
            text,
            chat_keypad=key
        )
    except Exception as e:
        print("SEND:",repr(e))

def start(m):
    send(
        m.chat_id,
        "🛍 فروشگاه روبیکا\n\n👇 انتخاب کنید:"
    )

def user_orders(uid):
    return [
        o for o in ORDERS.values()
        if str(o.get("chat_id"))==str(uid)
    ]

def last(uid):
    a=user_orders(uid)
    return max(a,key=oid) if a else None

def username(m):
    try:
        u=getattr(
            bot.get_chat(str(m.chat_id)),
            "username",
            None
        )

        return (
            "@"+str(u).lstrip("@")
            if u else "ندارد"
        )

    except:
        return "ندارد"

def normalize(t):
    t=t.strip()

    if re.fullmatch(
        r"@[A-Za-z0-9_]{3,64}",
        t
    ):
        return t

    m=re.fullmatch(
        r"https?://(?:www\.)?"
        r"(?:rubika\.ir|web\.rubika\.ir)/"
        r"([A-Za-z0-9_]{3,64})/?",
        t,
        re.I
    )

    if m:
        return "@"+m.group(1)

    return None

def show_prices(
    uid,
    items,
    prefix,
    title,
    typ
):

    rows=[]

    for x in items:

        service,price=x.split(
            " — ",
            1
        )

        rows.append([
            (
                prefix+x,
                f"buy|{typ}|{service}|{price}"
            )
        ])

    rows.append([
        ("🔙 خدمات","services"),
        ("🏠 اصلی","home")
    ])

    send(
        uid,
        title,
        kb(rows)
    )

def create(
    m,
    service,
    price,
    typ
):

    uid=str(m.chat_id)

    n=max(
        [oid(x) for x in ORDERS.values()]
        +[1000]
    )+1

    ORDERS[str(n)]={
        "id":n,
        "chat_id":uid,
        "sender_id":str(
            getattr(
                m,
                "sender_id",
                ""
            ) or uid
        ),
        "username":username(m),
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

    send(
        uid,
        "📌 یوزرنیم مقصد را ارسال کنید.\n\n"
        "کانال، پیج یا گروه را به شکل زیر بفرستید:\n"
        "@username\n\n"
        "مثال:\n"
        "@Poriysmeii",
        kb([
            [("❌ خروج","cancel")],
            [("🏠 اصلی","home")]
        ])
    )

def payment(uid,o):

    send(
        uid,
        f"""💳 پرداخت سفارش #{o["id"]}

🛍 {o["service"]}
📌 {o["type"]}
🔗 {o["target"]}

💰 مبلغ: {money(o["final"])} تومان

💳 کارت:
{CARD}

📸 رسید را ارسال کنید."""
    )

def set_target(m,t):

    uid=str(m.chat_id)
    o=last(uid)

    if not o or not o.get("waiting"):
        return

    u=normalize(t)

    if not u:

        send(
            uid,
            "❌ یوزرنیم نامعتبر است.\n\n"
            "لطفاً یوزرنیم کانال، پیج یا گروه را "
            "به شکل زیر ارسال کنید:\n\n"
            "@username\n\n"
            "مثال:\n"
            "@Poriysmeii"
        )

        return

    o.update(
        target=u,
        waiting=0,
        discount_wait=1
    )

    save()

    send(
        uid,
        f"✅ مقصد ثبت شد:\n{u}\n\n"
        "🎁 کد تخفیف دارید؟",
        kb([
            [("❌ ندارم","no_discount")],
            [("❌ خروج","cancel")]
        ])
    )

def discount(m,t):

    uid=str(m.chat_id)
    o=last(uid)

    if not o:
        return

    if t.strip().lower()!=CODE.lower():

        send(
            uid,
            "❌ کد تخفیف نامعتبر است.",
            kb([
                [("❌ ندارم","no_discount")],
                [("❌ خروج","cancel")]
            ])
        )

        return

    p=num(o["price"])

    o.update(
        discount=p*20//100,
        final=p*80//100,
        discount_wait=0
    )

    save()
    payment(uid,o)

def receipt(m):

    uid=str(m.chat_id)
    o=last(uid)

    if not o:
        send(uid,"❌ سفارش ندارید.")
        return

    if o.get("receipt"):
        send(uid,"⚠️ رسید قبلاً ارسال شده.")
        return

    path=f"{DATA}/r{o['id']}.jpg"

    try:

        f=getattr(
            m,
            "file",
            None
        )

        fid=(
            getattr(f,"id",None)
            or getattr(f,"file_id",None)
        )

        if not fid:
            raise Exception("NO_FILE")

        data=bot.download_file(
            bot.get_file(fid)
        )

        if not data:
            raise Exception("NO_DATA")

        with open(path,"wb") as f:
            f.write(data)

        text=(
            f"💰 سفارش #{o['id']}\n"
            f"🛍 {o['service']}\n"
            f"📌 {o['type']}\n"
            f"🔗 {o['target']}\n"
            f"💰 {money(o['final'])} تومان\n"
            f"👤 {o['username']}"
        )

        with open(path,"rb") as f:

            bot.send_photo(
                ADMIN,
                f,
                text=text
            )

        o["receipt"]=1

        save()

        send(
            uid,
            "✅ رسید دریافت شد.\n"
            "⏳ در انتظار بررسی."
        )

    except Exception as e:

        print(
            "RECEIPT:",
            repr(e)
        )

        send(
            uid,
            f"❌ ارسال رسید ناموفق بود.\n{SUPPORT}"
        )

    finally:

        try:
            os.remove(path)
        except:
            pass

STATUS={
    "📋 جدید":"در انتظار بررسی",
    "🔵 درحال انجام":"در حال انجام",
    "🟢 تکمیل":"تکمیل شد",
    "🔴 لغوشده":"لغو شد"
}

def admin_buttons(o):

    n=o["id"]

    if o["status"]=="در انتظار بررسی":

        return kb([
            [
                (f"🔵 شروع #{n}","start"),
                (f"🟢 تکمیل #{n}","done")
            ],
            [
                (f"🔴 لغو #{n}","cancel")
            ]
        ])

    if o["status"]=="در حال انجام":

        return kb([
            [
                (f"🟢 تکمیل #{n}","done"),
                (f"🔴 لغو #{n}","cancel")
            ]
        ])

    return ADMIN_KB

def admin_list(status):

    a=sorted(
        [
            o for o in ORDERS.values()
            if o.get("status")==status
        ],
        key=oid,
        reverse=True
    )

    if not a:

        send(
            ADMIN,
            "📭 سفارشی نیست.",
            ADMIN_KB
        )

        return

    for o in a[:30]:

        send(
            ADMIN,
            f"""📦 #{o["id"]}
🛍 {o["service"]}
📌 {o["type"]}
🔗 {o["target"]}
💰 {money(o["final"])} تومان
👤 {o["username"]}
📊 {o["status"]}""",
            admin_buttons(o)
        )

def change(n,status):

    o=next(
        (
            x for x in ORDERS.values()
            if str(x.get("id"))==str(n)
        ),
        None
    )

    if not o:

        send(
            ADMIN,
            f"❌ سفارش #{n} پیدا نشد.",
            ADMIN_KB
        )

        return

    o.update(
        status=status,
        waiting=0,
        discount_wait=0
    )

    save()

    send(
        o["chat_id"],
        f"📦 سفارش #{n}\n"
        f"📊 وضعیت: {status}"
    )

    send(
        ADMIN,
        f"✅ سفارش #{n} → {status}",
        ADMIN_KB
    )

def admin_cmd(t):

    if t=="/admin":

        send(
            ADMIN,
            "⚙️ پنل مدیریت",
            ADMIN_KB
        )

        return True

    if t in STATUS:

        admin_list(
            STATUS[t]
        )

        return True

    if t=="🗑 حذف لغوشده":

        a=[
            k for k,o in ORDERS.items()
            if o.get("status")=="لغو شد"
        ]

        for k in a:
            del ORDERS[k]

        save()

        send(
            ADMIN,
            f"🗑 {len(a)} سفارش حذف شد.",
            ADMIN_KB
        )

        return True

    x=re.match(
        r"^(🔵 شروع|🟢 تکمیل|🔴 لغو) #(\d+)$",
        t
    )

    if x:

        action,n=x.groups()

        change(
            n,
            {
                "🔵 شروع":"در حال انجام",
                "🟢 تکمیل":"تکمیل شد",
                "🔴 لغو":"لغو شد"
            }[action]
        )

        return True

    return False

def handle(m):

    if not m:
        return

    uid=str(m.chat_id)

    sid=str(
        getattr(
            m,
            "sender_id",
            ""
        ) or ""
    )

    t=(
        getattr(
            m,
            "text",
            ""
        )
        or ""
    ).strip()

    if t=="/admin":

        if uid==ADMIN or sid==ADMIN:

            send(
                uid,
                "⚙️ پنل مدیریت",
                ADMIN_KB
            )

        else:

            send(
                uid,
                "❌ شما دسترسی ادمین ندارید."
            )

        return

    if uid==ADMIN or sid==ADMIN:

        if admin_cmd(t):
            return

    if t.startswith("/start"):

        start(m)
        return

    if t in (
        "❌ خروج",
        "❌ لغو"
    ):

        for k,o in list(ORDERS.items()):

            if (
                str(o.get("chat_id"))==uid
                and (
                    o.get("waiting")
                    or o.get("discount_wait")
                )
            ):

                del ORDERS[k]

        save()

        send(
            uid,
            "✅ لغو شد."
        )

        return

    if t=="🛍 خدمات":

        send(
            uid,
            "🛍 خدمات روبیکا",
            SERV
        )

        return

    if t=="ℹ️ توضیحات":

        send(
            uid,
            "ℹ️ خدمات دارای پشتیبانی هستند.",
            kb([
                [("🛒 خرید","buy")],
                [("🏠 اصلی","home")]
            ])
        )

        return

    if t=="🛒 خرید":

        send(
            uid,
            "🛍 خدمات",
            SERV
        )

        return

    if t=="📣 کانال":

        show_prices(
            uid,
            CHANNEL,
            "📣 ",
            "📣 تعرفه کانال",
            "کانال"
        )

        return

    if t=="👥 گروه":

        show_prices(
            uid,
            CHANNEL,
            "👥 ",
            "👥 تعرفه گروه",
            "گروه"
        )

        return

    if t=="⭐ فالور":

        show_prices(
            uid,
            FOLLOWERS,
            "⭐ ",
            "⭐ تعرفه فالور",
            "روبینو"
        )

        return

    if t.startswith("buy|"):

        parts=t.split("|",3)

        if len(parts)==4:

            _,typ,service,price=parts

            create(
                m,
                service,
                price,
                typ
            )

            return

    if t.startswith(
        ("📣 ","👥 ","⭐ ")
    ) and " — " in t:

        for p,typ in [
            ("📣 ","کانال"),
            ("👥 ","گروه"),
            ("⭐ ","روبینو")
        ]:

            if t.startswith(p):

                service,price=t[
                    len(p):
                ].split(
                    " — ",
                    1
                )

                create(
                    m,
                    service,
                    price,
                    typ
                )

                return

    o=last(uid)

    if t=="❌ ندارم":

        if o and o.get("discount_wait"):

            o.update(
                discount_wait=0,
                final=num(o["price"])
            )

            save()
            payment(uid,o)

        return

    if (
        getattr(m,"file",None)
        or getattr(m,"photo",None)
        or getattr(m,"image",None)
    ):

        receipt(m)
        return

    if o and o.get("discount_wait"):

        discount(
            m,
            t
        )

        return

    if o and o.get("waiting"):

        set_target(
            m,
            t
        )

        return

    if t=="📦 پیگیری":

        a=[
            o for o in user_orders(uid)
            if o.get("status")=="در حال انجام"
        ]

        send(
            uid,
            "📦 سفارش‌ها:\n\n"+
            (
                "\n".join(
                    f"#{o['id']} | {o['service']}"
                    for o in a
                )
                or "📭 ندارد."
            )
        )

        return

    if t=="🧾 سفارش‌ها":

        a=sorted(
            user_orders(uid),
            key=oid,
            reverse=True
        )[:20]

        send(
            uid,
            "🧾 سفارش‌ها:\n\n"+
            (
                "\n".join(
                    f"#{o['id']} | "
                    f"{o['service']} | "
                    f"{o['status']}"
                    for o in a
                )
                or "📭 ندارد."
            )
        )

        return

    if t=="📜 قوانین":

        send(
            uid,
            "📜 قوانین:\n"
            "1️⃣ آیدی صحیح ارسال کنید.\n"
            "2️⃣ مقصد عمومی باشد.\n"
            "3️⃣ پس از پرداخت رسید ارسال شود."
        )

        return

    if t=="📞 پشتیبانی":

        send(
            uid,
            SUPPORT
        )

        return

    if t=="🏠 اصلی":

        start(m)
        return

    send(
        uid,
        "👇 از منو انتخاب کنید."
    )

def get_updates(offset=""):

    while True:

        try:

            p={
                "limit":50
            }

            if offset:
                p["offset_id"]=offset

            r=S.post(
                f"{bot.BASE_URL}/getUpdates",
                json=p,
                timeout=(5,20)
            )

            if r.status_code!=200:

                time.sleep(3)
                continue

            d=r.json()

            if d.get("status")!="OK":

                time.sleep(3)
                continue

            x=d.get("data") or {}

            return (
                x.get("updates",[]),
                x.get("next_offset_id")
                or offset
            )

        except requests.exceptions.RequestException as e:

            print(
                "NETWORK:",
                repr(e)
            )

            time.sleep(3)

        except Exception as e:

            print(
                "GET:",
                repr(e)
            )

            time.sleep(3)

def init_offset():

    old=read(OF)

    if old:
        return old

    try:

        _,no=get_updates("")

        if no:

            write(
                OF,
                no
            )

            return no

    except Exception as e:

        print(
            "INIT:",
            repr(e)
        )

    return ""

class Health(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(
        self,
        *args
    ):
        pass

def web():

    while True:

        try:

            HTTPServer(
                ("0.0.0.0",PORT),
                Health
            ).serve_forever()

        except Exception as e:

            print(
                "WEB:",
                repr(e)
            )

            time.sleep(5)

def run():

    print("================================")
    print("RUBIKA BOT STARTED")
    print("ADMIN:",ADMIN)
    print("PORT:",PORT)
    print("================================")

    offset=init_offset()

    while True:

        try:

            arr,no=get_updates(
                offset
            )

            for x in arr:

                try:

                    m=updates.Update(
                        x
                    ).to_message()

                    if m:
                        handle(m)

                except Exception as e:

                    print(
                        "UPDATE:",
                        repr(e)
                    )

            if no!=offset:

                offset=no

                write(
                    OF,
                    offset
                )

            if not arr:
                time.sleep(.05)

        except exceptions.RubiBotAccessError:

            print(
                "ACCESS ERROR"
            )

            time.sleep(10)

        except KeyboardInterrupt:

            return

        except Exception as e:

            print(
                "MAIN:",
                repr(e)
            )

            time.sleep(3)

if __name__=="__main__":

    Thread(
        target=web,
        daemon=True
    ).start()

    run()
