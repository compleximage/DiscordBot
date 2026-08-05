import os
import urllib.parse
import feedparser
import requests

# Discord Webhook URL（環境変数から取得）
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# 検索キーワード（AI関連情報）
QUERY = "人工知能 OR AI OR ChatGPT OR Claude"
encoded_query = urllib.parse.quote(QUERY)

# GoogleニュースのRSS URL
RSS_URL = f"https://news.google.com/rss/search?q={encoded_query}&hl=ja&gl=JP&ceid=JP:ja"

def fetch_ai_news():
    feed = feedparser.parse(RSS_URL)
    # 最新3件を取得
    entries = feed.entries[:3]
    return entries

def send_to_discord(entries):
    if not entries:
        print("ニュースが見つかりませんでした。")
        return

    embeds = []
    for entry in entries:
        # 記事情報を埋め込みカード形式に整形
        embed = {
            "title": entry.title,
            "url": entry.link,
            "description": entry.published,
            "color": 3447003  # 青色
        }
        embeds.append(embed)

    payload = {
        "content": "☀️ **今朝のAI最新ニュースをお届けします！**",
        "embeds": embeds
    }

    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code in [200, 204]:
        print("Discordへの送信に成功しました。")
    else:
        print(f"送信失敗: {response.status_code}, {response.text}")

if __name__ == "__main__":
    if not WEBHOOK_URL:
        print("エラー: DISCORD_WEBHOOK_URL が設定されていません。")
    else:
        news = fetch_ai_news()
        send_to_discord(news)
