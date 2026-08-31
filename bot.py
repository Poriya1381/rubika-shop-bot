from rubibot import RubiBot, types, updates, exceptions
import os,time,json,re,requests
from threading import Thread
from http.server import BaseHTTPRequestHandler,HTTPServer

TOKEN=os.getenv("TOKEN","CDBECG0UXQGRRZSSDLFQSTKDIJEHEUXGFUWQOPYPLJBBMZFYAFIKMPSEBFUIWCLH")
ADMINS={"u0KYDRB070eb6d2f015b56edb5476dcd","b0KYDRB0BBLs0d5ad48d891eca78ebfa"}
CARD="6219861932569709"
SUPPORT="@Poriysmeii"
CODE="@PoriyBot"
PORT=int(os.getenv("PORT","10000"))

BASE="data"
os.makedirs(BASE,exist_ok=True)
OF=f"{BASE}/offset.txt"
DF=f"{BASE}/orders.json"

bot=RubiBot(TOKEN)
http=requests.Session()


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


def save_orders():
    try:
        tmp=DF+".tmp"
        with open(tmp,"w",encoding="utf-8") as f:
            json.dump(ORDERS,f,ensure_ascii=False,separators=(",",":"))
        os.replace(tmp,DF)
    except Exception as e:
        print("SAVE:",repr(e))


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
        bot.send_message(str(uid),str(text),chat_keypad=key)
        return True
    except Exception as e:
        print("SEND:",repr(e))
        return False


def admin_send(text,key=ADMIN_KB):
    for admin in ADMINS:
        send(admin,text,key)


def is_admin(m):
    uid=str(getattr(m,"chat_id","") or "")
    sid=str(getattr(m,"sender_id","") or "")
    return uid in ADMINS or sid in ADMINS


def start(m):
    send(m.chat_id,"🛍 فروشگاه روبیکا\n\n👇 انتخاب کنید:")


def oid(o):
    try:
        return int(o.get("id",0))
    except:
        return 0


def num(x):
    try:
        return int(str(x).replace(",","").replace(".","").replace(" تومان","").strip())
    except:
        return 0


def money(x):
    return f"{num(x):,}"


def get_user_orders(uid):
    return [o for o in ORDERS.values() if str(o.get("chat_id"))==str(uid)]


def last_order(uid):
    orders=get_user_orders(uid)
    return max(orders,key=oid) if orders else None


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

    if re.fullmatch(r"@[A-Za-z0-9_]{3,64}",text):
        return text

    m=re.fullmatch(
        r"https?://(?:www\.)?(?:rubika\.ir|web\.rubika\.ir)/"
        r"([A-Za-z0-9_]{3,64})/?",
        text,re.I
    )

    if m:
        return "@"+m.group(1)

    return None


def show_prices(uid,items,prefix,title):
    rows=[[(prefix+x,"price")] for x in items]
    rows.append([("🔙 خدمات","services"),("🏠 اصلی","home")])
    send(uid,title,kb(rows))


