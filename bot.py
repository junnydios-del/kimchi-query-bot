import os
import requests

# ===============================
# 설정
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
DIFF_THRESHOLD = 0.5  # 상위/하위 표시용 (0.5% 이상도 포함 가능)


# ===============================
# 업비트/빗썸 공통 코인 가져오기
# ===============================
def load_common_coins():
    # 업비트 KRW 마켓
    upbit = requests.get("https://api.upbit.com/v1/market/all", timeout=10).json()
    upbit_coins = {m["market"].replace("KRW-", "") for m in upbit if m["market"].startswith("KRW-")}

    # 빗썸 KRW 마켓
    bithumb = requests.get("https://api.bithumb.com/public/ticker/ALL_KRW", timeout=10).json()
    bithumb_coins = set(bithumb["data"].keys()) - {"date"}

    # 공통 코인
    return sorted(list(upbit_coins & bithumb_coins))


# ===============================
# 가격 조회
# ===============================
def get_upbit_price(symbol):
    r = requests.get("https://api.upbit.com/v1/ticker", params={"markets": f"KRW-{symbol}"}, timeout=10).json()
    return float(r[0]["trade_price"])


def get_bithumb_price(symbol):
    r = requests.get(f"https://api.bithumb.com/public/ticker/{symbol}_KRW", timeout=10).json()
    return float(r["data"]["closing_price"])


# ===============================
# 텔레그램 전송
# ===============================
def send_telegram(msg):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                  data={"chat_id": CHAT_ID, "text": msg}, timeout=10)


# ===============================
# 수동 조회 (상위/하위 10개)
# ===============================
def send_query_result():
    coins = load_common_coins()
    diffs = []

    for s in coins:
        try:
            up = get_upbit_price(s)
            bt = get_bithumb_price(s)
            diff = ((up - bt) / bt) * 100
            diffs.append((s, diff))
        except:
            continue

    if not diffs:
        send_telegram("조회 실패")
        return

    # 내림차순 정렬
    diffs.sort(key=lambda x: x[1], reverse=True)
    top10 = diffs[:10]
    bottom10 = diffs[-10:][::-1]

    msg = "📊 업비트 ↔ 빗썸 가격차이\n\n"
    msg += "📈 상위 10\n"
    for s, d in top10:
        msg += f"{s}: {d:.2f}%\n"

    msg += "\n📉 하위 10\n"
    for s, d in bottom10:
        msg += f"{s}: {d:.2f}%\n"

    send_telegram(msg)


# ===============================
# 실행
# ===============================
if __name__ == "__main__":
    send_query_result()
