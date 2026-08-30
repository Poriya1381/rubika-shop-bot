from rubibot import RubiBot,types,updates,exceptions
import os,time,json,re,requests
from threading import Thread
from http.server import BaseHTTPRequestHandler,HTTPServer

TOKEN=os.getenv("TOKEN","CDBECG0HQBJVRMBNGUWWXVCPLCHUIYZISYNGPQPKQQAEKZNLVFFWFTUUUJKHLCDZ")
ADMIN="b0KYDRB0BBLs0d5ad48d891eca78ebfa"
CARD="6219861932569709"
SUPPORT="@Poriysmeii"
CODE="@iraannbot"
PORT=int(os.getenv("PORT","10000"))

BASE="data"
os.makedirs(BASE,exist_ok=True)

OF=f"{BASE}/offset.txt"
DF=f"{BASE}/orders.json"

if not TOKEN:
    raise RuntimeError("TOKEN environment variable is not set")

bot=RubiBot(TOKEN)

def new_session():
    s=requests.Session()
    s.headers.update({
        "Connection":"keep-alive",
        "User-Agent":"RubikaShopBot/1.0"
    })
    return s

http=new_session()

def read(path,default=""):
    try:
        with open(path,encoding="utf-8") as f:
            return f.read().strip() or default
    except:
        return default

def write(path,value):
    try:
        tmp=path+".tmp"
        with open(tmp,"w",encoding="utf-8") as f:
            f.write(str(value))
        os.replace(tmp,path)
    except Exception as e:
        print("WRITE:",repr(e))

try:
    ORDERS=json.loads(read(DF,"{}"))
    if not isinstance(ORDERS,dict):
        ORDERS={}
except:
    ORDERS={}

def save():
    try:
        tmp=DF+".tmp"
        with open(tmp,"w",encoding="utf-8") as f:
            json.dump(
                ORDERS,f,
                ensure_ascii=False,
                separators=(",",":")
            )
        os.replace(tmp,DF)
    except Exception as e:
        print("SAVE:",repr(e))

def oid(o):
    try:
        return int(o.get("id",0))
    except:
        return 0

def num(x):
    try:
        return int(
            str(x)
            .replace(",","")
            .replace(".","")
            .replace(" تومان","")
            .strip()
        )
    except:
        return 0

def money(x):
    return f"{num(x):,}"

def kb(rows):
    k=types.ChatKeypad(resize_keyboard=True)
    for row in rows:
        r=types.KeypadRow()
        for text,data in row:
            r.add(types.KeypadSimpleButton(text,data))
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
        return True
    except Exception as e:
        print("SEND:",repr(e))
        return False

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

def last_order(uid):
    a=user_orders(uid)
    return max(a,key=oid) if a else None

def username(m):
    try:
        c=bot.get_chat(str(m.chat_id))
        u=getattr(c,"username",None)
        if u:
            return "@"+str(u).lstrip("@")
    except:
        pass
    return "ندارد"

def normalize(text):
    text=text.strip()

    if re.fullmatch(
        r"@[A-Za-z0-9_]{3,64}",
        text
    ):
        return text

    m=re.fullmatch(
        r"https?://(?:www\.)?"
        r"(?:rubika\.ir|web\.rubika\.ir)/"
        r"([A-Za-z0-9_]{3,64})/?",
        text,re.I
    )

    if m:
        return "@"+m.group(1)

    return None

def prices(uid,items,prefix,title):
    rows=[
        [(prefix+x,"price")]
        for x in items
    ]

    rows.append([
        ("🔙 خدمات","services"),
        ("🏠 اصلی","home")
    ])

    send(uid,title,kb(rows))

def parse_price(text):
    m=re.search(
        r"(\d[\d,\.]*)\s*[—\-–]\s*([\d,\.]+)",
        text
    )

    if not m:
        return None

    count=m.group(1)
    price=m.group(2)

    if text.startswith("📣"):
        typ="کانال"
    elif text.startswith("👥"):
        typ="گروه"
    elif text.startswith("⭐"):
        typ="روبینو"
    else:
        return None

    return typ,count,price

