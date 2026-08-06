import os
import json
import re
import urllib.parse
import feedparser
import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

QUERY = "(人工知能 OR AI OR ChatGPT OR Claude OR LLM) when:1d"
encoded_query = urllib.parse.quote(QUERY)
RSS_URL = f"https://news.google.com/rss/search?q={encoded_query}&hl=ja&gl=JP&ceid=JP:ja"

def fetch_ai_news():
    """RSSから最新ニュースを取得"""
    feed = feedparser.parse(RSS_URL)
    return feed.entries[:3]

def scrape_article_text(url):
    """【機能①】記事の本文テキストを抽出"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            # 不要なタグを除去
            for element in soup(["script", "style", "nav", "header", "footer"]):
                element.decompose()
            text = soup.get_text(separator=" ", strip=True)
            return text[:2000] # トークン節約のため先頭2000文字
    except Exception as e:
        print(f"Scraping warning: {e}")
    return ""

def generate_deep_briefing(title, link):
    """【機能①・②・③】Gemini APIで全文解析・JSON出力・Search Groundingを実行"""
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # 本文スクレイピング
        article_text = scrape_article_text(link)
        
        prompt = f"""
以下のニュース記事について、毎朝のチーム共有会で発表・議論するための詳細なブリーフィングを作成してください。

タイトル: {title}
URL: {link}
記事本文抜粋:
{article_text if article_text else "（本文取得不可。タイトルと背景情報から生成してください）"}

【指示】
1. 必要に応じてWeb検索を用いて業界の文脈や過去の経緯を補足してください。
2. 以下のJSONフォーマットのみで出力してください。Markdown装飾(```json など)は不要です。

【出力JSONフォーマット】
{{
    "summary": "概要（3〜4行で要点と背景を深掘り要約）",
    "talking_point": "朝会で話せるポイント（業務・社会への影響や議論のきっかけ）",
    "importance": "重要度（1〜5の数値）",
    "category": "カテゴリタグ（例: #LLM, #セキュリティ, #インフラ から1〜2個）",
    "target": "推奨対象（例: エンジニア向け, 企画・営業向け, 全員向け）"
}}
"""

        # 【機能③】Google Search Grounding（Web検索連携）を有効化
        config = types.GenerateContentConfig(
            tools=[{"google_search": {}}],
            response_mime_type="application/json",  # 【機能②】JSON Mode指定
        )

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=config,
        )
        
        # JSONレスポンスのクレンジング
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
            
        return json.loads(text.strip())

    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None

def send_to_discord(entries):
    if not entries:
        print("ニュースが見つかりませんでした。")
        return

    embeds = []
    for entry in entries:
        title = entry.title
        link = entry.link
        
        data = generate_deep_briefing(title, link)

        if data:
            # 重要度を★マークに変換
            try:
                score = int(data.get("importance", 3))
            except ValueError:
                score = 3
            stars = "★" * score + "☆" * (5 - score)

            description = f"""**重要度**: {stars}
**カテゴリ**: {data.get('category', '#AI')} | **対象**: {data.get('target', '全員向け')}

■ **概要**
{data.get('summary', '')}

■ **朝会トークポイント**
{data.get('talking_point', '')}"""

            embed = {
                "title": title,
                "url": link,
                "description": description,
                "color": 3447003
            }
        else:
            # エラー時のフォールバック表示
            embed = {
                "title": title,
                "url": link,
                "description": "※要約の生成に失敗しました。",
                "color": 15158332
            }
        
        embeds.append(embed)

    payload = {
        "content": "☀️ **【高精度版】今朝のAIニュース共有＆トークポイント（Gemini Deep Analysis）**",
        "embeds": embeds
    }

    requests.post(WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    if not WEBHOOK_URL or not GEMINI_API_KEY:
        print("エラー: DISCORD_WEBHOOK_URL または GEMINI_API_KEY が設定されていません。")
    else:
        news = fetch_ai_news()
        send_to_discord(news)
