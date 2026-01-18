import os
import json
import datetime
import requests

# ===============================
# 설정
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
DIFF_THRESHOLD = 0.5  # 수동 조회 기준
COMMON_FILE = "tradable_coins.json"
LAST_FILE = "last_prices.json"

# ===============================
# 공통 코인 + 입출금 가능 코인 하루 1회 갱신
# ===============================
def update_tradable_coins():
    # 업비트
    upbit = requests.get("https://api.upbit.com/v1/market/all", timeout=10).json()
    upbit_coins = {m["market"].replace("KRW-", "") for m in upbit if m["market"].startswith("KRW-")}

    # 빗썸
    bithumb = requests.get("https://api.bithumb.com/public/ticker/ALL_KRW", timeout=10).json()
    bithumb_coins = set(bithumb["data"].keys()) - {"date"}

    common = upbit_coins & bithumb_coins

    # 업비트 지갑 상태
    wallet = requests.get("https://api.upbit.com/v1/status/wallet", timeout=10).json()
    wallet_data = wallet.get("data", [])
    wallet_map = {c.get("currency"): (c.get("deposit_state")=="ACTIVE" and c.get("withdraw_state")=="ACTIVE") for c in wallet_data}

    tradable = sorted([c for c in common if wallet_map.get(c)])

    with open(COMMON_FILE, "w") as f:
        json.dump({"date": datetime.date.today().isoformat(), "coins": tradable}, f)

    print(f"[INFO] 입출금 가능 공통 코인 {len(tradable)}개 저장")

def load_tradable_coins():
    today = datetime.date.today().isoformat()
    if not os.path.exists(COMMON_FILE):
        update_tradable_coins()
    with open(COMMON_FILE, "r") as f:
        data = json.load(f)
    if data["date"] != today:
        update_tradable_coins()
        with open(COMMON_FILE, "r") as f:
            data = json.load(f)
    return data["coins"]

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
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg}, timeout=10)

# ===============================
# 수동 조회
# ===============================
def get_all_prices():
    coins = load_tradable_coins()
    prices = {}
    for s in coins:
        try:
            up = get_upbit_price(s)
            bt = get_bithumb_price(s)
            prices[s] = (up, bt)
        except:
            continue
    return prices

def save_last_prices(prices):
    with open(LAST_FILE, "w") as f:
        json.dump(prices, f)

def load_last_prices():
    if not os.path.exists(LAST_FILE):
        return {}
    with open(LAST_FILE, "r") as f:
        return json.load(f)

def send_query_result():
    current_prices = get_all_prices()
    last_prices = load_last_prices()

    diffs = []
    for s, (up, bt) in current_prices.items():
        # 마지막 가격과 비교
        if s in last_prices:
            last_up, last_bt = last_prices[s]
            # 마지막 가격 대비 현재 차이(%)
            diff = ((up - bt) / bt) * 100
            diffs.append((s, diff))
        else:
            # 처음 조회면 그냥 현재 가격 차이 계산
            diff = ((up - bt) / bt) * 100
            diffs.append((s, diff))

    if not diffs:
        send_telegram("조회 실패")
        return

    # 상위/하위 10개
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

    # 마지막 조회 저장
    save_last_prices(current_prices)

# ===============================
# 실행
# ===============================
if __name__ == "__main__":
    send_query_result()  # 깃허브 액션에서 누르면 바로 조회
