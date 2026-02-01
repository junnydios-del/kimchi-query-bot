import os
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

COINS_FILE = "manual_coins.json"
MAX_WORKERS = 10


# ===============================
# 가격 조회
# ===============================
def get_upbit(symbol):
    r = requests.get(
        "https://api.upbit.com/v1/ticker",
        params={"markets": f"KRW-{symbol}"},
        timeout=5
    ).json()
    return float(r[0]["trade_price"])


def get_bithumb(symbol):
    r = requests.get(
        f"https://api.bithumb.com/public/ticker/{symbol}_KRW",
        timeout=5
    ).json()
    return float(r["data"]["closing_price"])


def compare_coin(symbol):
    try:
        up = get_upbit(symbol)
        bt = get_bithumb(symbol)
        diff = ((up - bt) / bt) * 100
        return symbol, diff, up, bt
    except:
        return None


# ===============================
# 텔레그램
# ===============================
def send_telegram(msg):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg},
        timeout=10
    )


# ===============================
# 수동 조회
# ===============================
def manual_check():
    with open(COINS_FILE, "r") as f:
        coins = json.load(f)["coins"]

    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exe:
        futures = [exe.submit(compare_coin, c) for c in coins]

        for f in as_completed(futures):
            r = f.result()
            if r:
                results.append(r)

    if not results:
        send_telegram("📊 수동 조회 결과 없음")
        return

    # 가격차 기준 정렬
    results.sort(key=lambda x: x[1], reverse=True)

    top = results[:7]
    bottom = results[-7:]

    msg = "📊 업비트 ↔ 빗썸 가격차이 (수동)\n\n"

    msg += "📈 업비트가 더 비싼 TOP 7\n"
    for c, d, up, bt in top:
        msg += f"{c} | {d:.2f}% | 업 {up:,} / 빗 {bt:,}\n"

    msg += "\n📉 빗썸이 더 비싼 BOTTOM 7\n"
    for c, d, up, bt in bottom:
        msg += f"{c} | {d:.2f}% | 업 {up:,} / 빗 {bt:,}\n"

    send_telegram(msg)


# ===============================
# 실행
# ===============================
if __name__ == "__main__":
    manual_check()
