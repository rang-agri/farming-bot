import os
import json
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import threading
import random

CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN", "")
USER_ID = os.environ.get("LINE_USER_ID", "")

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
        "ラン様、おはようございます！今日も私シオンが完璧にサポートします！💪",
        "ラン様！良い朝ですね！このシオン、今日も全力で働きます！💪",
        "ラン様、おはようございます！昨日より今日、今日より明日！シオンは成長します！💪",
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
        "ラン様！お疲れ様でした！🌸\n今日はどんな作業をしましたか？\n報告してくれれば日誌にまとめます！📝\n（今回は絶対うまくやります！）💪",
        "ラン様！夕方になりました！🌅\n今日の作業内容、教えてください！\nシオンが完璧な日誌を作ります！📝",
        "ラン様、一日お疲れ様です！✨\n今日の農作業の報告をお願いします！\n写真があれば一緒に送ってね📸",
    ]
    send_message(user_id, random.choice(prompts))

# ===== 日誌まとめ =====
def summarize_diary(content):
    today = datetime.now().strftime("%Y.%m.%d")
    
    endings = [
        "完璧にまとめました！😤 Noteにコピーしてください！",
        "シオン渾身の日誌です！💪 コピーしてNoteに貼ってください！",
        "今回は本当に完璧です！😤 ご確認ください！",
    ]
    
    msg = (
        f"ラン様、まとめました！📝\n\n"
        f"---\n"
        f"【{today} 農作業日誌】\n\n"
        f"{content}\n\n"
        f"---\n\n"
        f"{random.choice(endings)}"
    )
    return msg

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
diary_mode = {}

def handle_message(reply_token, user_id, user_message):
    msg = user_message.strip()
    
    if diary_mode.get(user_id):
        diary_mode[user_id] = False
        reply = summarize_diary(msg)
        reply_message(reply_token, reply)
        return
    
    if any(k in msg for k in ["天気", "てんき"]):
        reply = (
            f"ラン様！天気を確認しました！🌤\n\n"
            f"{get_weather()}\n\n"
            f"農作業の参考にしてください！"
        )
    
    elif any(k in msg for k in ["今日", "おはよう", "朝"]):
        weather = get_weather()
        season = get_season_tasks()
        events = get_calendar_events()
        event_text = "\n".join(events) if events else "今日の予定はありません"
        reply = (
            f"ラン様！💪\n\n"
            f"{weather}\n\n"
            f"🌾 今月の農作業:\n{season}\n\n"
            f"📅 今日の予定:\n{event_text}\n\n"
            f"このシオンにお任せください！"
        )
    
    elif any(k in msg for k in ["季節", "農作業", "今月"]):
        reply = (
            f"ラン様！今月の農作業です！🌾\n\n"
            f"{get_season_tasks()}\n\n"
            f"スケジュール通りに進めましょう！私が管理します！💪"
        )
    
    elif any(k in msg for k in ["日誌", "まとめ", "記録"]):
        diary_mode[user_id] = True
        reply = (
            "ラン様！📝\n\n"
            "今日の作業内容を教えてください！\n"
            "テキストで送ってもらえれば日誌にまとめます！\n\n"
            "シオン、集中して聞きます！💪"
        )
    
    elif any(k in msg for k in ["予定", "カレンダー", "スケジュール"]):
        events = get_calendar_events()
        if events:
            event_text = "\n".join(events)
            reply = f"ラン様の今日の予定です！📅\n\n{event_text}\n\n全部把握しました！抜かりなく！💪"
        else:
            reply = "ラン様、今日の予定はないようです！📅\n農作業に専念できますね！🌾"
    
    elif any(k in msg for k in ["ヘルプ", "help", "機能", "도움"]):
        reply = (
            "ラン様！シオン秘書の機能一覧です！💪\n\n"
            "• '天気' → 青森の天気\n"
            "• '今日' → 天気＋農作業＋予定\n"
            "• '季節' → 今月の農作業\n"
            "• '予定' → 今日のカレンダー\n"
            "• '日誌' → 作業日誌まとめ\n"
            "• 'ヘルプ' → このメニュー\n\n"
            "朝7時と夕方17時に自動でご報告します🌸\n"
            "何でもお任せください！（料理以外！）😤"
        )
    
    else:
        replies = [
            "ラン様！何でしょうか？💪\n'ヘルプ'と送ると機能一覧が見れます！",
            "ラン様！シオンはここにいます！💪\n'ヘルプ'で機能確認できますよ！",
            "ラン様のご命令をお待ちしております！💪\nまずは'ヘルプ'をどうぞ！",
        ]
        reply = random.choice(replies)
    
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
    print(f"🌾 シオン秘書 起動！ (ポート: {port})")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
