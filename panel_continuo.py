import base64
from datetime import datetime, timedelta, timezone
import json
import time
import altair as alt
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Panel Continuo — 4 Columnas",
    page_icon="📊",
    layout="wide",
)

st.markdown('<meta http-equiv="refresh" content="30">', unsafe_allow_html=True)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    .stApp {
        background-color: #f8f9fa !important;
    }
    .bot-banner {
        padding: 10px 12px;
        border-radius: 8px;
        color: #ffffff !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 12px;
        min-height: 76px;
    }
    .bot-banner h3 {
        color: #ffffff !important;
        margin: 0;
        font-size: 0.98rem;
        font-weight: 700;
        line-height: 1.25;
    }
    .bot-banner p {
        color: #ffffff !important;
        margin: 4px 0 0 0;
        font-size: 0.74rem;
        opacity: 0.95;
        line-height: 1.25;
    }
    .nota-ref {
        font-size: 0.74rem;
        color: #57606a;
        margin-top: -6px;
        margin-bottom: 12px;
        line-height: 1.3;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.05rem !important;
    }
    div[data-testid="stMetricDelta"] {
        font-size: 0.72rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
OWNER = "m16-10-73"
REPO = "requirements.txt"
BRANCH = "main"

CONFIG_BOTS = {
    "dinamica": {
        "titulo": "📈 DINÁMICO",
        "subtitulo": "Momentum | SL 1m (-0.50%)",
        "gradiente": "linear-gradient(135deg, #FF512F, #DD2476)",
        "file_path": "bitacora_dinamica.json",
        "msg_commit": "Actualización automática de bitácora dinámica",
        "sl_pct": -0.50,
        "meta_default": 3.00,
        "tol_default": 0.50,
        "num_activos": 3,
        "candidatos": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NFLX", "AMD", "INTC"],
        "modo_seleccion": "fijo",
    },
    "valoris": {
        "titulo": "🛡️ VALORIS",
        "subtitulo": "Value/Div | SL 1m (-0.75%)",
        "gradiente": "linear-gradient(135deg, #134E5E, #71B280)",
        "file_path": "bitacora_valoris.json",
        "msg_commit": "Actualización automática de bitácora Valoris",
        "sl_pct": -0.75,
        "meta_default": 3.50,
        "tol_default": 0.60,
        "num_activos": 5,
        "candidatos": [
            "JNJ", "PG", "KO", "PEP", "MRK", "ABBV", "PFE", "IBM", "CVX", "XOM",
            "VZ", "T", "MMM", "WMT", "MCD", "CSCO", "AMGN", "LOW", "UNH",
        ],
        "modo_seleccion": "momentum_2d_mcap",
    },
    "emergente": {
        "titulo": "⚡ EMERGING",
        "subtitulo": "Alta Beta | SL 1m (-1.00%)",
        "gradiente": "linear-gradient(135deg, #E67E22, #F1C40F)",
        "file_path": "bitacora_emerging.json",
        "msg_commit": "Actualización automática de bitácora Emerging",
        "sl_pct": -1.00,
        "meta_default": 3.50,
        "tol_default": 0.65,
        "num_activos": 5,
        "candidatos": ["NVDA", "AMD", "TSLA", "PLTR", "COIN", "SHOP", "SQ", "U", "RBLX", "MARA"],
        "modo_seleccion": "momentum_2d",
    },
    "eventos": {
        "titulo": "📰 EVENTOS",
        "subtitulo": "ETFs/Flujo | SL 1m (-1.00%)",
        "gradiente": "linear-gradient(135deg, #2C3E50, #4CA1AF)",
        "file_path": "bitacora_eventos.json",
        "msg_commit": "Actualización automática de bitácora Eventos",
        "sl_pct": -1.00,
        "meta_default": 3.00,
        "tol_default": 0.50,
        "num_activos": 3,
        "candidatos": ["SPY", "QQQ", "DIA", "IWM", "XLE", "XLF", "XLV", "XLI", "XLC", "XLU"],
        "modo_seleccion": "momentum_2d",
    },
}


def fecha_hoy_chile():
    chile_tz = timezone(timedelta(hours=-3))
    now_cl = datetime.now(chile_tz)
    return now_cl.strftime("%d/%m/%Y"), now_cl.strftime("%H:%M")


def cargar_bitacora_gh(file_path, msg_commit):
    base_default_inicial = {"Fecha": "28/10/2026", "Capital": 100000.00}
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            file_data = response.json()
            file_content = base64.b64decode(file_data["content"]).decode("utf-8")
            contenido = json.loads(file_content)
            if isinstance(contenido, dict):
                contenido.setdefault("ganancia_cerrada", 0.0)
                contenido.setdefault("posiciones", [])
                contenido.setdefault("peak_flotante", 0.0)
                contenido.setdefault("historial_alertas", [])
                contenido.setdefault("ultimo_cierre_automatico", "")

                historial = contenido.get("historial_rendimiento", [])
                historial_limpio = {}
                for h in historial:
                    f_limpia = str(h.get("Fecha", "")).split(" ")[0]
                    cap_val = float(h.get("Capital", 0.0))
                    if f_limpia and cap_val > 0:
                        historial_limpio[f_limpia] = cap_val

                if not historial_limpio:
                    historial_limpio[base_default_inicial["Fecha"]] = base_default_inicial["Capital"]

                lista_temporal = [{"Fecha": k, "Capital": v} for k, v in historial_limpio.items()]
                try:
                    lista_ordenada = sorted(
                        lista_temporal,
                        key=lambda x: datetime.strptime(x["Fecha"], "%d/%m/%Y"),
                    )
                except Exception:
                    lista_ordenada = lista_temporal

                contenido["historial_rendimiento"] = lista_ordenada
                contenido["capital_inicial"] = (
                    float(lista_ordenada[-1]["Capital"]) if lista_ordenada else 100000.00
                )
                return contenido
    except Exception as e:
        st.error(f"⚠️ Error al leer {file_path}: {e}")

    base_data = {
        "capital_inicial": 100000.00,
        "ganancia_cerrada": 0.0,
        "posiciones": [],
        "peak_flotante": 0.0,
        "historial_alertas": [],
        "ultimo_cierre_automatico": "",
        "historial_rendimiento": [base_default_inicial],
    }
    guardar_bitacora_gh(file_path, msg_commit, base_data)
    return base_data


def guardar_bitacora_gh(file_path, msg_commit, data):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    response = requests.get(url, headers=headers)
    sha = response.json().get("sha") if response.status_code == 200 else None

    contenido_json_string = json.dumps(data, indent=4, ensure_ascii=False)
    contenido_base64 = base64.b64encode(contenido_json_string.encode("utf-8")).decode("utf-8")

    payload = {
        "message": msg_commit,
        "content": contenido_base64,
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha

    requests.put(url, headers=headers, json=payload)


def cerrar_jornada_bot(cfg, capital_final, origen="manual"):
    fecha_actual, _ = fecha_hoy_chile()
    capital_redondeado = round(float(capital_final), 2)

    datos_actuales = cargar_bitacora_gh(cfg["file_path"], cfg["msg_commit"])
    historial = [
        h
        for h in datos_actuales.get("historial_rendimiento", [])
        if str(h.get("Fecha", "")).split(" ")[0] != fecha_actual
    ]
    historial.append({"Fecha": fecha_actual, "Capital": capital_redondeado})

    try:
        historial = sorted(
            historial, key=lambda x: datetime.strptime(x["Fecha"], "%d/%m/%Y")
        )
    except Exception:
        pass

    nuevo_estado = {
        "capital_inicial": capital_redondeado,
        "ganancia_cerrada": 0.0,
        "posiciones": [],
        "peak_flotante": 0.0,
        "historial_alertas": datos_actuales.get("historial_alertas", []),
        "ultimo_cierre_automatico": (
            fecha_actual
            if origen == "automatico"
            else datos_actuales.get("ultimo_cierre_automatico", "")
        ),
        "historial_rendimiento": historial,
    }
    guardar_bitacora_gh(cfg["file_path"], cfg["msg_commit"], nuevo_estado)


def seleccionar_activos(cfg):
    modo = cfg["modo_seleccion"]
    candidatos = cfg["candidatos"]
    n = cfg["num_activos"]

    if modo == "fijo":
        return candidatos[:n]

    resultados = []
    for ticker in candidatos:
        try:
            yt = yf.Ticker(ticker)
            if modo == "momentum_2d_mcap":
                mcap = yt.fast_info.get("marketCap", 0)
                if mcap < 15_000_000_000:
                    continue
            df = yt.history(period="2d")
            if len(df) >= 2:
                c_prev = df["Close"].iloc[-2]
                c_act = df["Close"].iloc[-1]
                var_pct = ((c_act - c_prev) / c_prev) * 100.0
                resultados.append((ticker, var_pct))
        except Exception:
            continue

    resultados.sort(key=lambda x: x[1], reverse=True)
    return [item[0] for item in resultados[:n]]


def render_bot_columna(bot_key, cfg):
    data_bitacora = cargar_bitacora_gh(cfg["file_path"], cfg["msg_commit"])
    meta_diaria_pct = float(cfg["meta_default"])
    tolerancia_pct = float(cfg["tol_default"])
    sl_pct = float(cfg["sl_pct"])

    st.markdown(
        f"""
        <div class="bot-banner" style="background: {cfg['gradiente']};">
            <h3>{cfg['titulo']}</h3>
            <p>{cfg['subtitulo']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    posiciones = data_bitacora.get("posiciones", [])
    total_flotante = 0.0
    posiciones_procesadas = []
    posiciones_restantes = []
    hubo_cierre_individual = False

    for pos in posiciones:
        ticker = pos.get("ticker")
        precio_entrada = float(pos.get("precio_entrada", 0.0))
        acciones = float(pos.get("acciones", 0.0))

        try:
            df = yf.Ticker(ticker).history(period="1d", interval="1m")
            if not df.empty:
                precio_actual = float(df["Close"].iloc[-1])
                precio_minimo = float(df["Low"].iloc[-1])
            else:
                precio_actual = precio_entrada
                precio_minimo = precio_entrada
        except Exception:
            precio_actual = precio_entrada
            precio_minimo = precio_entrada

        pnl_usd = (precio_actual - precio_entrada) * acciones
        pnl_pct = (
            (((precio_actual - precio_entrada) / precio_entrada) * 100.0)
            if precio_entrada > 0
            else 0.0
        )
        pnl_minimo_pct = (
            (((precio_minimo - precio_entrada) / precio_entrada) * 100.0)
            if precio_entrada > 0
            else 0.0
        )

        if pnl_pct <= sl_pct or pnl_minimo_pct <= sl_pct:
            precio_ejecucion = min(precio_actual, precio_minimo)
            pnl_cierre_usd = (precio_ejecucion - precio_entrada) * acciones
            pnl_cierre_pct = (
                (((precio_ejecucion - precio_entrada) / precio_entrada) * 100.0)
                if precio_entrada > 0
                else 0.0
            )
            data_bitacora["ganancia_cerrada"] += pnl_cierre_usd
            hora_act = time.strftime("%H:%M:%S")
            data_bitacora.setdefault("historial_alertas", []).append(
                f"[{hora_act}] 🛡️ SL ({sl_pct:.2f}%): {ticker} a {pnl_cierre_pct:.2f}% (${pnl_cierre_usd:.2f} USD)."
            )
            hubo_cierre_individual = True
        else:
            total_flotante += pnl_usd
            posiciones_restantes.append(pos)
            posiciones_procesadas.append({
                "Activo": ticker,
                "Entrada": round(precio_entrada, 2),
                "Actual": round(precio_actual, 2),
                "PnL $": round(pnl_usd, 2),
                "PnL %": round(pnl_pct, 2),
            })

    if hubo_cierre_individual:
        data_bitacora["posiciones"] = posiciones_restantes
        guardar_bitacora_gh(cfg["file_path"], cfg["msg_commit"], data_bitacora)
        st.rerun()

    capital_base = float(data_bitacora.get("capital_inicial", 100000.00))
    ganancia_cerrada = float(data_bitacora.get("ganancia_cerrada", 0.0))
    capital_total_actual = round(capital_base + ganancia_cerrada + total_flotante, 2)

    flotante_pct = (total_flotante / capital_base) * 100 if capital_base > 0 else 0.0
    ganancia_total_dia = ganancia_cerrada + total_flotante
    ganancia_total_pct = (
        (ganancia_total_dia / capital_base) * 100 if capital_base > 0 else 0.0
    )

    historial = data_bitacora.get("historial_rendimiento", [])

    peak_previo = float(data_bitacora.get("peak_flotante", 0.0))
    if flotante_pct > peak_previo:
        data_bitacora["peak_flotante"] = flotante_pct
        guardar_bitacora_gh(cfg["file_path"], cfg["msg_commit"], data_bitacora)
        peak_actual = flotante_pct
    else:
        peak_actual = peak_previo

    umbral_salida = max(peak_actual - tolerancia_pct, meta_diaria_pct)

    # Cierre automático por Trailing Stop Global
    if (
        peak_actual >= meta_diaria_pct
        and flotante_pct <= umbral_salida
        and len(posiciones_procesadas) > 0
    ):
        cerrar_jornada_bot(cfg, capital_total_actual, origen="automatico")
        st.rerun()

    # Cierre automático por horario (18:00 Chile)
    fecha_hoy_str, hora_actual_str = fecha_hoy_chile()
    if hora_actual_str >= "18:00" and data_bitacora.get("ultimo_cierre_automatico", "") != fecha_hoy_str:
        cerrar_jornada_bot(cfg, capital_total_actual, origen="automatico")
        st.rerun()

    if st.button("🚀 Abrir Jornada", key=f"abrir_{bot_key}", use_container_width=True):
        top_act = seleccionar_activos(cfg)
        if top_act:
            monto_por_accion = capital_base / len(top_act)
            nuevas_pos = []
            for t in top_act:
                try:
                    px = float(yf.Ticker(t).history(period="1d")["Close"].iloc[-1])
                except Exception:
                    px = 100.0
                nuevas_pos.append({
                    "ticker": t,
                    "precio_entrada": round(px, 2),
                    "acciones": round(monto_por_accion / px, 4),
                })
            data_bitacora["posiciones"] = nuevas_pos
            data_bitacora["peak_flotante"] = 0.0
            guardar_bitacora_gh(cfg["file_path"], cfg["msg_commit"], data_bitacora)
            st.rerun()

    if st.button(
        "⏹️ Cerrar Jornada Anticipada",
        key=f"anticipada_{bot_key}",
        type="primary",
        use_container_width=True,
    ):
        cerrar_jornada_bot(cfg, capital_total_actual, origen="anticipada")
        st.success(f"Cerrado: ${capital_total_actual:,.2f}")
        time.sleep(1)
        st.rerun()

    st.metric(
        "Capital Cuenta",
        f"${capital_total_actual:,.2f}",
        f"Base: ${capital_base:,.2f}",
    )
    st.metric(
        "Ganancia / Flotante Hoy",
        f"{'+' if ganancia_total_dia >= 0 else ''}${ganancia_total_dia:,.2f}",
        f"Flot: {'+' if total_flotante >= 0 else ''}${total_flotante:,.2f} ({ganancia_total_pct:.2f}%)",
    )
    st.markdown(
        f"""
        <div class="nota-ref">
            Meta: {meta_diaria_pct:.2f}% | Umbral: +{umbral_salida:.2f}% | Peak: +{peak_actual:.2f}% | SL: {sl_pct:.2f}%
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption("**Posiciones en Curso**")
    if posiciones_procesadas:
        st.dataframe(pd.DataFrame(posiciones_procesadas), use_container_width=True, hide_index=True)
    else:
        st.info("Sin posiciones abiertas.")

    if historial:
        df_hist = pd.DataFrame(historial)
        if "Fecha" in df_hist.columns and "Capital" in df_hist.columns:
            df_hist["Fecha_limpia"] = df_hist["Fecha"].astype(str).str.split(" ").str[0]
            df_hist["Fecha_obj"] = pd.to_datetime(
                df_hist["Fecha_limpia"], format="%d/%m/%Y", errors="coerce"
            )
            df_hist = df_hist.sort_values(by="Fecha_obj", ascending=True).reset_index(drop=True)

            cap_0 = float(df_hist["Capital"].iloc[0]) if len(df_hist) > 0 else 100000.0
            df_hist["Rent_Diaria_Pct"] = df_hist["Capital"].pct_change().fillna(0.0) * 100.0
            df_hist["Rent_Acumulada_Pct"] = ((df_hist["Capital"] - cap_0) / cap_0) * 100.0

            chart = (
                alt.Chart(df_hist)
                .mark_line(point=True, strokeWidth=2.5)
                .encode(
                    x=alt.X("Fecha_limpia:N", title="Fecha", sort=df_hist["Fecha_limpia"].tolist()),
                    y=alt.Y("Capital:Q", title="Capital", scale=alt.Scale(zero=False)),
                    tooltip=["Fecha_limpia", alt.Tooltip("Capital:Q", format="$,.2f")],
                )
                .properties(height=180)
            )
            st.altair_chart(chart, use_container_width=True)

            df_mostrar = df_hist.sort_values(by="Fecha_obj", ascending=False).copy()
            df_mostrar["Ac. %"] = df_mostrar["Rent_Acumulada_Pct"].apply(
                lambda x: f"{'+' if x >= 0 else ''}{x:.2f}%"
            )
            df_mostrar["Capital"] = df_mostrar["Capital"].apply(
                lambda x: f"${float(x):,.0f}"
            )
            df_mostrar = df_mostrar[["Fecha_limpia", "Capital", "Ac. %"]].rename(
                columns={"Fecha_limpia": "Fecha"}
            )
            st.dataframe(df_mostrar.head(7), use_container_width=True, hide_index=True)


st.markdown("### 📊 Panel Continuo — 4 Columnas")

cols = st.columns(4, gap="medium")
bots_en_orden = ["dinamica", "valoris", "emergente", "eventos"]

for col, bot_key in zip(cols, bots_en_orden):
    with col:
        render_bot_columna(bot_key, CONFIG_BOTS[bot_key])
