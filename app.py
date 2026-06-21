import os
from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
    FileMessage,
    ImageMessage,
)
import os
import requests
from datetime import datetime

app = Flask(__name__)

# LINE 設定
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# Discord Webhook 設定
DISCORD_WEBHOOKS = {
    "圖片儲存": os.getenv("DISCORD_IMAGE"),
    "連結總匯": os.getenv("DISCORD_LINK"),
    "程式碼": os.getenv("DISCORD_CODE"),
    "影音": os.getenv("DISCORD_MEDIA"),
    "學習筆記": os.getenv("DISCORD_NOTE"),
    "其他": os.getenv("DISCORD_OTHER"),
}


def get_folder(file_name):
    name = file_name.lower()

    if name.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")):
        return "圖片儲存"

    elif name.endswith((".mp4", ".mov", ".avi", ".mkv", ".wmv", ".mp3", ".wav")):
        return "影音"

    elif name.endswith((
        ".py", ".js", ".java", ".cpp", ".c", ".html",
        ".css", ".json", ".php", ".sql"
    )):
        return "程式碼"

    elif name.endswith((
        ".pdf", ".doc", ".docx", ".ppt", ".pptx",
        ".xls", ".xlsx", ".csv"
    )):
        return "學習筆記"

    elif name.endswith((".txt", ".md")):
        return "連結總匯"

    else:
        return "其他"


def upload_to_discord(file_path, file_name, folder):
    webhook_url = DISCORD_WEBHOOKS.get(folder)

    if not webhook_url or "你的" in webhook_url:
        print("Discord Webhook 沒設定：", folder)
        return False

    with open(file_path, "rb") as f:
        files = {
            "file": (file_name, f)
        }

        data = {
            "content": f"LINE 檔案已分類\n分類：{folder}\n檔名：{file_name}"
        }

        response = requests.post(webhook_url, data=data, files=files)

    print("Discord 回應：", response.status_code, response.text)

    return response.status_code in [200, 204]


def upload_text_to_discord(text, folder):
    webhook_url = DISCORD_WEBHOOKS.get(folder)

    if not webhook_url or "你的" in webhook_url:
        return False

    data = {
        "content": text
    }

    response = requests.post(webhook_url, json=data)

    return response.status_code in [200, 204]


@app.route("/")
def home():
    return "LINE Bot Running"


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    handler.handle(body, signature)

    return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_text = event.message.text

    if user_text.startswith("http://") or user_text.startswith("https://"):
        discord_ok = upload_text_to_discord(
            f"LINE 連結已分類\n分類：連結總匯\n連結：{user_text}",
            "連結總匯"
        )

        if discord_ok:
            reply = "已上傳到 Discord：連結總匯"
        else:
            reply = "收到連結，但 Discord 上傳失敗"

    else:
        reply = f"收到：{user_text}"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )


@handler.add(MessageEvent, message=FileMessage)
def handle_file(event):
    file_name = event.message.file_name
    message_id = event.message.id

    folder = get_folder(file_name)
    os.makedirs(folder, exist_ok=True)

    save_path = os.path.join(folder, file_name)

    content = line_bot_api.get_message_content(message_id)

    with open(save_path, "wb") as f:
        for chunk in content.iter_content():
            f.write(chunk)

    discord_ok = upload_to_discord(save_path, file_name, folder)

    if discord_ok:
        reply = f"已儲存並上傳到 Discord\n檔名：{file_name}\n分類：{folder}"
    else:
        reply = f"已儲存到電腦\n檔名：{file_name}\n分類：{folder}\nDiscord 上傳失敗"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )


@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    message_id = event.message.id

    folder = "圖片儲存"
    os.makedirs(folder, exist_ok=True)

    file_name = datetime.now().strftime("image_%Y%m%d_%H%M%S.jpg")
    save_path = os.path.join(folder, file_name)

    content = line_bot_api.get_message_content(message_id)

    with open(save_path, "wb") as f:
        for chunk in content.iter_content():
            f.write(chunk)

    discord_ok = upload_to_discord(save_path, file_name, folder)

    if discord_ok:
        reply = f"已儲存圖片並上傳到 Discord\n分類：{folder}"
    else:
        reply = f"已儲存圖片到電腦\n分類：{folder}\nDiscord 上傳失敗"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )


if __name__ == "__main__":
    app.run(port=5000)