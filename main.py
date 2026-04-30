import os
import json
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN", "")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY", "")
CITY = "Aomori,JP"

def get_weather():
    if not WEATHER_API_KEY:
        return "🌤 날씨 정보 준비중"
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={WEATHER_API_KEY}&units=metric&lang=kr"
        with urllib.request.urlopen(url, timeout=5) as res:
            data = json.loads(res.read())
        desc = data["weather"][0]["description"]
        temp = data["main"]["temp"]
        return f"🌤 아오모리 날씨: {desc}, {temp:.1f}°C"
    except:
        return "날씨 정보를 가져올 수 없어요"

def get_season_tasks():
    month = datetime.now().month
    tasks = {
        1:  "❄️ 1월: 농기구 점검, 종자 준비, 퍼머컬쳐 계획 세우기",
        2:  "❄️ 2월: 씨앗 주문, 토양 개량 계획, 온상 준비",
        3:  "🌱 3월: 온상 파종 시작, 퇴비 만들기, 밭 준비",
        4:  "🌸 4월: 사과 꽃 관리, 밭 경운, 모종 준비",
        5:  "🌿 5월: 모내기 준비, 사과 적과 시작, 퍼머컬쳐 가든 작업",
        6:  "🌾 6월: 모내기, 사과 봉지씌우기, 제초",
        7:  "☀️ 7월: 논 관수 관리, 사과 여름 전정, 해충 관리",
        8:  "☀️ 8월: 논 물 관리, 사과 색 관리, 게스트하우스 여름 성수기 준비",
        9:  "🍎 9월: 벼 출수 관리, 사과 수확 시작 (쓰가루계)",
        10: "🍂 10월: 벼 수확, 사과 본격 수확 (후지 등), 저장 준비",
        11: "🍂 11월: 수확 마무리, 사과 저장관리, 밭 정리",
        12: "❄️ 12월: 사과 전정 시작, 연간 정리, 내년 계획",
    }
    return tasks.get(month, "계절 작업 정보 없음")

def get_daily_reminder():
    day = datetime.now().weekday()
    reminders = {
        0: "📋 월요일: 이번 주 농작업 계획 확인하기",
        1: "💧 화요일: 논/밭 수분 상태 확인",
        2: "🌿 수요일: 퍼머컬쳐 가든 점검",
        3: "📸 목요일: 사진 작업 & 포트폴리오 정리",
        4: "🏠 금요일: 게스트하우스 준비 상태 확인",
        5: "📚 토요일: 농업 공부 & 기록 정리",
        6: "🧘 일요일: 한 주 돌아보기 & 휴식",
    }
    return reminders.get(day, "오늘도 화이팅!")

def make_reply(reply_token, text):
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

def handle_message(reply_token, user_message):
    msg = user_message.strip()

    if any(k in msg for k in ["날씨", "weather"]):
        reply = get_weather()
    elif any(k in msg for k in ["계절", "이번달", "농작업"]):
        reply = get_season_tasks()
    elif any(k in msg for k in ["오늘", "today", "할일", "리마인더"]):
        reply = f"{get_weather()}\n\n{get_daily_reminder()}\n\n{get_season_tasks()}"
    elif any(k in msg for k in ["도움", "help", "기능"]):
        reply = (
            "🌾 농업비서 기능 안내\n\n"
            "• '날씨' → 아오모리 날씨\n"
            "• '오늘' → 오늘 할 일 + 날씨\n"
            "• '계절' → 이번달 농작업\n"
            "• '도움' → 이 메뉴"
        )
    else:
        reply = f"{get_daily_reminder()}\n\n'도움' 이라고 입력하면 기능을 볼 수 있어요! 🌾"

    make_reply(reply_token, reply)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"LINE Bot is running!")

    def do_POST(self):
        # 모든 POST 요청에 200 응답 (서명 검증 생략)
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
                        event["message"]["text"]
                    )
        except Exception as e:
            print(f"Error: {e}")

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🌾 농업비서 봇 시작 (포트: {port})")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
