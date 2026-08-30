from rubibot import RubiBot,types,updates,exceptions
import requests,os,time,json,re,threading
from http.server import BaseHTTPRequestHandler,HTTPServer

TOKEN=os.getenv("RUBIKA_BOT_TOKEN","").strip()
CARD=os.getenv("CARD_NUMBER","6219861932569709").strip()
SUPPORT=os.getenv("SUPPORT_USERNAME","@Poriysmeii").strip()
BASE=os.getenv("DATA_DIR",".")

ADMIN_FILE=f"{BASE}/admin_id.txt"
OFFSET_FILE=f"{BASE}/rubika_offset.txt"
ORDERS_FILE=f"{BASE}/orders.json"

bot=RubiBot(TOKEN) if TOKEN else None
ADMIN_ID=None
ORDERS={}

def read(p,d=None):
    try:
        if os.path.exists(p):
            with open(p,encoding="utf-8") as f:
                return f.read().strip() or d
    except:
        pass
    return d

def save(p,v):
    try:
        with open(p,"w",encoding="utf-8") as f:
            f.write(str(v))
    except:
        pass

ADMIN_ID=os.getenv("ADMIN_ID","").strip() or read(ADMIN_FILE)

try:
    ORDERS=json.loads(read(ORDERS_FILE,"{}"))
    if not isinstance(ORDERS,dict):
        ORDERS={}
except:
    ORDERS={}

def save_orders():
    try:
        with open(ORDERS_FILE,"w",encoding="utf-8") as f:
            json.dump(ORDERS,f,ensure_ascii=False)
    except:
        pass

def get_updates(offset=None):
    p={"limit":10}

    if offset:
        p["offset_id"]=offset

    try:
        r=requests.post(
            f"{bot.BASE_URL}/getUpdates",
            json=p,
            timeout=60
        )

        if r.status_code in (502,503,504):
            print("RUBIKA SERVER ERROR:",r.status_code)
            time.sleep(5)
            return [],offset

        if r.status_code!=200:
            print("HTTP ERROR:",r.status_code)
            time.sleep(5)
            return [],offset

        text=r.text.strip()

        if not text:
            print("EMPTY RESPONSE")
            time.sleep(3)
            return [],offset

        try:
            d=r.json()
        except:
            print(
                "INVALID RESPONSE:",
                r.status_code,
                repr(text[:150])
            )
            time.sleep(3)
            return [],offset

        if d.get("status")!="OK":
            print("GET UPDATES ERROR:",d)
            time.sleep(3)
            return [],offset

        x=d.get("data") or {}

        if not isinstance(x,dict):
            return [],offset

        arr=x.get("updates") or []

        return (
            [updates.Update(i) for i in arr],
            x.get("next_offset_id") or offset
        )

    except requests.exceptions.Timeout:
        print("GET UPDATES TIMEOUT")
        time.sleep(5)
        return [],offset

    except requests.exceptions.ConnectionError:
        print("CONNECTION ERROR")
        time.sleep(5)
        return [],offset

    except requests.exceptions.RequestException as e:
        print("REQUEST ERROR:",repr(e))
        time.sleep(5)
        return [],offset

    except Exception as e:
        print("GET UPDATES ERROR:",repr(e))
        time.sleep(5)
        return [],offset

def kb(rows):
    k=types.ChatKeypad(resize_keyboard=True)

    for row in rows:
        r=types.KeypadRow()

        for t,d in row:
            r.add(types.KeypadSimpleButton(t,d))

        k.add(r)

    return k

def main_kb():
    return kb([
        [("🛍 خدمات روبیکا","services")],
        [("📜 قوانین","rules")],
        [("📞 پشتیبانی","support")]
    ])

def services_kb():
    return kb([
        [("📣 افزایش کانال","channel"),("👥 افزایش گروه","group")],
        [("⭐ افزایش روبینو","followers")],
        [("🏠 منوی اصلی","home")]
    ])

CHANNEL=[
    "100 — 20,000",
    "500 — 60,000",
    "1,000 — 110,000",
    "5,000 — 500,000",
    "10,000 — 950,000"
]

GROUP=CHANNEL[:]

FOLLOWERS=[
    "1,000 — 15,000",
    "10,000 — 100,000",
    "50,000 — 450,000",
    "100,000 — 800,000",
    "150,000 — 1,000,000"
]

def price_kb(items,p):
    return kb(
        [[(p+x,"price")] for x in items]+
        [[("🔙 خدمات","services"),("🏠 اصلی","home")]]
    )

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
        c=bot.get_chat(str(m.chat_id))
        u=getattr(c,"username",None)

        if u:
            return "@"+str(u).lstrip("@")

    except:
        pass

    return "ندارد"