def extract_price(text):
    m=re.search(r"(\d[\d,\.]*)\s*[—\-–]\s*([\d,\.]+)",text)
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
    ids=[oid(o) for o in ORDERS.values()]
    n=max(ids+[1000])+1

    ORDERS[str(n)]={
        "id":n,
        "chat_id":uid,
        "sender_id":str(getattr(m,"sender_id","") or uid),
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
        "receipt":0,
        "created":int(time.time())
    }

    save_orders()

    send(
        uid,
        "📌 یوزرنیم مقصد را ارسال کنید.\n\n"
        "مثال:\n@username\n\n"
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

📸 رسید را به صورت عکس ارسال کنید."""
    )


def set_target(m,text):
    uid=str(m.chat_id)
    o=last_order(uid)

    if not o or not o.get("waiting"):
        return

    username=normalize_username(text)

    if not username:
        send(uid,"❌ یوزرنیم نامعتبر است.\n\nمثال:\n@Poriysmeii")
        return

    o["target"]=username
    o["waiting"]=0
    o["discount_wait"]=1
    save_orders()

    send(
        uid,
        f"✅ مقصد ثبت شد:\n{username}\n\n🎁 کد تخفیف دارید؟",
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

    o["discount"]=off
    o["final"]=price-off
    o["discount_wait"]=0

    save_orders()
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
        fid=getattr(f,"id",None) or getattr(f,"file_id",None)

        if not fid:
            p=getattr(m,"photo",None)
            fid=getattr(p,"id",None) or getattr(p,"file_id",None)

        if not fid:
            raise Exception("FILE_ID_NOT_FOUND")

        file_url=bot.get_file(fid)

        if not file_url:
            raise Exception("GET_FILE_FAILED")

        data=bot.download_file(file_url)

        if not data:
            raise Exception("DOWNLOAD_FAILED")

        with open(path,"wb") as fp:
            fp.write(data)

        caption=(
            f"💰 سفارش #{o['id']}\n"
            f"🛍 {o['service']}\n"
            f"📌 {o['type']}\n"
            f"🔗 {o['target']}\n"
            f"💰 {money(o['final'])} تومان\n"
            f"👤 {o['username']}"
        )

        sent=False

        for admin in ADMINS:
            try:
                bot.send_photo(admin,path,text=caption)
                sent=True
            except Exception as e:
                print("SEND_PHOTO:",repr(e))

                try:
                    bot.send_file(admin,path,text=caption)
                    sent=True
                except Exception as e2:
                    print("SEND_FILE:",repr(e2))

        if not sent:
            raise Exception("SEND_RECEIPT_FAILED")

        o["receipt"]=1
        save_orders()

        send(uid,"✅ رسید با موفقیت دریافت شد.\n⏳ در انتظار بررسی ادمین.")

    except Exception as e:
        print("RECEIPT:",repr(e))
        send(uid,"❌ ارسال رسید ناموفق بود.\nلطفاً عکس را دوباره ارسال کنید.")

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
            [(f"🔵 شروع #{n}","start"),(f"🟢 تکمیل #{n}","done")],
            [(f"🔴 لغو #{n}","cancel")],
            [("🔙 پنل مدیریت","admin")]
        ])

    if o["status"]=="در حال انجام":
        return kb([
            [(f"🟢 تکمیل #{n}","done"),(f"🔴 لغو #{n}","cancel")],
            [("🔙 پنل مدیریت","admin")]
        ])

    return ADMIN_KB


def admin_list(status,admin_id):
    orders=sorted(
        [o for o in ORDERS.values() if o.get("status")==status],
        key=oid,
        reverse=True
    )

    if not orders:
        send(admin_id,f"📭 سفارشی با وضعیت «{status}» وجود ندارد.",ADMIN_KB)
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


def change_status(order_id,status,admin_id):
    o=next(
        (x for x in ORDERS.values() if str(x.get("id"))==str(order_id)),
        None
    )

    if not o:
        send(admin_id,f"❌ سفارش #{order_id} پیدا نشد.",ADMIN_KB)
        return

    o["status"]=status
    o["waiting"]=0
    o["discount_wait"]=0
    save_orders()

    send(
        o["chat_id"],
        f"📦 سفارش #{order_id}\n📊 وضعیت: {status}"
    )

    send(
        admin_id,
        f"✅ سفارش #{order_id} → {status}",
        ADMIN_KB
    )


def admin_command(text,admin_id):

    if text in ("/admin","🔙 پنل مدیریت","⚙️ پنل مدیریت"):
        send(admin_id,"⚙️ پنل مدیریت",ADMIN_KB)
        return True

    if text=="📋 جدید":
        admin_list("در انتظار بررسی",admin_id)
        return True

    if text=="🔵 درحال انجام":
        admin_list("در حال انجام",admin_id)
        return True

    if text=="🟢 تکمیل":
        admin_list("تکمیل شد",admin_id)
        return True

    if text=="🔴 لغوشده":
        admin_list("لغو شد",admin_id)
        return True

    if text=="🗑 حذف لغوشده":
        keys=[k for k,o in ORDERS.items() if o.get("status")=="لغو شد"]

        for k in keys:
            del ORDERS[k]

        save_orders()
        send(admin_id,f"🗑 {len(keys)} سفارش حذف شد.",ADMIN_KB)
        return True

    m=re.match(r"^🔵 شروع\s*#(\d+)$",text)
    if m:
        change_status(m.group(1),"در حال انجام",admin_id)
        return True

    m=re.match(r"^🟢 تکمیل\s*#(\d+)$",text)
    if m:
        change_status(m.group(1),"تکمیل شد",admin_id)
        return True

    m=re.match(r"^🔴 لغو\s*#(\d+)$",text)
    if m:
        change_status(m.group(1),"لغو شد",admin_id)
        return True

    return False


def handle(m):
    if not m:
        return

    uid=str(getattr(m,"chat_id","") or "")
    sid=str(getattr(m,"sender_id","") or "")
    text=(getattr(m,"text","") or "").strip()

    print("MESSAGE:",sid or uid,repr(text))

    if is_admin(m):
        if admin_command(text,uid):
            return

        if text=="🏠 اصلی":
            start(m)
            return

    if text.startswith("/start"):
        start(m)
        return

    if text in ("❌ خروج","❌ لغو"):
        for key,o in list(ORDERS.items()):
            if str(o.get("chat_id"))==uid and (
                o.get("waiting") or o.get("discount_wait")
            ):
                del ORDERS[key]

        save_orders()
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
        show_prices(uid,CHANNEL,"📣 ","📣 تعرفه کانال")
        return

    if text=="👥 گروه":
        show_prices(uid,CHANNEL,"👥 ","👥 تعرفه گروه")
        return

    if text=="⭐ فالور":
        show_prices(uid,FOLLOWERS,"⭐ ","⭐ تعرفه فالور")
        return

    price=extract_price(text)

    if price:
        typ,service,amount=price
        create_order(m,service,amount,typ)
        return

    o=last_order(uid)

    if text=="❌ ندارم":
        if o and o.get("discount_wait"):
            o["discount_wait"]=0
            o["final"]=num(o["price"])
            save_orders()
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
            o for o in get_user_orders(uid)
            if o.get("status")=="در حال انجام"
        ]

        send(
            uid,
            "📦 سفارش‌ها:\n\n"+
            (
                "\n".join(
                    f"#{o['id']} | {o['service']} | {o['status']}"
                    for o in orders
                ) or "📭 ندارد."
            )
        )
        return

    if text=="🧾 سفارش‌ها":
        orders=sorted(
            get_user_orders(uid),
            key=oid,
            reverse=True
        )[:20]

        send(
            uid,
            "🧾 سفارش‌ها:\n\n"+
            (
                "\n".join(
                    f"#{o['id']} | {o['service']} | {o['status']}"
                    for o in orders
                ) or "📭 ندارد."
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


def process_update(item):
    try:
        m=updates.Update(item).to_message()
        if m:
            handle(m)
    except Exception as e:
        print("UPDATE:",repr(e))


def get_updates(offset=""):
    try:
        params={"limit":100}

        if offset:
            params["offset_id"]=offset

        r=http.post(
            f"{bot.BASE_URL}/getUpdates",
            json=params,
            timeout=(3,15)
        )

        if r.status_code!=200:
            print("HTTP:",r.status_code)
            return [],offset

        data=r.json()

        if data.get("status")!="OK":
            print("API:",data.get("status_det"))
            return [],offset

        x=data.get("data") or {}

        return (
            x.get("updates") or [],
            x.get("next_offset_id") or offset
        )

    except Exception as e:
        print("GET_UPDATES:",repr(e))
        return [],offset


def polling():
    print("BOT STARTED")
    print("ADMINS:",",".join(ADMINS))

    offset=read(OF)

    if not offset:
        print("CLEARING OLD UPDATES...")

        while True:
            try:
                arr,new_offset=get_updates("")

                if new_offset:
                    offset=new_offset

                if not arr:
                    break

            except Exception as e:
                print("CLEAR OLD:",repr(e))
                time.sleep(2)

        if offset:
            write(OF,offset)

        print("OLD UPDATES CLEARED")

    print("WAITING FOR NEW MESSAGES...")

    while True:
        try:
            arr,new_offset=get_updates(offset)

            if new_offset and new_offset!=offset:
                offset=new_offset
                write(OF,offset)

            for item in arr:
                process_update(item)

            if not arr:
                time.sleep(.5)

        except exceptions.RubiBotAccessError as e:
            print("ACCESS ERROR:",repr(e))
            time.sleep(3)

        except Exception as e:
            print("POLLING:",repr(e))
            time.sleep(2)


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self,*args):
        pass


def web_server():
    try:
        server=HTTPServer(
            ("0.0.0.0",PORT),
            Handler
        )

        print("WEB:",PORT)
        server.serve_forever()

    except Exception as e:
        print("WEB ERROR:",repr(e))


if __name__=="__main__":
    Thread(
        target=web_server,
        daemon=True
    ).start()

    polling()
