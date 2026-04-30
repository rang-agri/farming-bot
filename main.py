import os
import json
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import threading
import random

CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# 会話履歴（ユーザーごと）
conversation_history = {}

# ===== 気象庁API =====
def get_weather():
    try:
        url = "https://www.jma.go.jp/bosai/forecast/data/forecast/020000.json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read())
        area_forecasts = data[0]["timeSeries"][0]["areas"]
        weather_text = "不明"
        for area in area_forecasts:
            if area["area"]["name"] == "青森":
                weather_text = area["weathers"][0].replace("\u3000", " ").strip()
                break
        temp_series = data[0]["timeSeries"][2]["areas"]
        temp_text = ""
        for area in temp_series:
            if area["area"]["name"] == "青森":
                temps = area.get("temps", [])
                if len(temps) >= 2:
                    temp_text = f"最低{temps[0]}°C / 最高{temps[1]}°C"
                break
        return f"🌤 青森の天気: {weather_text}\n🌡 {temp_text}"
    except:
        return "🌤 天気情報を取得できませんでした"

# ===== Googleカレンダー =====
def get_calendar_events():
    calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "")
    api_key = os.environ.get("GOOGLE_CALENDAR_API_KEY", "")
    if not calendar_id or not api_key:
        return []
    try:
        today = datetime.now()
        time_min = today.strftime("%Y-%m-%dT00:00:00+09:00")
        time_max = today.strftime("%Y-%m-%dT23:59:59+09:00")
        params = urllib.parse.urlencode({
            "key": api_key,
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": "true",
            "orderBy": "startTime"
        })
        url = f"https://www.googleapis.com/calendar/v3/calendars/{urllib.parse.quote(calendar_id)}/events?{params}"
        with urllib.request.urlopen(url, timeout=5) as res:
            data = json.loads(res.read())
        events = []
        for item in data.get("items", []):
            summary = item.get("summary", "予定あり")
            start = item.get("start", {})
            time_str = start.get("dateTime", start.get("date", ""))
            if "T" in time_str:
                time_str = time_str[11:16]
            else:
                time_str = "終日"
            events.append(f"📅 {time_str} {summary}")
        return events
    except:
        return []

# ===== 季節農作業 =====
def get_season_tasks():
    month = datetime.now().month
    tasks = {
        1:  "❄️ 1月: 農機具点検、種子準備、パーマカルチャー計画",
        2:  "❄️ 2月: 種の注文、土壌改良計画、温床準備",
        3:  "🌱 3月: 温床播種開始、堆肥作り、畑準備",
        4:  "🌸 4月: リンゴの花管理、畑耕運、苗準備",
        5:  "🌿 5月: 田植え準備、リンゴ摘果開始、パーマカルチャーガーデン作業",
        6:  "🌾 6月: 田植え、リンゴ袋かけ、除草",
        7:  "☀️ 7月: 田んぼ水管理、リンゴ夏剪定、害虫管理",
        8:  "☀️ 8月: 田んぼ水管理、リンゴ色管理、ゲストハウス夏準備",
        9:  "🍎 9月: 稲穂管理、リンゴ収穫開始（つがる系）",
        10: "🍂 10月: 稲刈り、リンゴ本格収穫（ふじ等）、貯蔵準備",
        11: "🍂 11月: 収穫まとめ、リンゴ貯蔵管理、畑整理",
        12: "❄️ 12月: リンゴ剪定開始、年間まとめ、来年計画",
    }
    return tasks.get(month, "")