def normalize_link(t):
    t=t.strip()

    if t.startswith("@"):
        u=t[1:].strip()

        if re.fullmatch(r"[A-Za-z0-9_]{3,64}",u):
            return "@"+u

        return None

    m=re.match(
        r"^https?://(?:www\.)?(?:rubika\.ir|web\.rubika\.ir)/([^/?#\s]+)",
        t,
        re.I
    )

    if m:
        u=m.group(1).lstrip("@")

        if re.fullmatch(r"[A-Za-z0-9_]{3,64}",u):
            return "@"+u

    return None

def new_order(m,service,price,typ):
    uid=str(m.chat_id)

    ORDERS[uid]={
        "sender_id":str(getattr(m,"sender_id","") or ""),
        "username":get_username(m),
        "service":service,
        "price":price,
        "type":typ,
        "target":"",
        "waiting":True,
        "receipt":False
    }

    save_orders()

    if typ=="کانال":
        title="📌 آیدی کانال را ارسال کنید"
    elif typ=="گروه":
        title="📌 آیدی گروه را ارسال کنید"
    else:
        title="📌 آیدی پیج را وارد کنید"

    bot.send_message(
        uid,
        f"""{title}

مثال:
@username

⚠️ فقط آیدی عمومی روبیکا را ارسال کنید.""",
        chat_keypad=main_kb()
    )

def set_target(m,text):
    o=ORDERS.get(str(m.chat_id))

    if not o:
        return

    link=normalize_link(text)

    if not link:
        if o["type"]=="کانال":
            title="📌 آیدی کانال را ارسال کنید"
        elif o["type"]=="گروه":
            title="📌 آیدی گروه را ارسال کنید"
        else:
            title="📌 آیدی پیج را وارد کنید"

        bot.send_message(
            m.chat_id,
            f"""❌ آیدی نامعتبر است.

{title}

مثال:
@username

⚠️ فقط آیدی عمومی روبیکا را ارسال کنید.""",
            chat_keypad=main_kb()
        )
        return

    o["target"]=link
    o["waiting"]=False
    o["username"]=get_username(m)

    save_orders()

    bot.send_message(
        m.chat_id,
        f"""✅ مقصد با موفقیت ثبت شد

🛍 {o["service"]}
📌 نوع: {o["type"]}
🔗 {o["target"]}

💰 {o["price"]} تومان

💳 شماره کارت:
{CARD}

👤 به نام پوریا سمیعی

📸 بعد از واریز، عکس رسید را همینجا ارسال کنید.
⚠️ پس از ارسال رسید، برای پشتیبانی فرستاده می‌شود.""",
        chat_keypad=main_kb()
    )

def receipt_text(m,o):
    return f"""💰 سفارش پرداختی جدید

🛍 خدمت: {o["service"]}
📌 نوع: {o["type"]}
💰 مبلغ: {o["price"]} تومان

🔗 آیدی مقصد:
{o["target"]}

👤 یوزرنیم کاربر:
{o.get("username","ندارد")}

🆔 شناسه کاربر:
{o.get("sender_id","ندارد")}

🆔 چت کاربر:
{m.chat_id}

📸 رسید دریافت شد."""

def send_admin(m,o):
    if not ADMIN_ID:
        return False

    try:
        f=getattr(m,"file",None)

        fid=(
            getattr(f,"id",None)
            or getattr(f,"file_id",None)
        )

        if not fid:
            return False

        url=bot.get_file(fid)
        data=bot.download_file(url)

        if not data:
            return False

        path=f"{BASE}/receipt.jpg"

        with open(path,"wb") as x:
            x.write(data)

        with open(path,"rb") as x:
            bot.send_photo(
                ADMIN_ID,
                x,
                text=receipt_text(m,o)
            )

        try:
            os.remove(path)
        except:
            pass

        return True

    except Exception as e:
        print("RECEIPT ERROR:",repr(e))
        return False

def is_media(m):
    try:
        if getattr(m,"file",None):
            return True

        if getattr(m,"photo",None):
            return True

        if getattr(m,"image",None):
            return True

    except:
        pass

    return False

