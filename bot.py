from rubibot import RubiBot,types,updates,exceptions
import requests,os,time,json,re,threading
from http.server import BaseHTTPRequestHandler,HTTPServer

TOKEN=os.getenv("RUBIKA_BOT_TOKEN","").strip()
CARD=os.getenv("CARD_NUMBER","6219861932569709").strip()
SUPPORT=os.getenv("SUPPORT_USERNAME","@Poriysmeii").strip()
BASE=os.getenv("DATA_DIR",".")
ADMIN_FILE=f"{BASE}/admin_id.txt"; OFFSET_FILE=f"{BASE}/rubika_offset.txt"; ORDERS_FILE=f"{BASE}/orders.json"

bot=RubiBot(TOKEN) if TOKEN else None
ADMIN_ID=os.getenv("ADMIN_ID","").strip()
ORDERS={}

def read(p,d=""):
    try:
        with open(p,encoding="utf-8") as f:return f.read().strip() or d
    except:return d

def save(p,v):
    try:
        with open(p,"w",encoding="utf-8") as f:f.write(str(v))
    except:pass

if not ADMIN_ID: ADMIN_ID=read(ADMIN_FILE)

try: ORDERS=json.loads(read(ORDERS_FILE,"{}"))
except: ORDERS={}
if not isinstance(ORDERS,dict): ORDERS={}

def save_orders():
    try:
        with open(ORDERS_FILE,"w",encoding="utf-8") as f:json.dump(ORDERS,f,ensure_ascii=False)
    except:pass

def get_updates(offset=None):
    try:
        p={"limit":10}
        if offset:p["offset_id"]=offset
        r=requests.post(f"{bot.BASE_URL}/getUpdates",json=p,timeout=70)
        if r.status_code==429:return [],offset,30
        if r.status_code!=200:return [],offset,10
        d=r.json()
        if d.get("status")!="OK":
            msg=str(d).upper()
            return [],offset,30 if "TOO_REQUESTS" in msg or "NOT ACCESS" in msg else 10
        x=d.get("data") or {}
        return x.get("updates") or [],x.get("next_offset_id") or offset,3
    except Exception as e:
        print("GET UPDATES:",repr(e),flush=True)
        return [],offset,10

def kb(rows):
    k=types.ChatKeypad(resize_keyboard=True)
    for row in rows:
        r=types.KeypadRow()
        for t,d in row:r.add(types.KeypadSimpleButton(t,d))
        k.add(r)
    return k

MAIN=kb([
    [("🛍 خدمات روبیکا","services")],
    [("📜 قوانین","rules"),("📞 پشتیبانی","support")]
])

SERVICES=kb([
    [("📣 افزایش کانال","channel"),("👥 افزایش گروه","group")],
    [("⭐ افزایش روبینو","followers")],
    [("🏠 منوی اصلی","home")]
])

EXIT=kb([[("❌ خروج","cancel_order")]])

CHANNEL=[
    "100 — 200","500 — 500","1,000 — 800",
    "5,000 — 1,200","10,000 — 1,400","15,000 — 1,600"
]

GROUP=[
    "100 — 200","500 — 500","1,000 — 800",
    "5,000 — 1,200","10,000 — 1,400"
]

FOLLOWERS=[
    "1,000 — 500","10,000 — 1,500","50,000 — 5,000",
    "100,000 — 9,500","150,000 — 14,500"
]

def price_kb(items,p):
    return kb([[(
        p+x,"price"
    )] for x in items]+[
        [("🔙 خدمات","services"),("🏠 اصلی","home")]
    ])

def start(m):
    bot.send_message(m.chat_id,
"""🛍 فروشگاه خدمات روبیکا

سلام دوست عزیز 👋

خدمت موردنظر را انتخاب کنید 👇""",chat_keypad=MAIN)

def username(m):
    try:
        u=getattr(bot.get_chat(str(m.chat_id)),"username",None)
        return "@"+str(u).lstrip("@") if u else "ندارد"
    except:return "ندارد"

def normalize(t):
    t=t.strip()
    if t.startswith("@"):
        u=t[1:]
    else:
        m=re.match(r"^https?://(?:www\.)?(?:rubika\.ir|web\.rubika\.ir)/([^/?#\s]+)",t,re.I)
        if not m:return None
        u=m.group(1).lstrip("@")
    return "@"+u if re.fullmatch(r"[A-Za-z0-9_]{3,64}",u) else None

