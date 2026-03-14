import requests
import json
import time
import threading
import os
from telegram.ext import Updater, CommandHandler

BOT_TOKEN = os.getenv("TELEGRAM_BOT_CODE")

ALERT_FILE = "alerts.json"

lock = threading.Lock()


def format_symbol(symbol):
    symbol = symbol.upper()
    if not symbol.endswith("USD"):
        symbol = symbol + "USD"
    return symbol


def load_alerts():
    try:
        if not os.path.exists(ALERT_FILE):
            with open(ALERT_FILE, "w") as f:
                json.dump({}, f)
            return {}

        with open(ALERT_FILE) as f:
            return json.load(f)

    except:
        return {}


def save_alerts(alerts):
    with lock:
        with open(ALERT_FILE, "w") as f:
            json.dump(alerts, f, indent=2)


alerts = load_alerts()


def get_price(symbol):
    try:
        url = f"https://api.india.delta.exchange/v2/tickers/{symbol}"
        response = requests.get(url)
        data = response.json()
        price = float(data["result"]["mark_price"])
        return price
    except Exception as e:
        print("Price fetch error:", e)
        return None


def start(update, context):
    update.message.reply_text(
        "Commands:\n"
        "/price BTC\n"
        "/add BTC 70192\n"
        "/remove BTC 70192\n"
        "/list"
    )


def price(update, context):

    if len(context.args) == 0:
        update.message.reply_text("Usage: /price BTC")
        return

    symbol = format_symbol(context.args[0])

    price = get_price(symbol)

    if price:
        update.message.reply_text(f"📈 {symbol} Price: {price}")
    else:
        update.message.reply_text("Invalid coin symbol")


def alert(update, context):

    if len(context.args) < 2:
        update.message.reply_text("Usage: /add BTC 70192")
        return

    symbol = format_symbol(context.args[0])
    target = float(context.args[1])
    chat = str(update.message.chat_id)

    price = get_price(symbol)

    with lock:

        alerts = load_alerts()

        if chat not in alerts:
            alerts[chat] = []

        alerts[chat].append({
            "symbol": symbol,
            "price": target
        })

        save_alerts(alerts)

    update.message.reply_text(
        f"✅ Alert Added\n"
        f"Coin: {symbol}\n"
        f"Alert price: {target}\n"
        f"Current price: {price}"
    )


def remove(update, context):

    if len(context.args) < 2:
        update.message.reply_text("Usage: /remove BTC 70192")
        return

    symbol = format_symbol(context.args[0])
    target = float(context.args[1])
    chat = str(update.message.chat_id)

    with lock:

        alerts = load_alerts()

        if chat in alerts:

            for a in alerts[chat]:

                if a["symbol"] == symbol and a["price"] == target:

                    alerts[chat].remove(a)

                    save_alerts(alerts)

                    update.message.reply_text(
                        f"❌ Removed alert\n{symbol} {target}"
                    )

                    return

    update.message.reply_text("Alert not found")


def list_alerts(update, context):

    chat = str(update.message.chat_id)

    alerts = load_alerts()

    if chat not in alerts or len(alerts[chat]) == 0:
        update.message.reply_text("No alerts set")
        return

    msg = "📋 Your alerts:\n\n"

    for a in alerts[chat]:
        msg += f"{a['symbol']} → {a['price']}\n"

    update.message.reply_text(msg)


def monitor():

    while True:

        try:

            alerts = load_alerts()

            for chat in alerts:

                for a in alerts[chat][:]:

                    symbol = a["symbol"]
                    target = a["price"]

                    price = get_price(symbol)

                    if price and price >= target:

                        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

                        requests.get(
                            url,
                            params={
                                "chat_id": chat,
                                "text": f"🚨 ALERT HIT\nCoin: {symbol}\nCurrent price: {price}\nAlert price: {target}"
                            }
                        )

                        with lock:

                            alerts = load_alerts()

                            alerts[chat].remove(a)

                            save_alerts(alerts)

        except Exception as e:
            print("Monitor error:", e)

        time.sleep(20)


def main():

    updater = Updater(BOT_TOKEN, use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("price", price))
    dp.add_handler(CommandHandler("add", alert))
    dp.add_handler(CommandHandler("remove", remove))
    dp.add_handler(CommandHandler("list", list_alerts))

    thread = threading.Thread(target=monitor)
    thread.daemon = True
    thread.start()

    updater.start_polling()
    updater.idle()


main()
