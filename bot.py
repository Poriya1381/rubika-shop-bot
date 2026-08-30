import os,time,json,re,requests,threading
from http.server import BaseHTTPRequestHandler,HTTPServer
from rubibot import RubiBot,types,updates

TOKEN=os.getenv("RUBIKA_BOT_TOKEN","").strip()
CARD=os.getenv("CARD_NUMBER","6219861932569709").strip()
SUPPORT=os.getenv("SUPPORT_USERNAME","@Poriysmeii").strip()
ADMIN=os.getenv("ADMIN_ID","").strip()
BASE=os.getenv("DATA_DIR",".")
OFF=f"{BASE}/offset.txt"
ORD=f"{BASE}/orders.json"

if not TOKEN: raise RuntimeError("RUBIKA_BOT_TOKEN is not set")
bot=RubiBot(TOKEN)

try:
    orders=json.load(open(ORD,encoding="utf-8")) if os.path.exists(ORD) else {}
except: orders={}

def save():
    try:
        json.dump(orders,open(ORD,"w",encoding="utf-8"),ensure_ascii=False)
    except: pass

def kb(rows):
    k=types.ChatKeypad(resize_keyboard=True)
    for row in rows:
        r=types.KeypadRow()
        for t,d in row:r.add(types.KeypadSimpleButton(t,d))
        k.add(r)
    return k

def main():
    return kb([
        [("🛍 خدمات روبیکا","services")],
        [("📜 قوانین","rules"),("📞 پشتیبانی","support")]
    ])

def services():
    return kb([
        [("📣 افزایش کانال","channel"),("👥 افزایش گروه","group")],
        [("⭐ افزایش روبینو","followers")],
        [("🏠 منوی اصلی","home")]
    ])

CHANNEL=[
    "1,000 — 150",
    "5,000 — 550",
    "10,000 — 1,100",
    "15,000 — 1,600"
]

GROUP=[
    "1,000 — 150",
    "5,000 — 550",
    "10,000 — 1,100"
]

FOLLOWERS=[
    "1,000 — 500",
    "10,000 — 1,500",
    "50,000 — 5,500",
    "100,000 — 9,500",
    "150,000 — 14,500"
]

def prices(items,prefix):
    return kb(
        [[(prefix+x,"price")] for x in items]+
        [[("🔙 خدمات","services"),("🏠 اصلی","home")]]
    )

def start(uid):
    bot.send_message(uid,
"""🛍 فروشگاه خدمات روبیکا

سلام دوست عزیز 👋

📣 افزایش کانال
👥 افزایش گروه
⭐ افزایش روبینو

خدمت موردنظر را انتخاب کنید 👇""",chat_keypad=main())

def valid(t):
    t=t.strip()
    if t.startswith("@"):
        u=t[1:]
    else:
        m=re.match(r"^https?://(?:www\.)?(?:rubika\.ir|web\.rubika\.ir)/([^/?#\s]+)$",t,re.I)
        if not m:return None
        u=m.group(1).lstrip("@")
    return "@"+u if re.fullmatch(r"[A-Za-z0-9_]{3,64}",u) else None

def order(uid,service,price,typ):
    orders[uid]={
        "service":service,
        "price":price,
        "type":typ,
        "target":"",
        "waiting":True,
        "receipt":False
    }
    save()
    title={"کانال":"آیدی کانال","گروه":"آیدی گروه","روبینو":"آیدی پیج"}[typ]
    bot.send_message(uid,
f"""📌 {title} را ارسال کنید

مثال:
@username

⚠️ فقط آیدی عمومی روبیکا را ارسال کنید.

❌ برای خروج از ثبت سفارش، دکمه «❌ خروج» را بزنید.""",
        chat_keypad=kb([
            [("❌ خروج","cancel")]
        ])
    )

def set_target(uid,text):
    o=orders.get(uid)
    if not o:return

    link=valid(text)
    if not link:
        title={"کانال":"آیدی کانال","گروه":"آیدی گروه","روبینو":"آیدی پیج"}[o["type"]]
        bot.send_message(uid,
f"""❌ آیدی نامعتبر است.

📌 {title} را دوباره ارسال کنید

مثال:
@username

⚠️ فقط آیدی عمومی روبیکا را ارسال کنید.""",
            chat_keypad=kb([[("❌ خروج","cancel")]]))
        return

    o["target"]=link
    o["waiting"]=False
    save()

    bot.send_message(uid,
f"""✅ مقصد با موفقیت ثبت شد

🛍 خدمت: {o["service"]}
📌 نوع: {o["type"]}
🔗 {link}

💰 مبلغ: {o["price"]} تومان

💳 شماره کارت:
{CARD}

👤 به نام پوریا سمیعی

📸 بعد از واریز، عکس رسید را همینجا ارسال کنید.""",
        chat_keypad=main())

def receipt_text(uid,o):
    return f"""💰 سفارش جدید

🛍 خدمت: {o["service"]}
📌 نوع: {o["type"]}
💰 مبلغ: {o["price"]} تومان

🔗 مقصد:
{o["target"]}

🆔 چت کاربر:
{uid}

📸 رسید دریافت شد."""

def send_receipt(m,o):
    if not ADMIN:return False
    try:
        f=getattr(m,"file",None)
        fid=getattr(f,"id",None) or getattr(f,"file_id",None)
        if not fid:return False
        data=bot.download_file(bot.get_file(fid))
        if not data:return False
        path=f"{BASE}/receipt.jpg"
        open(path,"wb").write(data)
        with open(path,"rb") as x:
            bot.send_photo(ADMIN,x,text=receipt_text(str(m.chat_id),o))
        try:os.remove(path)
        except:pass
        return True
    except Exception as e:
        print("RECEIPT ERROR:",repr(e),flush=True)
        return False

