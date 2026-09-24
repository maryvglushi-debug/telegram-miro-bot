import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = "@safe_space_for_teachers"
MIRO_URL = os.environ.get("MIRO_URL")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def telegram(method, data=None):
    response = requests.post(
        f"{API_URL}/{method}",
        json=data or {},
        timeout=20
    )
    response.raise_for_status()
    return response.json()


def send_message(chat_id, text, buttons=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if buttons:
        data["reply_markup"] = {
            "inline_keyboard": buttons
        }

    return telegram("sendMessage", data)


def is_subscribed(user_id):
    result = telegram(
        "getChatMember",
        {
            "chat_id": CHANNEL_USERNAME,
            "user_id": user_id
        }
    )

    if not result.get("ok"):
        return False

    status = result["result"]["status"]

    return status in ["member", "administrator", "creator"]


def subscription_buttons():
    return [
        [
            {
                "text": "📲 Подписаться на канал",
                "url": "https://t.me/safe_space_for_teachers"
            }
        ],
        [
            {
                "text": "✅ Я подписался — проверить",
                "callback_data": "check_subscription"
            }
        ]
    ]


def give_materials(chat_id):
    send_message(
        chat_id,
        "🎉 Готово! Вы подписаны на канал.\n\n"
        "Вот ссылка на бесплатные материалы:",
        [
            [
                {
                    "text": "📚 Открыть материалы в Miro",
                    "url": MIRO_URL
                }
            ]
        ]
    )


def show_subscription(chat_id):
    send_message(
        chat_id,
        "🎁 Чтобы получить бесплатные материалы, "
        "сначала подпишитесь на наш Telegram-канал.\n\n"
        "После подписки нажмите кнопку «Я подписался — проверить».",
        subscription_buttons()
    )


@app.route("/", methods=["GET"])
def home():
    return "Bot is running"


@app.route("/webhook", methods=["POST"])
def webhook():
    if WEBHOOK_SECRET:
        received_secret = request.headers.get(
            "X-Telegram-Bot-Api-Secret-Token"
        )

        if received_secret != WEBHOOK_SECRET:
            return "Forbidden", 403

    update = request.get_json(silent=True) or {}

    # Обработка обычных сообщений
    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        if text.startswith("/start"):
            send_message(
                chat_id,
                "Привет! 👋\n\n"
                "Здесь можно получить бесплатные материалы.",
                [
                    [
                        {
                            "text": "🎁 Получить материалы",
                            "callback_data": "get_materials"
                        }
                    ]
                ]
            )

    # Обработка нажатий на кнопки
    if "callback_query" in update:
        callback = update["callback_query"]
        callback_id = callback["id"]
        data = callback.get("data")
        chat_id = callback["message"]["chat"]["id"]
        user_id = callback["from"]["id"]

        telegram(
            "answerCallbackQuery",
            {
                "callback_query_id": callback_id
            }
        )

        if data in ["get_materials", "check_subscription"]:
            if is_subscribed(user_id):
                give_materials(chat_id)
            else:
                show_subscription(chat_id)

    return jsonify({"ok": True})


def set_webhook():
    external_url = os.environ.get("RENDER_EXTERNAL_URL")

    if not external_url:
        return

    webhook_url = external_url.rstrip("/") + "/webhook"

    data = {
        "url": webhook_url
    }

    if WEBHOOK_SECRET:
        data["secret_token"] = WEBHOOK_SECRET

    telegram("setWebhook", data)


if __name__ == "__main__":
    set_webhook()

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
