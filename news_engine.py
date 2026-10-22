import pandas as pd
import yfinance as yf

# Palabras clave para scoring básico de sentimiento en inglés (usado por yfinance news)
PALABRAS_POSITIVAS = [
    "growth",
    "profit",
    "record",
    "surge",
    "bullish",
    "gain",
    "outperform",
    "beat",
    "high",
    "upward",
    "buy",
    "revenue",
    "partnership",
    "expansion",
]
PALABRAS_NEGATIVAS = [
    "loss",
    "drop",
    "fall",
    "bearish",
    "decline",
    "miss",
    "lawsuit",
    "risk",
    "downgrade",
    "cut",
    "fail",
    "warn",
    "bankruptcy",
    "slash",
]

# Universo de escaneo para el bot de eventos
CANDIDATAS_EVENT_DRIVEN = [
    "NVDA",
    "TSLA",
    "AAPL",
    "MSFT",
    "AMZN",
    "GOOGL",
    "META",
    "AMD",
    "NFLX",
    "PLTR",
    "INTC",
    "COIN",
    "BA",
    "DIS",
    "BABA",
]


def analizar_sentimiento_texto(texto: str) -> float:
    """Calcula un score entre -1.0 y +1.0 basado en presencia de palabras clave."""
    if not texto:
        return 0.0

    texto_lower = texto.lower()
    pos = sum(1 for p in PALABRAS_POSITIVAS if p in texto_lower)
    neg = sum(1 for n in PALABRAS_NEGATIVAS if n in texto_lower)

    total = pos + neg
    if total == 0:
        return 0.0

    return (pos - neg) / total


def obtener_noticias_y_sentimiento(ticker: str) -> dict:
    """Obtiene titulares recientes de yfinance para un ticker y determina el sentimiento promedio."""
    try:
        yt = yf.Ticker(ticker)
        news = yt.news

        if not news:
            return {
                "ticker": ticker,
                "score": 0.0,
                "titulares": [],
                "estado": "Sin noticias recientes",
            }

        scores = []
        titulares = []

        for item in news[:5]:  # Analiza los últimos 5 titulares
            titulo = item.get("title", "")
            if titulo:
                sc = analizar_sentimiento_texto(titulo)
                scores.append(sc)
                titulares.append(titulo)

        score_promedio = sum(scores) / len(scores) if scores else 0.0

        return {
            "ticker": ticker,
            "score": round(score_promedio, 2),
            "titulares": titulares[:3],  # Guarda los 3 más relevantes
            "estado": "OK",
        }
    except Exception as e:
        return {
            "ticker": ticker,
            "score": 0.0,
            "titulares": [],
            "estado": f"Error: {str(e)}",
        }


def seleccionar_top_eventdriven(n: int = 5) -> list:
    """Filtra el universo por sentimiento positivo y ordena por momentum/variación."""
    resultados = []

    for ticker in CANDIDATAS_EVENT_DRIVEN:
        info_sentimiento = obtener_noticias_y_sentimiento(ticker)

        # Solo considera acciones con sentimiento neutro-positivo o alto (> 0.0)
        if info_sentimiento["score"] >= 0.0:
            try:
                df = yf.Ticker(ticker).history(period="2d")
                if len(df) >= 2:
                    c_prev = df["Close"].iloc[-2]
                    c_act = df["Close"].iloc[-1]
                    var_pct = ((c_act - c_prev) / c_prev) * 100.0
                else:
                    var_pct = 0.0
            except Exception:
                var_pct = 0.0

            resultados.append({
                "ticker": ticker,
                "score_sentimiento": info_sentimiento["score"],
                "var_pct": var_pct,
                "titulares": info_sentimiento["titulares"],
            })

    # Ordena combinando sentimiento y momentum
    resultados.sort(
        key=lambda x: (x["score_sentimiento"], x["var_pct"]), reverse=True
    )

    return resultados[:n]