def media(m):
    return bool(getattr(m,"file",None) or getattr(m,"photo",None) or getattr(m,"image",None))

def handle(m):
    uid=str(m.chat_id)
    text=(getattr(m,"text","") or "").strip()

    if text.startswith("/start"):
        start(uid)
        return

    if text=="❌ خروج":
        text="cancel"

    if text=="cancel":
        orders.pop(uid,None)
        save()
        bot.send_message(uid,
            "❌ ثبت سفارش لغو شد.",
            chat_keypad=main())
        return

    if media(m):
        o=orders.get(uid)
        if not o:
            bot.send_message(uid,"❌ سفارش فعالی ندارید.",chat_keypad=main())
        elif not o.get("target"):
            bot.send_message(uid,"❌ ابتدا آیدی مقصد را ارسال کنید.")
        elif o.get("receipt"):
            bot.send_message(uid,"⚠️ این رسید قبلاً دریافت شده است.")
        elif send_receipt(m,o):
            o["receipt"]=True
            save()
            bot.send_message(uid,
                "✅ رسید دریافت شد و برای ادمین ارسال شد.\n\n⏳ منتظر بررسی باشید.",
                chat_keypad=main())
        else:
            bot.send_message(uid,
                f"❌ ارسال رسید ناموفق بود.\n\n📞 پشتیبانی: {SUPPORT}",
                chat_keypad=main())
        return

    o=orders.get(uid)
    if o and o.get("waiting"):
        if text:set_target(uid,text)
        return

    if text=="🛍 خدمات روبیکا":
        bot.send_message(uid,"🛍 خدمات روبیکا",chat_keypad=services())
        return

    if text=="📣 افزایش کانال":
        bot.send_message(uid,"📣 تعرفه افزایش کانال",chat_keypad=prices(CHANNEL,"📣 "))
        return

    if text=="👥 افزایش گروه":
        bot.send_message(uid,
"""👥 تعرفه افزایش گروه

⚠️ سقف افزایش اعضای گروه روبیکا:
🔟 ۱۰٬۰۰۰ عضو

بیشتر از این مقدار امکان ثبت سفارش ندارد.""",
            chat_keypad=prices(GROUP,"👥 "))
        return

    if text=="⭐ افزایش روبینو":
        bot.send_message(uid,"⭐ تعرفه افزایش روبینو",chat_keypad=prices(FOLLOWERS,"⭐ "))
        return

    if text=="📜 قوانین":
        bot.send_message(uid,
f"""📜 قوانین ثبت سفارش

1️⃣ پس از ثبت سفارش، امکان لغو یا تغییر سفارش نیست.
2️⃣ آیدی صحیح مقصد را ارسال کنید.
3️⃣ مقصد باید عمومی باشد.
4️⃣ زمان انجام سفارش متغیر است.
5️⃣ پس از پرداخت، رسید را ارسال کنید.

📞 پشتیبانی:
{SUPPORT}""",chat_keypad=main())
        return

    if text=="📞 پشتیبانی":
        bot.send_message(uid,f"📞 پشتیبانی\n\n👤 {SUPPORT}",chat_keypad=main())
        return

    if text in ("🔙 خدمات","🛍 خدمات"):
        bot.send_message(uid,"🛍 خدمات روبیکا",chat_keypad=services())
        return

    if text in ("🏠 منوی اصلی","🏠 اصلی"):
        start(uid)
        return

    for prefix,typ in [("📣 ","کانال"),("👥 ","گروه"),("⭐ ","روبینو")]:
        if text.startswith(prefix) and " — " in text:
            s,p=text[len(prefix):].split(" — ",1)
            order(uid,s,p,typ)
            return

    bot.send_message(uid,"از دکمه‌های منو استفاده کنید 👇",chat_keypad=main())

def updates_loop():
    offset=""
    try:
        offset=open(OFF,encoding="utf-8").read().strip()
    except:pass

    while True:
        try:
            p={"limit":10}
            if offset:p["offset_id"]=offset

            r=requests.post(
                f"{bot.BASE_URL}/getUpdates",
                json=p,
                timeout=60)

            if r.status_code!=200:
                print("HTTP:",r.status_code,flush=True)
                time.sleep(10)
                continue

            d=r.json()

            if d.get("status")!="OK":
                print("API ERROR:",d,flush=True)
                time.sleep(10)
                continue

            data=d.get("data") or {}
            arr=data.get("updates") or []
            new=data.get("next_offset_id")

            if new and new!=offset:
                offset=new
                open(OFF,"w",encoding="utf-8").write(offset)

            for x in arr:
                try:
                    handle(updates.Update(x).to_message())
                except Exception as e:
                    print("UPDATE ERROR:",repr(e),flush=True)

            if not arr:time.sleep(1)

        except Exception as e:
            print("POLL ERROR:",repr(e),flush=True)
            time.sleep(10)

def health():
    port=int(os.getenv("PORT","10000"))

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type","text/plain")
            self.end_headers()
            self.wfile.write(b"Rubika bot is running")
        def log_message(self,*a):pass

    threading.Thread(
        target=HTTPServer(("0.0.0.0",port),H).serve_forever,
        daemon=True).start()

if __name__=="__main__":
    health()
    print("BOT STARTED",flush=True)
    print("ADMIN ID:",ADMIN or "NOT SET",flush=True)
    updates_loop()
