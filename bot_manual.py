import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# ===============================
# 텔레그램 설정 (기존과 동일)
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("BOT_TOKEN 또는 CHAT_ID 환경변수가 없습니다.")

# ===============================
# 수동 조회할 코인 목록 (30개)
# ===============================
COINS = [
    # 메이저 / 스테이블
    "USDT", "USDC",

    # 상단에 언급된 코인들
    "FLUID", "ZRO", "VANA", "AXS", "ENSO", "IP",
    "BARD", "ORCA", "TON",

    # 추천/중형
    "AQT", "BERA", "AKT", "KAITO", "TRX", "CBK",
    "JTO", "LA", "MET", "AVNT", "RED",

    # 중소형
    "SOMI", "OPEN", "BREV", "CTC", "ME",
    "SUPER", "TAIKO", "ZKP", "SAFE", "XPL",
    "ZBT",

    # 소형
    "ONG", "IN", "KERNEL", "WCT", "KAIA",
    "ZETA", "ARDR", "PYTH", "YGG", "CHZ", "MOC",

    # 저가 / 신규
    "SENT", "DEEP", "MOVE", "ZK", "ZORA",
    "CPOOL", "BLUR", "POKT", "BOUNTY",
    "MOCA", "STRAX",

    # 초저가
    "FCT2", "PLUME", "SOPH", "META", "NOM",
    "DKA", "DOOD", "QKC", "LINEA", "BLAST"
    ]

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
# 텔레그램 전송
# ===============================
def send_telegram(msg):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg},
        timeout=10
    )


# ===============================
# 수동 조회 실행
# ===============================
def manual_check():
    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exe:
        futures = [exe.submit(compare_coin, c) for c in COINS]

        for f in as_completed(futures):
            r = f.result()
            if r:
                results.append(r)

    if not results:
        send_telegram("📊 수동 조회 결과 없음")
        return

    # 가격차 기준 정렬
    results.sort(key=lambda x: x[1], reverse=True)

    upbit_high = [r for r in results if r[1] > 0][:7]
    bithumb_high = [r for r in results if r[1] < 0][-7:][::-1]

    msg = "📊 업비트 ↔ 빗썸 가격차이 (수동 조회)\n\n"

    msg += "📈 업비트가 더 비싼 TOP 7\n"
    for c, d, up, bt in upbit_high:
        msg += f"{c} | {d:.2f}% | 업 {up:,} / 빗 {bt:,}\n"

    msg += "\n📉 빗썸이 더 비싼 TOP 7\n"
    for c, d, up, bt in bithumb_high:
        msg += f"{c} | {d:.2f}% | 업 {up:,} / 빗 {bt:,}\n"

    send_telegram(msg)


# ===============================
# 실행
# ===============================
if __name__ == "__main__":
    manual_check()