def file_received(m):
    uid=str(m.chat_id)
    o=ORDERS.get(uid)

    if not o:
        bot.send_message(
            uid,
            "❌ سفارش فعالی ندارید.",
            chat_keypad=main_kb()
        )
        return

    if not o.get("target"):
        bot.send_message(
            uid,
            "❌ ابتدا آیدی مقصد را ارسال کنید."
        )
        return

    if o.get("receipt"):
        bot.send_message(
            uid,
            "⚠️ این رسید قبلاً دریافت شده است."
        )
        return

    if send_admin(m,o):

        o["receipt"]=True
        o["receipt_message_id"]=str(
            getattr(m,"message_id","")
        )

        save_orders()

        bot.send_message(
            uid,
"""✅ رسید دریافت شد و برای ادمین ارسال شد.

⏳ منتظر بررسی باشید.""",
            chat_keypad=main_kb()
        )

    else:
        bot.send_message(
            uid,
f"""❌ عکس رسید ارسال نشد.

📞 لطفاً به پشتیبانی پیام دهید و موارد زیر را ارسال کنید:

📸 عکس رسید پرداخت
🔗 آیدی کانال

👤 پشتیبانی:
{SUPPORT}""",
            chat_keypad=main_kb()
        )

def handle(m):
    global ADMIN_ID

    if not m:
        return

    uid=str(m.chat_id)
    text=(getattr(m,"text","") or "").strip()

    if text.startswith("/admin"):

        if ADMIN_ID and uid!=str(ADMIN_ID):
            bot.send_message(
                uid,
                "❌ دسترسی ندارید."
            )
            return

        ADMIN_ID=uid
        save(ADMIN_FILE,uid)

        bot.send_message(
            uid,
            "✅ ادمین ذخیره شد."
        )
        return

    if text.startswith("/start"):

        if not ADMIN_ID:
            ADMIN_ID=uid
            save(ADMIN_FILE,uid)

        start(m)
        return

    if is_media(m):
        file_received(m)
        return

    o=ORDERS.get(uid)

    if o and o.get("waiting"):

        if text:
            set_target(m,text)

        return

    if text=="🛍 خدمات روبیکا":
        bot.send_message(
            uid,
            "🛍 خدمات روبیکا",
            chat_keypad=services_kb()
        )
        return

    if text=="📣 افزایش کانال":
        bot.send_message(
            uid,
            "📣 تعرفه افزایش کانال",
            chat_keypad=price_kb(CHANNEL,"📣 ")
        )
        return

    if text=="👥 افزایش گروه":
        bot.send_message(
            uid,
            "👥 تعرفه افزایش گروه",
            chat_keypad=price_kb(GROUP,"👥 ")
        )
        return

    if text=="⭐ افزایش روبینو":
        bot.send_message(
            uid,
            "⭐ تعرفه افزایش روبینو",
            chat_keypad=price_kb(FOLLOWERS,"⭐ ")
        )
        return

    if text=="📜 قوانین":
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

    if text=="📞 پشتیبانی":
        bot.send_message(
            uid,
f"""📞 پشتیبانی

👤 آیدی پشتیبانی:
{SUPPORT}""",
            chat_keypad=main_kb()
        )
        return

    if text=="🔙 خدمات":
        bot.send_message(
            uid,
            "🛍 خدمات روبیکا",
            chat_keypad=services_kb()
        )
        return

    if text=="🏠 منوی اصلی":
        start(m)
        return

    for p,typ in [
        ("📣 ","کانال"),
        ("👥 ","گروه"),
        ("⭐ ","روبینو")
    ]:

        if text.startswith(p) and " — " in text:

            s,price=text[len(p):].split(
                " — ",
                1
            )

            new_order(
                m,
                s,
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
    port=int(os.getenv("PORT","10000"))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type","text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Rubika bot is running")

        def log_message(self, format, *args):
            return

    server=HTTPServer(("0.0.0.0",port),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    print("HEALTH SERVER:",port)


def run():
    if not TOKEN:
        raise RuntimeError("RUBIKA_BOT_TOKEN is not set")
    if bot is None:
        raise RuntimeError("Bot could not be initialized")
    start_health_server()
    print("================================")
    print("BOT STARTED")
    print("ADMIN ID:",ADMIN_ID or "NOT SET")
    print("API:",bot.BASE_URL)
    print("================================")

    offset=read(OFFSET_FILE)

    while True:

        try:
            us,no=get_updates(offset)

            if no and no!=offset:
                offset=no
                save(OFFSET_FILE,offset)

            for u in us:
                try:
                    handle(u.to_message())
                except Exception as e:
                    print(
                        "UPDATE ERROR:",
                        repr(e)
                    )

            if not us:
                time.sleep(1)

        except exceptions.RubiBotAccessError:
            print("INVALID_ACCESS")
            time.sleep(10)

        except KeyboardInterrupt:
            print("BOT STOPPED")
            break

        except Exception as e:
            print(
                "MAIN ERROR:",
                repr(e)
            )
            time.sleep(5)

if __name__=="__main__":
    while True:
        try:
            run()
        except KeyboardInterrupt:
            print("BOT STOPPED")
            break
        except Exception as e:
            print("RESTARTING:",repr(e))
            time.sleep(5)