from rubibot import RubiBot,types,updates,exceptions
import requests,os,time,json,re
from threading import Thread
from http.server import BaseHTTPRequestHandler,HTTPServer

TOKEN=os.getenv("TOKEN","CDBECG0HQBJVRMBNGUWWXVCPLCHUIYZISYNGPQPKQQAEKZNLVFFWFTUUUJKHLCDZ")
ADMIN="b0KYDRB0BBLs0d5ad48d891eca78ebfa"
CARD="6219861932569709"
SUPPORT="@Poriysmeii"
CODE="@PoriyBot"

BASE=os.path.join(os.getcwd(),"data")
os.makedirs(BASE,exist_ok=True)

OF=os.path.join(BASE,"offset.txt")
DF=os.path.join(BASE,"orders.json")

if not TOKEN:
    raise RuntimeError("TOKEN environment variable is not set")

bot=RubiBot(TOKEN)

# =========================
# RENDER PORT
# =========================

PORT=int(os.getenv("PORT","10000"))

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )
        self.end_headers()
        self.wfile.write(
            b"Rubika Bot is running"
        )

    def log_message(self,*args):
        pass

def health_server():
    try:
        server=HTTPServer(
            ("0.0.0.0",PORT),
            HealthHandler
        )
        print("HTTP SERVER:",PORT)
        server.serve_forever()

    except Exception as e:
        print("HTTP SERVER ERROR:",repr(e))


def read(p,d=""):
    try:
        with open(p,encoding="utf8") as f:
            return f.read().strip() or d
    except:
        return d


def write(p,x):
    try:
        with open(p,"w",encoding="utf8") as f:
            f.write(str(x))
    except Exception as e:
        print("WRITE:",repr(e))


try:
    ORDERS=json.loads(
        read(DF,"{}")
    )

    if not isinstance(ORDERS,dict):
        ORDERS={}

except:
    ORDERS={}


def save():
    write(
        DF,
        json.dumps(
            ORDERS,
            ensure_ascii=False
        )
    )


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

    k=types.ChatKeypad(
        resize_keyboard=True
    )

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


GROUP=CHANNEL[:]


FOLLOWERS=[
    "1,000 — 15,000",
    "10,000 — 100,000",
    "50,000 — 450,000",
    "100,000 — 800,000",
    "150,000 — 1.600.000"
]


def start(m):

    bot.send_message(
        str(m.chat_id),
        "🛍 فروشگاه روبیکا\n\n👇 انتخاب کنید:",
        chat_keypad=MAIN
    )


def user_orders(uid):

    return [
        o for o in ORDERS.values()
        if str(o.get("chat_id"))==str(uid)
    ]


def last_order(uid):

    a=user_orders(uid)

    return max(
        a,
        key=oid
    ) if a else None


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

    if t.startswith("@"):
        u=t[1:]

    else:

        x=re.match(
            r"^https?://(?:www\.)?"
            r"(?:rubika\.ir|web\.rubika\.ir)"
            r"/([^/?#\s]+)",
            t,
            re.I
        )

        if not x:
            return None

        u=x.group(1).lstrip("@")

    return (
        "@"+u
        if re.fullmatch(
            r"[A-Za-z0-9_]{3,64}",
            u
        )
        else None
    )


def prices(uid,items,prefix,title):

    bot.send_message(
        uid,
        title,
        chat_keypad=kb(
            [[
                (prefix+x,"buy")
            ] for x in items]
            +
            [[
                ("🔙 خدمات","services"),
                ("🏠 اصلی","home")
            ]]
        )
    )


def create_order(m,service,price,typ):

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

    bot.send_message(
        uid,
        "📌 آیدی مقصد را ارسال کنید:\n\n"
        "مثال: @username",
        chat_keypad=kb([
            [("❌ خروج","cancel")],
            [("🏠 اصلی","home")]
        ])
    )


def payment(uid,o):

    bot.send_message(
        uid,
        f"""💳 پرداخت سفارش #{o["id"]}

🛍 {o["service"]}
📌 {o["type"]}
🔗 {o["target"]}

💰 مبلغ: {money(o["final"])} تومان

💳 کارت:
{CARD}

📸 رسید را ارسال کنید.""",
        chat_keypad=MAIN
    )


def set_target(m,t):

    uid=str(m.chat_id)
    o=last_order(uid)

    if not o:
        return

    u=normalize(t)

    if not u:

        bot.send_message(
            uid,
            "❌ آیدی نامعتبر است."
        )

        return

    o.update({
        "target":u,
        "waiting":0,
        "discount_wait":1
    })

    save()

    bot.send_message(
        uid,
        "🎁 کد تخفیف دارید؟",
        chat_keypad=kb([
            [("❌ ندارم","no_discount")],
            [("❌ خروج","cancel")]
        ])
    )