def create_order(m,service,price,typ):
    uid=str(m.chat_id)

    n=max(
        [oid(o) for o in ORDERS.values()]+[1000]
    )+1

    ORDERS[str(n)]={
        "id":n,
        "chat_id":uid,
        "sender_id":str(
            getattr(m,"sender_id","") or uid
        ),
        "username":username(m),
        "service":service,
        "type":typ,
        "price":price,
        "final":num(price),
        "discount":0,
        "discount_code":"",
        "target":"",
        "status":"در انتظار بررسی",
        "waiting":1,
        "discount_wait":0,
        "receipt":0,
        "created":int(time.time())
    }

    save()

    print("ORDER:",n)

    send(
        uid,
        "📌 یوزرنیم مقصد را ارسال کنید.\n\n"
        "کانال، پیج یا گروه:\n"
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

def set_target(m,text):
    uid=str(m.chat_id)
    o=last_order(uid)

    if not o or not o.get("waiting"):
        return

    u=normalize(text)

    if not u:
        send(
            uid,
            "❌ یوزرنیم نامعتبر است.\n\n"
            "به شکل @username ارسال کنید."
        )
        return

    o["target"]=u
    o["waiting"]=0
    o["discount_wait"]=1

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

def discount(m,text):
    uid=str(m.chat_id)
    o=last_order(uid)

    if not o or not o.get("discount_wait"):
        return

    code=text.strip().lower()

    if code!=CODE.lower():
        send(
            uid,
            "❌ کد تخفیف نامعتبر است.",
            kb([
                [("❌ ندارم","no_discount")],
                [("❌ خروج","cancel")]
            ])
        )
        return

    if o.get("discount_code"):
        send(uid,"⚠️ کد تخفیف این سفارش قبلاً ثبت شده.")
        return

    p=num(o["price"])
    d=p*20//100

    o["discount"]=d
    o["final"]=p-d
    o["discount_code"]=CODE
    o["discount_wait"]=0

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
        send(uid,"❌ سفارش ندارید.")
        return

    if o.get("receipt"):
        send(uid,"⚠️ رسید قبلاً ارسال شده.")
        return

    path=f"{BASE}/receipt_{o['id']}.jpg"

    try:
        f=getattr(m,"file",None)

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
            f"🎁 تخفیف: {money(o.get('discount',0))} تومان\n"
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
        print("RECEIPT:",repr(e))
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
            [(f"🔴 لغو #{n}","cancel")]
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
        send(ADMIN,"📭 سفارشی نیست.",ADMIN_KB)
        return

    for o in a[:30]:
        send(
            ADMIN,
            f"""📦 سفارش #{o["id"]}

🛍 {o["service"]}
📌 {o["type"]}
🔗 {o["target"] or "ثبت نشده"}
💰 {money(o["final"])} تومان
🎁 تخفیف: {money(o.get("discount",0))} تومان
👤 {o["username"]}
📊 {o["status"]}""",
            admin_buttons(o)
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
        send(ADMIN,f"❌ سفارش #{n} پیدا نشد.",ADMIN_KB)
        return

    o["status"]=status
    o["waiting"]=0
    o["discount_wait"]=0

    save()

    send(
        o["chat_id"],
        f"📦 سفارش #{n}\n📊 وضعیت: {status}"
    )

    send(
        ADMIN,
        f"✅ سفارش #{n} → {status}",
        ADMIN_KB
    )

def admin_command(text):
    if text=="/admin":
        send(ADMIN,"⚙️ پنل مدیریت",ADMIN_KB)
        return True

    if text in STATUS:
        admin_list(STATUS[text])
        return True

    if text=="🗑 حذف لغوشده":
        keys=[
            k for k,o in ORDERS.items()
            if o.get("status")=="لغو شد"
        ]

        for k in keys:
            del ORDERS[k]

        save()
        send(
            ADMIN,
            f"🗑 {len(keys)} سفارش حذف شد.",
            ADMIN_KB
        )
        return True

    m=re.match(
        r"^(🔵 شروع|🟢 تکمیل|🔴 لغو)\s*#(\d+)$",
        text
    )

    if m:
        action,n=m.groups()

        status={
            "🔵 شروع":"در حال انجام",
            "🟢 تکمیل":"تکمیل شد",
            "🔴 لغو":"لغو شد"
        }[action]

        change_status(n,status)
        return True

    return False

def handle(m):
    if not m:
        return

    uid=str(m.chat_id)
    sid=str(
        getattr(m,"sender_id","") or ""
    )

    text=(
        getattr(m,"text","")
        or ""
    ).strip()

    print("MSG:",repr(text),"CHAT:",uid)

    if text=="/admin":
        if uid==ADMIN or sid==ADMIN:
            send(uid,"⚙️ پنل مدیریت",ADMIN_KB)
        else:
            send(uid,"❌ شما دسترسی ادمین ندارید.")
        return

    if uid==ADMIN or sid==ADMIN:
        if admin_command(text):
            return

    if text.startswith("/start"):
        start(m)
        return

    if text in ("❌ خروج","❌ لغو"):
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
        send(uid,"✅ لغو شد.")
        return

    if text=="🛍 خدمات":
        send(uid,"🛍 خدمات روبیکا",SERV)
        return

    if text=="ℹ️ توضیحات":
        send(
            uid,
            "ℹ️ خدمات دارای پشتیبانی هستند.",
            kb([
                [("🛒 خرید","buy")],
                [("🏠 اصلی","home")]
            ])
        )
        return

    if text=="🛒 خرید":
        send(uid,"🛍 خدمات",SERV)
        return

    if text=="📣 کانال":
        prices(
            uid,
            CHANNEL,
            "📣 ",
            "📣 تعرفه کانال"
        )
        return

    if text=="👥 گروه":
        prices(
            uid,
            CHANNEL,
            "👥 ",
            "👥 تعرفه گروه"
        )
        return

    if text=="⭐ فالور":
        prices(
            uid,
            FOLLOWERS,
            "⭐ ",
            "⭐ تعرفه فالور"
        )
        return

    p=parse_price(text)

    if p:
        typ,service,price=p
        create_order(
            m,
            service,
            price,
            typ
        )
        return

    o=last_order(uid)

    if text=="❌ ندارم":
        if o and o.get("discount_wait"):
            o["discount_wait"]=0
            o["final"]=num(o["price"])
            save()
            payment(uid,o)
        return

    if is_media(m):
        receipt(m)
        return

    if o and o.get("discount_wait"):
        discount(m,text)
        return

    if o and o.get("waiting"):
        set_target(m,text)
        return

    if text=="📦 پیگیری":
        a=[
            o for o in user_orders(uid)
            if o.get("status")=="در حال انجام"
        ]

        send(
            uid,
            "📦 سفارش‌های در حال انجام:\n\n"+
            (
                "\n".join(
                    f"#{o['id']} | {o['service']}"
                    for o in a
                )
                or "📭 ندارد."
            )
        )
        return

    if text=="🧾 سفارش‌ها":
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

    if text=="📜 قوانین":
        send(
            uid,
            "📜 قوانین:\n"
            "1️⃣ آیدی صحیح ارسال کنید.\n"
            "2️⃣ مقصد عمومی باشد.\n"
            "3️⃣ پس از پرداخت رسید ارسال شود."
        )
        return

    if text=="📞 پشتیبانی":
        send(uid,SUPPORT)
        return

    if text=="🏠 اصلی":
        start(m)
        return

    send(uid,"👇 از منو انتخاب کنید.")

def get_updates(offset=""):
    global http

    try:
        p={"limit":100}

        if offset:
            p["offset_id"]=offset

        r=http.post(
            f"{bot.BASE_URL}/getUpdates",
            json=p,
            timeout=(3,8)
        )

        if r.status_code!=200:
            print("HTTP:",r.status_code)
            return [],offset

        d=r.json()

        if d.get("status")!="OK":
            print("API:",d)
            return [],offset

        data=d.get("data") or {}

        return (
            data.get("updates") or [],
            data.get("next_offset_id") or offset
        )

    except Exception as e:
        print("NETWORK:",repr(e))

        try:
            http.close()
        except:
            pass

        http=new_session()

        return [],offset

def clear_old():
    offset=read(OF)

    if offset:
        return offset

    print("CLEAR OLD UPDATES")

    for _ in range(5):
        arr,no=get_updates(offset)

        if no and no!=offset:
            offset=no
            write(OF,offset)

        if not arr:
            break

    print("OLD UPDATES CLEARED")

    return offset

def polling():
    offset=clear_old()
    errors=0

    while True:
        try:
            arr,no=get_updates(offset)

            if no and no!=offset:
                offset=no
                write(OF,offset)

            if arr:
                errors=0

                for item in arr:
                    try:
                        m=updates.Update(item).to_message()

                        if m:
                            handle(m)

                    except Exception as e:
                        print("UPDATE:",repr(e))

            else:
                time.sleep(.10)

        except exceptions.RubiBotAccessError:
            print("ACCESS ERROR")
            time.sleep(5)

        except KeyboardInterrupt:
            return

        except Exception as e:
            errors+=1

            print(
                "MAIN:",
                repr(e),
                "ERRORS:",
                errors
            )

            if errors>=3:
                try:
                    http.close()
                except:
                    pass

                http=new_session()
                errors=0

            time.sleep(1)

class Health(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type","text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self,*args):
        pass

def web():
    while True:
        try:
            server=HTTPServer(
                ("0.0.0.0",PORT),
                Health
            )

            print("WEB SERVER:",PORT)
            server.serve_forever()

        except Exception as e:
            print("WEB:",repr(e))
            time.sleep(2)

if __name__=="__main__":

    Thread(
        target=web,
        daemon=True
    ).start()

    print("================================")
    print("RUBIKA BOT STARTED")
    print("ADMIN:",ADMIN)
    print("PORT:",PORT)
    print("ORDERS:",len(ORDERS))
    print("================================")

    polling()