def new_order(m,service,price,typ):
    uid=str(m.chat_id)
    ORDERS[uid]={
        "sender_id":str(getattr(m,"sender_id","") or ""),
        "username":username(m),
        "service":service,
        "price":price,
        "type":typ,
        "target":"",
        "waiting":True,
        "receipt":False
    }
    save_orders()
    title={"کانال":"آیدی کانال","گروه":"آیدی گروه","روبینو":"آیدی پیج روبینو"}[typ]
    bot.send_message(uid,
f"""📌 {title} را ارسال کنید

مثال:
@username

⚠️ فقط آیدی عمومی روبیکا را ارسال کنید.

❌ برای لغو، دکمه خروج را بزنید.""",chat_keypad=EXIT)

def set_target(m,text):
    o=ORDERS.get(str(m.chat_id))
    if not o:return
    link=normalize(text)
    if not link:
        title={"کانال":"آیدی کانال","گروه":"آیدی گروه","روبینو":"آیدی پیج روبینو"}[o["type"]]
        bot.send_message(m.chat_id,
f"""❌ آیدی نامعتبر است.

📌 {title} را ارسال کنید

مثال:
@username

❌ برای لغو، دکمه خروج را بزنید.""",chat_keypad=EXIT)
        return
    o.update(target=link,waiting=False,username=username(m))
    save_orders()
    bot.send_message(m.chat_id,
f"""✅ مقصد ثبت شد

🛍 {o["service"]}
📌 نوع: {o["type"]}
🔗 {o["target"]}

💰 {o["price"]} تومان

💳 شماره کارت:
{CARD}

👤 به نام پوریا سمیعی

📸 عکس رسید را همینجا ارسال کنید.""",chat_keypad=MAIN)

def receipt_text(m,o):
    return f"""💰 سفارش پرداختی جدید

🛍 خدمت: {o["service"]}
📌 نوع: {o["type"]}
💰 مبلغ: {o["price"]} تومان

🔗 مقصد:
{o["target"]}

👤 یوزرنیم:
{o.get("username","ندارد")}

🆔 شناسه:
{o.get("sender_id","ندارد")}

🆔 چت:
{m.chat_id}

📸 رسید دریافت شد."""

def send_admin(m,o):
    if not ADMIN_ID:return False
    try:
        f=getattr(m,"file",None)
        fid=getattr(f,"id",None) or getattr(f,"file_id",None)
        if not fid:return False
        data=bot.download_file(bot.get_file(fid))
        if not data:return False
        path=f"{BASE}/receipt.jpg"
        with open(path,"wb") as x:x.write(data)
        with open(path,"rb") as x:bot.send_photo(ADMIN_ID,x,text=receipt_text(m,o))
        try:os.remove(path)
        except:pass
        return True
    except Exception as e:
        print("RECEIPT:",repr(e),flush=True)
        return False

def media(m):
    return bool(getattr(m,"file",None) or getattr(m,"photo",None) or getattr(m,"image",None))

def receipt(m):
    uid=str(m.chat_id);o=ORDERS.get(uid)
    if not o:
        bot.send_message(uid,"❌ سفارش فعالی ندارید.",chat_keypad=MAIN);return
    if not o.get("target"):
        bot.send_message(uid,"❌ ابتدا آیدی مقصد را ارسال کنید.",chat_keypad=EXIT);return
    if o.get("receipt"):
        bot.send_message(uid,"⚠️ رسید قبلاً دریافت شده.",chat_keypad=MAIN);return
    if send_admin(m,o):
        o["receipt"]=True;save_orders()
        bot.send_message(uid,"✅ رسید دریافت شد و برای ادمین ارسال شد.\n\n⏳ منتظر بررسی باشید.",chat_keypad=MAIN)
    else:
        bot.send_message(uid,f"❌ ارسال رسید ناموفق بود.\n\n📞 پشتیبانی: {SUPPORT}",chat_keypad=MAIN)

