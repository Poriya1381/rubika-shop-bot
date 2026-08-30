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

BASE="data"
os.makedirs(BASE,exist_ok=True)

if not TOKEN:
    raise RuntimeError("TOKEN environment variable is not set")

bot=RubiBot(TOKEN)
HTTP=requests.Session()

OF=f"{BASE}/offset.txt"
DF=f"{BASE}/orders.json"

def read(path,default=""):
    try:
        with open(path,encoding="utf-8") as f:
            return f.read().strip() or default
    except:
        return default

def write(path,data):
    try:
        tmp=path+".tmp"
        with open(tmp,"w",encoding="utf-8") as f:
            f.write(str(data))
        os.replace(tmp,path)
    except:
        pass

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
                ORDERS,
                f,
                ensure_ascii=False,
                separators=(",",":")
            )
        os.replace(tmp,DF)
    except Exception as e:
        print("SAVE:",repr(e))

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

def last_order(uid):
    a=user_orders(uid)
    return max(a,key=oid) if a else None

def get_username(m):
    try:
        c=bot.get_chat(str(m.chat_id))
        u=getattr(c,"username",None)

        if u:
            return "@"+str(u).lstrip("@")

    except:
        pass

    return "ندارد"

def normalize_username(text):
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
        text,
        re.I
    )

    if m:
        return "@"+m.group(1)

    return None

def show_prices(uid,items,prefix,title):
    rows=[
        [(prefix+x,"price")]
        for x in items
    ]

    rows.append([
        ("🔙 خدمات","services"),
        ("🏠 اصلی","home")
    ])

    send(
        uid,
        title,
        kb(rows)
    )

def extract_price(text):
    """
    تشخیص قیمت حتی اگر قبل یا بعد آن متن اضافی باشد.
    مثال:
    📣 5,000 — 500,000
    ⭐ 10,000 - 950,000
    """

    m=re.search(
        r"(\d[\d,\.]*)\s*[—\-–]\s*([\d,\.]+)",
        text
    )

    if not m:
        return None

    count=m.group(1)
    price=m.group(2)

    if text.lstrip().startswith("📣"):
        typ="کانال"
    elif text.lstrip().startswith("👥"):
        typ="گروه"
    elif text.lstrip().startswith("⭐"):
        typ="روبینو"
    else:
        return None

    return typ,count,price