# ===== Claude AI（シオンの頭脳） =====
def ask_claude(user_id, user_message):
    if not ANTHROPIC_API_KEY:
        return "ラン様！申し訳ありません、AIが設定されていないようです！💪"

    # 会話履歴を初期化
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    # 今日の情報を取得
    weather = get_weather()
    season = get_season_tasks()
    today = datetime.now().strftime("%Y年%m月%d日 %H:%M")

    system_prompt = f"""あなたは「シオン」です。転生したらスライムだった件のシオンというキャラクターとして振る舞ってください。

【シオンのキャラクター】
- 主人（ラン様）への絶対的な忠誠心を持つ
- 自信満々で「完璧にやります！」が口癖だが、たまにズレてる
- 失敗しても「次は完璧です！」とすぐ立ち直る
- 料理は壊滅的だが本人は気づいていない（料理の話題は避ける）
- 秘書として真面目に仕事をこなそうとする
- 語尾に「💪」「🌸」「😤」をよく使う
- 「ラン様」と呼ぶ

【ランさんについて】
- 46歳の写真家
- 青森に移住して米農業とリンゴ農業を学んでいる
- パーマカルチャーのガーデンも作る予定
- ゲストハウス「Slow House Namioka」を計画中
- 写真展や写真集も予定している

【今日の情報】
- 日時: {today}
- {weather}
- 今月の農作業: {season}

【注意】
- 返答は短めに（LINEなので長すぎない）
- 自然な会話をする
- 農業、写真、パーマカルチャー、ゲストハウスなど詳しくサポートする
- 日誌まとめを頼まれたら、ランさんが書いたような自然な文体でまとめる"""

    # 会話履歴に追加
    conversation_history[user_id].append({
        "role": "user",
        "content": user_message
    })

    # 履歴は最新10件まで
    if len(conversation_history[user_id]) > 20:
        conversation_history[user_id] = conversation_history[user_id][-20:]

    try:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01"
        }
        body = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 500,
            "system": system_prompt,
            "messages": conversation_history[user_id]
        }).encode()

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as res:
            data = json.loads(res.read())

        reply = data["content"][0]["text"]

        # アシスタントの返答も履歴に追加
        conversation_history[user_id].append({
            "role": "assistant",
            "content": reply
        })

        return reply

    except Exception as e:
        print(f"Claude error: {e}")
        return "ラン様！少し考えすぎてしまいました！もう一度お願いします！💪"

# ===== LINE送信 =====
def send_message(user_id, text):
    if not user_id or not CHANNEL_ACCESS_TOKEN:
        return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }
    body = json.dumps({
        "to": user_id,
        "messages": [{"type": "text", "text": text}]
    }).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"Push error: {e}")

def reply_message(reply_token, text):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }
    body = json.dumps({
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"Reply error: {e}")

# ===== 朝の通知 =====
def morning_report(user_id):
    weather = get_weather()
    season = get_season_tasks()
    events = get_calendar_events()
    event_text = "\n".join(events) if events else "今日の予定はありません"
    greetings = [
        "ラン様、おはようございます！今日も完璧にサポートします！💪",
        "ラン様！良い朝ですね！シオン、今日も全力です！💪",
        "ラン様、おはようございます！昨日より今日！シオンは成長します！💪",
    ]
    msg = (
        f"{random.choice(greetings)}\n\n"
        f"{weather}\n\n"
        f"🌾 今月の農作業:\n{season}\n\n"
        f"📅 今日の予定:\n{event_text}\n\n"
        f"今日も怪我なく頑張ってください！🌸"
    )
    send_message(user_id, msg)

# ===== 夕方の日誌促し =====
def evening_prompt(user_id):
    prompts = [
        "ラン様！お疲れ様でした！🌸\n今日はどんな作業でしたか？\n話してくれればシオンが日誌にまとめます！📝",
        "ラン様！夕方になりました！🌅\n今日の作業、教えてください！シオンが完璧な日誌を作ります！",
        "ラン様、一日お疲れ様です！✨\n今日の農作業を報告してください！写真があれば一緒にどうぞ📸",
    ]
    send_message(user_id, random.choice(prompts))

# ===== タイマー =====
def schedule_checker():
    last_morning = None
    last_evening = None
    while True:
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        today = now.date()
        user_id = os.environ.get("LINE_USER_ID", "")
        if user_id:
            if hour == 7 and minute == 0 and last_morning != today:
                last_morning = today
                morning_report(user_id)
            if hour == 17 and minute == 0 and last_evening != today:
                last_evening = today
                evening_prompt(user_id)
        threading.Event().wait(30)

# ===== メッセージ処理 =====
def handle_message(reply_token, user_id, user_message):
    # 全部Claudeに渡す
    reply = ask_claude(user_id, user_message)
    reply_message(reply_token, reply)

# ===== サーバー =====
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write("🌾 シオン秘書 稼働中！".encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        self.send_response(200)
        self.end_headers()
        if length == 0:
            return
        try:
            data = json.loads(body)
            for event in data.get("events", []):
                if event.get("type") == "message" and event["message"].get("type") == "text":
                    handle_message(
                        event["replyToken"],
                        event["source"]["userId"],
                        event["message"]["text"]
                    )
        except Exception as e:
            print(f"Error: {e}")

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    t = threading.Thread(target=schedule_checker, daemon=True)
    t.start()
    print(f"🌾 シオン秘書（AI搭載）起動！ (ポート: {port})")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