def handle(m):
    global ADMIN_ID
    if not m:return
    uid=str(m.chat_id);text=(getattr(m,"text","") or "").strip()

    if text.startswith("/admin"):
        if ADMIN_ID and uid!=str(ADMIN_ID):
            bot.send_message(uid,"❌ دسترسی ندارید.");return
        ADMIN_ID=uid;save(ADMIN_FILE,uid)
        bot.send_message(uid,"✅ ادمین ذخیره شد.");return

    if text.startswith("/start"):
        if not ADMIN_ID:ADMIN_ID=uid;save(ADMIN_FILE,uid)
        start(m);return

    if text=="❌ خروج":
        ORDERS.pop(uid,None);save_orders()
        bot.send_message(uid,"❌ سفارش لغو شد.\n\nبه منوی خدمات برگشتید 👇",chat_keypad=SERVICES);return

    if media(m):
        receipt(m);return

    o=ORDERS.get(uid)
    if o and o.get("waiting"):
        if text:set_target(m,text)
        return

    menus={
        "🛍 خدمات روبیکا":("🛍 خدمات روبیکا",SERVICES),
        "📣 افزایش کانال":("📣 تعرفه افزایش کانال",price_kb(CHANNEL,"📣 ")),
        "👥 افزایش گروه":("👥 تعرفه افزایش گروه",price_kb(GROUP,"👥 ")),
        "⭐ افزایش روبینو":("⭐ تعرفه افزایش روبینو",price_kb(FOLLOWERS,"⭐ ")),
        "🔙 خدمات":("🛍 خدمات روبیکا",SERVICES)
    }

    if text in menus:
        msg,key=menus[text]
        bot.send_message(uid,msg,chat_keypad=key);return

    if text=="🏠 منوی اصلی":
        start(m);return

    if text=="📜 قوانین":
        bot.send_message(uid,f"""📜 قوانین ثبت سفارش

1️⃣ پس از ثبت سفارش، امکان لغو یا تغییر سفارش نیست.
2️⃣ آیدی صحیح مقصد را ارسال کنید.
3️⃣ مقصد باید عمومی باشد.
4️⃣ زمان انجام سفارش متغیر است.
5️⃣ پس از پرداخت، رسید را ارسال کنید.

📞 پشتیبانی:
{SUPPORT}""",chat_keypad=MAIN);return

    if text=="📞 پشتیبانی":
        bot.send_message(uid,f"📞 پشتیبانی\n\n👤 {SUPPORT}",chat_keypad=MAIN);return

    for p,typ in [("📣 ","کانال"),("👥 ","گروه"),("⭐ ","روبینو")]:
        if text.startswith(p) and " — " in text:
            service,price=text[len(p):].split(" — ",1)
            new_order(m,service,price,typ);return

    bot.send_message(uid,"از دکمه‌های منو استفاده کنید 👇",chat_keypad=MAIN)

def health():
    port=int(os.getenv("PORT","10000"))
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type","text/plain")
            self.end_headers()
            self.wfile.write(b"Rubika bot is running")
        def log_message(self,*a):pass
    threading.Thread(target=HTTPServer(("0.0.0.0",port),H).serve_forever,daemon=True).start()
    print("HEALTH SERVER:",port,flush=True)

def run():
    if not TOKEN:raise RuntimeError("RUBIKA_BOT_TOKEN is not set")
    health()
    print("BOT STARTED",flush=True)
    print("ADMIN ID:",ADMIN_ID or "NOT SET",flush=True)
    print("API:",bot.BASE_URL,flush=True)

    offset=read(OFFSET_FILE)
    backoff=0

    while True:
        try:
            arr,no,delay=get_updates(offset)
            if no and no!=offset:
                offset=no;save(OFFSET_FILE,offset)
            for x in arr:
                try:handle(updates.Update(x).to_message())
                except exceptions.RubiBotAccessError as e:raise e
                except Exception as e:
                    print("UPDATE ERROR:",repr(e),flush=True)
            backoff=0
            time.sleep(delay)
        except exceptions.RubiBotAccessError as e:
            backoff=min(30 if backoff<30 else backoff*2,120)
            print("NOT ACCESS:",repr(e),flush=True)
            print("WAIT:",backoff,"SECONDS",flush=True)
            time.sleep(backoff)
        except Exception as e:
            s=str(e).upper()
            if "TOO_REQUESTS" in s or "NOT ACCESS" in s or "429" in s:
                backoff=min(30 if backoff<30 else backoff*2,120)
                print("RATE LIMIT:",repr(e),flush=True)
                print("WAIT:",backoff,"SECONDS",flush=True)
                time.sleep(backoff)
            else:
                print("MAIN ERROR:",repr(e),flush=True)
                time.sleep(10)

while True:
    try:run()
    except KeyboardInterrupt:break
    except Exception as e:
        print("RESTART:",repr(e),flush=True)
        time.sleep(10)
