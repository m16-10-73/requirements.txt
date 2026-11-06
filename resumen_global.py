import os
import json
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Consolidado de Bots de Trading",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    .stApp {
        background-color: #f8f9fa;
    }
    .master-header {
        background: linear-gradient(135deg, #2c3e50, #4ca1af);
        padding: 12px 18px;
        border-radius: 10px;
        color: white;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .master-header h1 {
        color: #ffffff;
        font-size: 1.3rem;
        margin: 0;
    }
    .master-header p {
        color: #f0f0f0;
        margin: 3px 0 0 0;
        font-size: 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="master-header">
        <h1>📊 RESUMEN CONSOLIDADO — 4 BOTS DE TRADING</h1>
        <p>Vista global de capitales iniciales, cierres y rendimiento actual de las estrategias</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Definición de los archivos de bitácora de cada bot
archivos_bots = [
    {"Nombre": "Bot Eventos", "Archivo": "bitacora_eventos.json"},
    {"Nombre": "Bot Dinámico", "Archivo": "bitacora_dinamica.json"},
    {"Nombre": "Bot Valoris", "Archivo": "bitacora_valoris.json"},
    {"Nombre": "Bot Emergente", "Archivo": "bitacora_emergente.json"}
]

resumen_datos = []

for bot in archivos_bots:
    nombre = bot["Nombre"]
    archivo = bot["Archivo"]
    
    capital_inicial = 10000.0
    capital_actual = 10000.0
    rentabilidad = 0.0
    
    if os.path.exists(archivo):
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # Obtener capital base o inicial configurado
                capital_inicial = float(data.get("capital_inicial", 10000.0))
                
                # Buscar en el historial de rendimiento el último cierre o valor
                historial = data.get("historial_rendimiento", [])
                if historial:
                    ultimo_reg = historial[-1]
                    capital_actual = float(ultimo_reg.get("Capital", capital_inicial))
                else:
                    capital_actual = capital_inicial
                    
                # Calcular rentabilidad respecto al inicio histórico (10,000 USD de base general)
                primer_capital = float(historial[0].get("Capital", 10000.0)) if historial else 10000.0
                rentabilidad = ((capital_actual - primer_capital) / primer_capital) * 100.0
        except Exception:
            pass

    resumen_datos.append({
        "Estrategia": nombre,
        "Capital Inicial / Base": round(capital_inicial, 2),
        "Capital Actual / Cierre": round(capital_actual, 2),
        "Rentabilidad (%)": round(rentabilidad, 2)
    })

df_resumen = pd.DataFrame(resumen_datos)

# Formatear visualmente los números para la tabla
df_resumen["Capital Inicial / Base"] = df_resumen["Capital Inicial / Base"].apply(lambda x: f"${x:,.2f} USD")
df_resumen["Capital Actual / Cierre"] = df_resumen["Capital Actual / Cierre"].apply(lambda x: f"${x:,.2f} USD")
df_resumen["Rentabilidad (%)"] = df_resumen["Rentabilidad (%)"].apply(lambda x: f"{'+' if x >= 0 else ''}{x:.2f}%")

# Mostrar la tabla resumen en fila / planilla limpia
st.dataframe(df_resumen, use_container_width=True, hide_index=True)
