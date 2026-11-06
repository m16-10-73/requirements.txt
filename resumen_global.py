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

# Orden exacto solicitado: Dinámica, Valoris, Emergente, Eventos
archivos_bots = [
    {"Nombre": "Bot Dinámico", "Archivo": "bitacora_dinamica.json"},
    {"Nombre": "Bot Valoris", "Archivo": "bitacora.valoris.json"},
    {"Nombre": "Bot Emergente", "Archivo": "bitacora_emerging.json"},
    {"Nombre": "Bot Eventos", "Archivo": "bitacora_eventos.json"}
]

resumen_datos = []

for bot in archivos_bots:
    nombre = bot["Nombre"]
    archivo = bot["Archivo"]
    
    capital_inicial = 10000.0
    capital_actual = 10000.0
    
    if os.path.exists(archivo):
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # 1. Obtener capital inicial de la raíz con respaldo genérico
                for key in ["capital_inicial", "capital_base", "initial_capital"]:
                    if key in data:
                        capital_inicial = float(data[key])
                        break
                
                # 2. Obtener historial o registros de rendimiento
                historial = None
                for h_key in ["historial_rendimiento", "historial", "history", "rendimiento"]:
                    if h_key in data and isinstance(data[h_key], list) and len(data[h_key]) > 0:
                        historial = data[h_key]
                        break
                
                if historial:
                    # Extraer el valor del último registro del historial como capital actual
                    ultimo_registro = historial[-1]
                    for c_key in ["Capital", "capital", "capital_actual", "current_capital", "valor"]:
                        if c_key in ultimo_registro:
                            capital_actual = float(ultimo_registro[c_key])
                            break
                else:
                    # Si no hay historial, buscar capital actual en la raíz
                    for c_key in ["capital_actual", "current_capital", "capital_cierre"]:
                        if c_key in data:
                            capital_actual = float(data[c_key])
                            break
                    else:
                        capital_actual = capital_inicial
                        
        except Exception:
            pass

    # Cálculo seguro de la rentabilidad
    if capital_inicial > 0:
        rentabilidad = ((capital_actual - capital_inicial) / capital_inicial) * 100.0
    else:
        rentabilidad = 0.0

    resumen_datos.append({
        "Estrategia": nombre,
        "Capital Inicial / Base": capital_inicial,
        "Capital Actual / Cierre": capital_actual,
        "Rentabilidad (%)": rentabilidad
    })

df_resumen = pd.DataFrame(resumen_datos)

# Dar formato visual limpio a la tabla
df_resumen["Capital Inicial / Base"] = df_resumen["Capital Inicial / Base"].apply(lambda x: f"${x:,.2f} USD")
df_resumen["Capital Actual / Cierre"] = df_resumen["Capital Actual / Cierre"].apply(lambda x: f"${x:,.2f} USD")
df_resumen["Rentabilidad (%)"] = df_resumen["Rentabilidad (%)"].apply(lambda x: f"{'+' if x >= 0 else ''}{x:.2f}%")

st.dataframe(df_resumen, use_container_width=True, hide_index=True)