def discount(m,t):

    uid=str(m.chat_id)
    o=last_order(uid)

    if not o:
        return

    if t.strip().lower()!=CODE.lower():

        bot.send_message(
            uid,
            "❌ کد تخفیف نامعتبر است.",
            chat_keypad=kb([
                [("❌ ندارم","no_discount")],
                [("❌ خروج","cancel")]
            ])
        )

        return

    p=num(o["price"])
    d=p*20//100

    o.update({
        "discount":d,
        "final":p-d,
        "discount_wait":0
    })

    save()

    payment(uid,o)


def is_media(m):

    return bool(
        getattr(m,"file",None)
        or getattr(m,"photo",None)
        or getattr(m,"image",None)
    )


def receipt(m):

    uid=str(m.chat_id)
    o=last_order(uid)

    if not o:

        bot.send_message(
            uid,
            "❌ سفارش ندارید.",
            chat_keypad=MAIN
        )

        return

    if o.get("receipt"):

        bot.send_message(
            uid,
            "⚠️ رسید قبلاً ارسال شده.",
            chat_keypad=MAIN
        )

        return

    path=None

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

        path=os.path.join(
            BASE,
            f"receipt_{o['id']}.jpg"
        )

        with open(path,"wb") as f:
            f.write(data)

        text=f"""💰 سفارش #{o["id"]}
🛍 {o["service"]}
📌 {o["type"]}
🔗 {o["target"]}
💰 {money(o["final"])} تومان
👤 {o["username"]}"""

        with open(path,"rb") as f:

            bot.send_photo(
                ADMIN,
                f,
                text=text
            )

        o["receipt"]=1
        save()

        bot.send_message(
            uid,
            "✅ رسید دریافت شد.\n"
            "⏳ در انتظار بررسی.",
            chat_keypad=MAIN
        )

    except Exception as e:

        print(
            "RECEIPT:",
            repr(e)
        )

        bot.send_message(
            uid,
            "❌ ارسال رسید ناموفق بود.\n"
            +SUPPORT,
            chat_keypad=MAIN
        )

    finally:

        if path:

            try:
                os.remove(path)
            except:
                pass


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

    a=[
        o for o in ORDERS.values()
        if o.get("status")==status
    ]

    a.sort(
        key=oid,
        reverse=True
    )

    if not a:

        bot.send_message(
            ADMIN,
            "📭 سفارشی نیست.",
            chat_keypad=ADMIN_KB
        )

        return

    for o in a[:30]:

        bot.send_message(
            ADMIN,
            f"""📦 #{o["id"]}
🛍 {o["service"]}
📌 {o["type"]}
🔗 {o["target"]}
💰 {money(o["final"])} تومان
👤 {o["username"]}
📊 {o["status"]}""",
            chat_keypad=admin_buttons(o)
        )


def change_status(n,status):

    o=next(
        (
            x for x in ORDERS.values()
            if str(x.get("id"))==str(n)
        ),
        None
    )

    if not o:

        bot.send_message(
            ADMIN,
            f"❌ سفارش #{n} پیدا نشد.",
            chat_keypad=ADMIN_KB
        )

        return

    o.update({
        "status":status,
        "waiting":0,
        "discount_wait":0
    })

    save()

    try:

        bot.send_message(
            str(o["chat_id"]),
            f"📦 سفارش #{n}\n"
            f"📊 وضعیت: {status}"
        )

    except Exception as e:
        print(
            "STATUS:",
            repr(e)
        )

    bot.send_message(
        ADMIN,
        f"✅ سفارش #{n} → {status}",
        chat_keypad=ADMIN_KB
    )


