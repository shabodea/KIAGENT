import sys
import os
import time
import requests
import pandas as pd
from datetime import datetime


# ==================================================
# SYSTEM PFAD
# ==================================================

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

if BASE_PATH not in sys.path:
    sys.path.insert(0, BASE_PATH)


# ==================================================
# IMPORTS
# ==================================================

from config.settings import HEADERS, SUPABASE_URL
from agents.gemini_agent import GeminiCoreAgent


# ==================================================
# KI INITIALISIEREN
# ==================================================

print("🦅 Initialisiere KI-Agent...", flush=True)

gemini_agent = GeminiCoreAgent()

print("✅ Gemini-Agent geladen", flush=True)



# ==================================================
# MARKTDATEN
# ==================================================

def get_live_kraken_markets():

    try:

        url = "https://api.kraken.com/0/public/AssetPairs"

        response = requests.get(
            url,
            timeout=10
        )

        data = response.json()

        if "result" not in data:
            return [
                "XBTUSDT",
                "ETHUSDT"
            ]


        markets = [
            x for x in data["result"].keys()
            if x.endswith("USDT")
        ]


        return markets[:3]


    except Exception as e:

        print(
            f"❌ Kraken Fehler: {e}",
            flush=True
        )

        return [
            "XBTUSDT",
            "ETHUSDT"
        ]



def calculate_market_metrics(pair):

    try:

        url = (
            "https://api.kraken.com/0/public/OHLC"
            f"?pair={pair}&interval=15"
        )


        response = requests.get(
            url,
            timeout=10
        )


        data = response.json()


        if "result" not in data:
            return None


        candles = list(
            data["result"].values()
        )[0]


        df = pd.DataFrame(
            candles,
            columns=[
                "time",
                "open",
                "high",
                "low",
                "close",
                "vwap",
                "volume",
                "count"
            ]
        )


        df["close"] = df["close"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)



        df["ema20"] = (
            df["close"]
            .rolling(20)
            .mean()
        )


        delta = df["close"].diff()


        gain = (
            delta.where(delta > 0,0)
            .rolling(14)
            .mean()
        )


        loss = (
            -delta.where(delta < 0,0)
            .rolling(14)
            .mean()
        )


        rsi = (
            100 -
            (
                100 /
                (
                    1 +
                    gain.iloc[-1] /
                    loss.iloc[-1]
                )
            )
        ) if loss.iloc[-1] != 0 else 100



        return {

            "price":
                float(df["close"].iloc[-1]),

            "ema":
                float(df["ema20"].iloc[-1]),

            "rsi":
                round(float(rsi),2)

        }



    except Exception as e:

        print(
            f"❌ Analyse Fehler {pair}: {e}",
            flush=True
        )

        return None




# ==================================================
# TRADING ZYKLUS
# ==================================================

def run_market_cycle():


    print(
        "📈 Starte Marktanalyse...",
        flush=True
    )


    markets = get_live_kraken_markets()


    for market in markets:


        metrics = calculate_market_metrics(
            market
        )


        if not metrics:
            continue



        print(
            f"{market}: "
            f"{metrics}",
            flush=True
        )



        price = metrics["price"]
        ema = metrics["ema"]
        rsi = metrics["rsi"]



        # einfache Teststrategie

        if price > ema and rsi < 55:


            print(
                f"🎯 Signal {market}",
                flush=True
            )



            answer = (
                gemini_agent
                .execute_thought_cycle(
                    f"""
                    Analysiere diesen Markt:

                    Asset: {market}
                    Preis: {price}
                    RSI: {rsi}
                    EMA: {ema}

                    Antworte nur:
                    BUY
                    oder
                    HOLD
                    """
                )
            )


            print(
                f"🤖 Gemini: {answer}",
                flush=True
            )


# ==================================================
# HAUPTSCHLEIFE
# ==================================================

def main():


    print(
        "🚀 KIAgent Worker gestartet",
        flush=True
    )


    while True:


        try:


            # ----------------------------
            # CHAT KI
            # ----------------------------

            print(
                "💬 Prüfe Chat...",
                flush=True
            )


            gemini_agent.process_live_chat()



            # ----------------------------
            # MARKT
            # ----------------------------

            run_market_cycle()



        except Exception as e:


            print(
                f"🔥 Worker Fehler: {e}",
                flush=True
            )



        time.sleep(10)




if __name__ == "__main__":

    main()
