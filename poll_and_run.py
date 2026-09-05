import os
import json
import requests
import subprocess

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
OFFSET_FILE = "offset.json"

def load_offset():
    if os.path.exists(OFFSET_FILE):
        with open(OFFSET_FILE) as f:
            return json.load(f).get("offset", 0)
    return 0

def save_offset(offset):
    with open(OFFSET_FILE, "w") as f:
        json.dump({"offset": offset}, f)

def send_message(chat_id, text):
    requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def main():
    offset = load_offset()
    resp = requests.get(
        f"{API_URL}/getUpdates", params={"offset": offset + 1, "timeout": 5}
    ).json()
    updates = resp.get("result", [])

    for update in updates:
        offset = update["update_id"]
        message = update.get("message")
        if not message or "text" not in message:
            continue

        chat_id = str(message["chat"]["id"])
        text = message["text"].strip()

        if text.startswith("/start"):
            send_message(
                chat_id,
                "🤖 Welcome! Koi link ya search term bhejein (jaise: 'psc.wb.gov.in' ya 'WB Medical Result')."
            )
            save_offset(offset)
            continue

        send_message(chat_id, f"🚀 OSINT Radar Start: '{text}'\nIsme thoda time lag sakta hai...")
        
        try:
            # Environment variables setup karna taaki main_spider.py seedha reply kar sake
            env = os.environ.copy()
            env["TELEGRAM_CHAT_ID"] = chat_id
            
            # Import karne ke bajaye naye script ko command line se run karna
            subprocess.run(["python", "main_spider.py", "--query", text], env=env, check=True)
            
        except subprocess.CalledProcessError as e:
            send_message(chat_id, "⚠️ Scraping complete, par shayad error aaya ya data nahi mila.")
        except Exception as e:
            send_message(chat_id, f"❌ System Error: {e}")

        save_offset(offset)

if __name__ == "__main__":
    main()
    offset = load_offset()
    resp = requests.get(
        f"{API_URL}/getUpdates", params={"offset": offset + 1, "timeout": 5}
    ).json()
    updates = resp.get("result", [])

    for update in updates:
        offset = update["update_id"]
        message = update.get("message")
        if not message or "text" not in message:
            continue

        chat_id = message["chat"]["id"]
        text = message["text"].strip()

        if text.startswith("/start"):
            send_message(
                chat_id,
                "🤖 Welcome! Koi bhi govt website ka link bhejein "
                "(jaise: psc.wb.gov.in), main scraping karke CSV bhej dunga.",
            )
            continue

        send_message(chat_id, f"🚀 Scraping shuru ho gaya: {text}\nThoda time lagega...")
        try:
            csv_path, count = scrape_and_build_csv(text)
            if count > 0:
                send_document(
                    chat_id, csv_path, caption=f"✅ {count} ST candidates mile."
                )
            else:
                send_message(
                    chat_id, "⚠️ Scraping complete, par koi ST candidate data nahi mila."
                )
        except Exception as e:
            send_message(chat_id, f"❌ Error: {e}")

    save_offset(offset)


# Sirf itna hi hona chahiye end mein
if __name__ == "__main__":
    main()
    offset = load_offset()
    resp = requests.get(
        f"{API_URL}/getUpdates", params={"offset": offset + 1, "timeout": 5}
    ).json()
    updates = resp.get("result", [])

    for update in updates:
        offset = update["update_id"]
        message = update.get("message")
        if not message or "text" not in message:
            continue

        chat_id = message["chat"]["id"]
        text = message["text"].strip()

        if text.startswith("/start"):
            send_message(
                chat_id,
                "🤖 Welcome! Koi bhi govt website ka link bhejein "
                "(jaise: psc.wb.gov.in), main scraping karke CSV bhej dunga.",
            )
            continue

        send_message(chat_id, f"🚀 Scraping shuru ho gaya: {text}\nThoda time lagega...")
        try:
            csv_path, count = scrape_and_build_csv(text)
            if count > 0:
                send_document(
                    chat_id, csv_path, caption=f"✅ {count} ST candidates mile."
                )
            else:
                send_message(
                    chat_id, "⚠️ Scraping complete, par koi ST candidate data nahi mila."
                )
        except Exception as e:
            send_message(chat_id, f"❌ Error: {e}")

    save_offset(offset)


if __name__ == "__main__":
    main()
    offset = load_offset()
    resp = requests.get(
        f"{API_URL}/getUpdates", params={"offset": offset + 1, "timeout": 5}
    ).json()
    updates = resp.get("result", [])

    for update in updates:
        offset = update["update_id"]
        message = update.get("message")
        if not message or "text" not in message:
            continue

        chat_id = message["chat"]["id"]
        text = message["text"].strip()

        if text.startswith("/start"):
            send_message(
                chat_id,
                "🤖 Welcome! Koi bhi govt website ka link bhejein "
                "(jaise: psc.wb.gov.in), main scraping karke CSV bhej dunga.",
            )
            continue

        send_message(chat_id, f"🚀 Scraping shuru ho gaya: {text}\nThoda time lagega...")
        try:
            csv_path, count = scrape_and_build_csv(text)
            if count > 0:
                send_document(
                    chat_id, csv_path, caption=f"✅ {count} ST candidates mile."
                )
            else:
                send_message(
                    chat_id, "⚠️ Scraping complete, par koi ST candidate data nahi mila."
                )
        except Exception as e:
            send_message(chat_id, f"❌ Error: {e}")

    save_offset(offset)


if __name__ == "__main__":
    main()
