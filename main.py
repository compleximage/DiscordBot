import os
import urllib.parse
import feedparser
import requests
from google import genai

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

QUERY = "(人工知能 OR AI OR ChatGPT OR Claude OR LLM) when:1d"
encoded_query = urllib.parse.quote(QUERY)
RSS_URL = f"https://news.google.com/rss/search?q={encoded_query}&hl=ja&gl=JP&ceid=JP:ja"

def fetch_ai_news():
    feed = feedparser.parse(RSS_URL)
    return feed.entries[:3]

def generate_summary_and_topic(title, link):
    """Gemini APIを使ってニュースの要約と朝のトークポイントを生成"""
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""
以下のAIニュースについて、毎朝のチーム共有会で発表・議論するためのブリーフィングを作成してください。

タイトル: {title}
URL: {link}

【出力フォーマット】
■ 概要（2〜3行で要約）
■ 朝会で話せるポイント（このニュースが業務や社会にどう影響するか、議論のきっかけになる一言コメント）

簡潔でわかりやすく、親しみやすい日本語で作成してください。
"""
        # 正しい最新モデル名: gemini-2.0-flash
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return f"要約の生成に失敗しました。（{e}）"

def send_to_discord(entries):
    if not entries:
        print("ニュースが見つかりませんでした。")
        return

    embeds = []
    for entry in entries:
        title = entry.title
        link = entry.link
        
        ai_analysis = generate_summary_and_topic(title, link)

        embed = {
            "title": title,
            "url": link,
            "description": ai_analysis,
            "color": 3447003
        }
        embeds.append(embed)

    payload = {
        "content": "☀️ **今朝のAIニュース共有＆トークポイント（Gemini要約付き）**",
        "embeds": embeds
    }

    requests.post(WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    if not WEBHOOK_URL or not GEMINI_API_KEY:
        print("エラー: DISCORD_WEBHOOK_URL または GEMINI_API_KEY が設定されていません。")
    else:
        news = fetch_ai_news()
        send_to_discord(news)