def create_order(m,service,price,typ):
    uid=str(m.chat_id)

    n=max(
        [oid(x) for x in ORDERS.values()]+[1000]
    )+1

    ORDERS[str(n)]={
        "id":n,
        "chat_id":uid,
        "sender_id":str(
            getattr(m,"sender_id","") or uid
        ),
        "username":get_username(m),
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
        "کانال، پیج یا گروه را به این شکل بفرستید:\n"
        "@username\n\n"
        "مثال:\n"
        "@Poriysmeii\n\n"
        "یا لینک روبیکا را ارسال کنید.",
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

    username=normalize_username(text)

    if not username:

        send(
            uid,
            "❌ یوزرنیم نامعتبر است.\n\n"
            "فقط به این شکل ارسال کنید:\n"
            "@username\n\n"
            "مثال:\n"
            "@Poriysmeii"
        )

        return

    o.update({
        "target":username,
        "waiting":0,
        "discount_wait":1
    })

    save()

    send(
        uid,
        f"✅ مقصد ثبت شد:\n{username}\n\n"
        "🎁 کد تخفیف دارید؟",
        kb([
            [("❌ ندارم","no_discount")],
            [("❌ خروج","cancel")]
        ])
    )

def discount(m,text):
    uid=str(m.chat_id)
    o=last_order(uid)

    if not o:
        return

    if text.strip().lower()!=CODE.lower():

        send(
            uid,
            "❌ کد تخفیف نامعتبر است.",
            kb([
                [("❌ ندارم","no_discount")],
                [("❌ خروج","cancel")]
            ])
        )

        return

    price=num(o["price"])
    off=price*20//100

    o.update({
        "discount":off,
        "final":price-off,
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

    orders=sorted(
        [
            o for o in ORDERS.values()
            if o.get("status")==status
        ],
        key=oid,
        reverse=True
    )

    if not orders:
        send(
            ADMIN,
            "📭 سفارشی نیست.",
            ADMIN_KB
        )
        return

    for o in orders[:30]:

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

def change_status(order_id,status):

    o=next(
        (
            x for x in ORDERS.values()
            if str(x.get("id"))==str(order_id)
        ),
        None
    )

    if not o:
        send(
            ADMIN,
            f"❌ سفارش #{order_id} پیدا نشد.",
            ADMIN_KB
        )
        return

    o.update({
        "status":status,
        "waiting":0,
        "discount_wait":0
    })

    save()

    send(
        o["chat_id"],
        f"📦 سفارش #{order_id}\n📊 وضعیت: {status}"
    )

    send(
        ADMIN,
        f"✅ سفارش #{order_id} → {status}",
        ADMIN_KB
    )

def admin_command(text):

    if text=="/admin":

        send(
            ADMIN,
            "⚙️ پنل مدیریت",
            ADMIN_KB
        )

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

        action,number=m.groups()

        status={
            "🔵 شروع":"در حال انجام",
            "🟢 تکمیل":"تکمیل شد",
            "🔴 لغو":"لغو شد"
        }[action]

        change_status(number,status)

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

    # ادمین
    if text=="/admin":

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

        if admin_command(text):
            return

    if text.startswith("/start"):
        start(m)
        return

    # لغو
    if text in ("❌ خروج","❌ لغو"):

        changed=False

        for key,o in list(ORDERS.items()):

            if (
                str(o.get("chat_id"))==uid
                and (
                    o.get("waiting")
                    or o.get("discount_wait")
                )
            ):
                del ORDERS[key]
                changed=True

        if changed:
            save()

        send(uid,"✅ لغو شد.")
        return

    # منو
    if text=="🛍 خدمات":

        send(
            uid,
            "🛍 خدمات روبیکا",
            SERV
        )

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

        send(
            uid,
            "🛍 خدمات",
            SERV
        )

        return

    if text=="📣 کانال":

        show_prices(
            uid,
            CHANNEL,
            "📣 ",
            "📣 تعرفه کانال"
        )

        return

    if text=="👥 گروه":

        show_prices(
            uid,
            CHANNEL,
            "👥 ",
            "👥 تعرفه گروه"
        )

        return

    if text=="⭐ فالور":

        show_prices(
            uid,
            FOLLOWERS,
            "⭐ ",
            "⭐ تعرفه فالور"
        )

        return

    # ⭐ مهم:
    # تشخیص قیمت قبل از بررسی سفارش قبلی
    price_data=extract_price(text)

    if price_data:

        typ,service,price=price_data

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

        discount(m,text)
        return

    if o and o.get("waiting"):

        set_target(m,text)
        return

    if text=="📦 پیگیری":

        orders=[
            o for o in user_orders(uid)
            if o.get("status")=="در حال انجام"
        ]

        send(
            uid,
            "📦 سفارش‌ها:\n\n"+
            (
                "\n".join(
                    f"#{o['id']} | {o['service']}"
                    for o in orders
                )
                or "📭 ندارد."
            )
        )

        return

    if text=="🧾 سفارش‌ها":

        orders=sorted(
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
                    for o in orders
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

    send(
        uid,
        "👇 از منو انتخاب کنید."
    )

def get_updates(offset=""):

    try:

        params={"limit":100}

        if offset:
            params["offset_id"]=offset

        r=HTTP.post(
            f"{bot.BASE_URL}/getUpdates",
            json=params,
            timeout=(3,10)
        )

        if r.status_code!=200:
            return [],offset

        data=r.json()

        if data.get("status")!="OK":
            return [],offset

        x=data.get("data") or {}

        return (
            x.get("updates") or [],
            x.get("next_offset_id") or offset
        )

    except Exception as e:

        print("NETWORK:",repr(e))
        return [],offset

def clear_old_updates():

    offset=read(OF)

    if offset:
        return offset

    print("CLEAR OLD UPDATES")

    empty=0

    while empty<2:

        arr,no=get_updates(offset)

        if no and no!=offset:
            offset=no
            write(OF,offset)

        if not arr:
            empty+=1
        else:
            empty=0

    print("OLD UPDATES CLEARED")

    return offset

def polling():

    offset=clear_old_updates()

    while True:

        try:

            arr,no=get_updates(offset)

            if no and no!=offset:

                offset=no
                write(OF,offset)

            for item in arr:

                try:

                    m=updates.Update(
                        item
                    ).to_message()

                    if m:
                        handle(m)

                except Exception as e:

                    print(
                        "UPDATE:",
                        repr(e)
                    )

            if not arr:
                time.sleep(.2)

        except exceptions.RubiBotAccessError:

            print("ACCESS ERROR")
            time.sleep(5)

        except KeyboardInterrupt:

            return

        except Exception as e:

            print(
                "MAIN:",
                repr(e)
            )

            time.sleep(2)

class Health(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self,*args):
        pass

def web():

    while True:

        try:

            HTTPServer(
                ("0.0.0.0",PORT),
                Health
            ).serve_forever()

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
    print("PORT:",PORT)
    print("================================")

    polling()