def admin_command(t):

    if t=="/admin":

        bot.send_message(
            ADMIN,
            "⚙️ پنل مدیریت",
            chat_keypad=ADMIN_KB
        )

        return True

    mp={
        "📋 جدید":"در انتظار بررسی",
        "🔵 درحال انجام":"در حال انجام",
        "🟢 تکمیل":"تکمیل شد",
        "🔴 لغوشده":"لغو شد"
    }

    if t in mp:

        admin_list(mp[t])
        return True

    if t=="🗑 حذف لغوشده":

        keys=[
            k for k,o in ORDERS.items()
            if o.get("status")=="لغو شد"
        ]

        for k in keys:
            del ORDERS[k]

        save()

        bot.send_message(
            ADMIN,
            f"🗑 {len(keys)} سفارش حذف شد.",
            chat_keypad=ADMIN_KB
        )

        return True

    x=re.match(
        r"^(🔵 شروع|🟢 تکمیل|🔴 لغو) #(\d+)$",
        t
    )

    if x:

        action,n=x.groups()

        status={
            "🔵 شروع":"در حال انجام",
            "🟢 تکمیل":"تکمیل شد",
            "🔴 لغو":"لغو شد"
        }[action]

        change_status(
            n,
            status
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

    print(
        "MSG:",
        repr(t),
        "CHAT:",
        uid,
        "SENDER:",
        sid
    )

    if t=="/admin":

        if uid==ADMIN or sid==ADMIN:

            bot.send_message(
                uid,
                "⚙️ پنل مدیریت",
                chat_keypad=ADMIN_KB
            )

        else:

            bot.send_message(
                uid,
                "❌ شما دسترسی ادمین ندارید."
            )

        return

    if uid==ADMIN or sid==ADMIN:

        if admin_command(t):
            return

    if t.startswith("/start"):

        start(m)
        return

    if t in (
        "❌ خروج",
        "❌ لغو"
    ):

        for k,o in list(
            ORDERS.items()
        ):

            if (
                str(o.get("chat_id"))==uid
                and (
                    o.get("waiting")
                    or o.get("discount_wait")
                )
            ):
                del ORDERS[k]

        save()

        bot.send_message(
            uid,
            "✅ لغو شد.",
            chat_keypad=MAIN
        )

        return

    if t=="🛍 خدمات":

        bot.send_message(
            uid,
            "🛍 خدمات روبیکا",
            chat_keypad=SERV
        )

        return

    if t=="ℹ️ توضیحات":

        bot.send_message(
            uid,
            "ℹ️ خدمات دارای پشتیبانی هستند.",
            chat_keypad=kb([
                [("🛒 خرید","buy")],
                [("🏠 اصلی","home")]
            ])
        )

        return

    if t=="🛒 خرید":

        bot.send_message(
            uid,
            "🛍 خدمات",
            chat_keypad=SERV
        )

        return

    if t=="📣 کانال":

        prices(
            uid,
            CHANNEL,
            "📣 ",
            "📣 تعرفه کانال"
        )

        return

    if t=="👥 گروه":

        prices(
            uid,
            GROUP,
            "👥 ",
            "👥 تعرفه گروه"
        )

        return

    if t=="⭐ فالور":

        prices(
            uid,
            FOLLOWERS,
            "⭐ ",
            "⭐ تعرفه فالور"
        )

        return

    if t=="📦 پیگیری":

        a=[
            o for o in user_orders(uid)
            if o.get("status")=="در حال انجام"
        ]

        bot.send_message(
            uid,
            "📦 سفارش‌ها:\n\n"
            +"\n".join(
                f"#{o['id']} | {o['service']}"
                for o in a
            )
            or "📭 ندارد.",
            chat_keypad=MAIN
        )

        return

    if t=="🧾 سفارش‌ها":

        a=sorted(
            user_orders(uid),
            key=oid,
            reverse=True
        )

        bot.send_message(
            uid,
            "🧾 سفارش‌ها:\n\n"
            +"\n".join(
                f"#{o['id']} | "
                f"{o['service']} | "
                f"{o['status']}"
                for o in a[:20]
            )
            or "📭 ندارد.",
            chat_keypad=MAIN
        )

        return

    if t=="📜 قوانین":

        bot.send_message(
            uid,
            "📜 قوانین:\n"
            "1️⃣ آیدی صحیح ارسال کنید.\n"
            "2️⃣ مقصد عمومی باشد.\n"
            "3️⃣ پس از پرداخت رسید ارسال شود.",
            chat_keypad=MAIN
        )

        return

    if t=="📞 پشتیبانی":

        bot.send_message(
            uid,
            SUPPORT,
            chat_keypad=MAIN
        )

        return

    if t=="🏠 اصلی":

        start(m)
        return

    o=last_order(uid)

    if t=="❌ ندارم":

        if o and o.get("discount_wait"):

            o.update({
                "discount_wait":0,
                "final":num(o["price"])
            })

            save()
            payment(uid,o)

        return

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

        if (
            t.startswith(p)
            and " — " in t
        ):

            service,price=t[
                len(p):
            ].split(
                " — ",
                1
            )

            create_order(
                m,
                service,
                price,
                typ
            )

            return

    bot.send_message(
        uid,
        "👇 از منو انتخاب کنید.",
        chat_keypad=MAIN
    )


def get_updates(offset):

    try:

        p={
            "limit":10
        }

        if offset:
            p["offset_id"]=offset

        r=requests.post(
            f"{bot.BASE_URL}/getUpdates",
            json=p,
            timeout=60
        )

        if r.status_code!=200:

            print(
                "HTTP:",
                r.status_code
            )

            return [],offset

        d=r.json()

        if d.get("status")!="OK":

            print(
                "API:",
                d
            )

            return [],offset

        x=d.get("data") or {}

        return (
            x.get("updates",[]),
            x.get("next_offset_id") or offset
        )

    except Exception as e:

        print(
            "GET:",
            repr(e)
        )

        return [],offset


def run():

    print("================================")
    print("RUBIKA BOT STARTED")
    print("ADMIN:",ADMIN)
    print("BASE:",BASE)
    print("PORT:",PORT)
    print("================================")

    offset=read(OF)

    while True:

        try:

            arr,no=get_updates(offset)

            if no!=offset:

                offset=no
                write(
                    OF,
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

            if not arr:
                time.sleep(1)

        except exceptions.RubiBotAccessError:

            print(
                "INVALID_ACCESS"
            )

            time.sleep(10)

        except KeyboardInterrupt:

            print(
                "BOT STOPPED"
            )

            return

        except Exception as e:

            print(
                "MAIN:",
                repr(e)
            )

            time.sleep(5)


if __name__=="__main__":

    Thread(
        target=health_server,
        daemon=True
    ).start()

    run()
