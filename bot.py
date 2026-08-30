import os
import time
import requests
from rubibot import RubiBot

TOKEN = os.getenv("RUBIKA_BOT_TOKEN", "").strip()

if not TOKEN:
    raise RuntimeError("RUBIKA_BOT_TOKEN is not set")

bot = RubiBot(TOKEN)

print("================================", flush=True)
print("RUBIKA API TEST STARTED", flush=True)
print("TOKEN: SET", flush=True)
print("API: https://botapi.rubika.ir/v3/******", flush=True)
print("================================", flush=True)

while True:
    try:
        r = requests.post(
            f"{bot.BASE_URL}/getUpdates",
            json={"limit": 1},
            timeout=60
        )

        print("HTTP STATUS:", r.status_code, flush=True)
        print("RESPONSE:", r.text[:500], flush=True)

        if r.status_code == 200:
            try:
                data = r.json()

                if data.get("status") == "OK":
                    print("✅ GET UPDATES OK", flush=True)
                else:
                    print("❌ RUBIKA API ERROR", flush=True)

            except Exception as e:
                print("❌ JSON ERROR:", repr(e), flush=True)

        elif r.status_code == 429:
            print("⚠️ TOO MANY REQUESTS", flush=True)

        else:
            print("❌ HTTP ERROR", flush=True)

    except requests.exceptions.Timeout:
        print("❌ REQUEST TIMEOUT", flush=True)

    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION ERROR", flush=True)

    except Exception as e:
        print("❌ ERROR:", repr(e), flush=True)

    print("Waiting 30 seconds...", flush=True)
    time.sleep(30)
