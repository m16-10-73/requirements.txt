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
        padding-top: 0.8rem !important;
        padding-bottom: 0.8rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    .stApp {
        background-color: #f8f9fa;
    }
    .master-header {
        background: linear-gradient(135deg, #2c3e50, #4ca1af);
        padding: 10px 14px;
        border-radius: 8px;
        color: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 15px;
    }
    .master-header h1 {
        color: #ffffff;
        font-size: 1.1rem;
        margin: 0;
    }
    .master-header p {
        color: #f0f0f0;
        margin: 2px 0 0 0;
        font-size: 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="master-header">
        <h1>📊 RESUMEN CONSOLIDADO — 4 BOTS</h1>
        <p>Vista global de capitales y rendimiento actual</p>
    </div>
    """,
    unsafe_allow_html=True,
)

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
                historial = data.get("historial_rendimiento", [])
                
                if historial and isinstance(historial, list) and len(historial) > 0:
                    capital_inicial = float(historial[0].get("Capital", 10000.0))
                    capital_actual = float(historial[-1].get("Capital", capital_inicial))
                else:
                    capital_inicial = float(data.get("capital_inicial", 10000.0))
                    capital_actual = capital_inicial
        except Exception:
            pass

    if capital_inicial > 0:
        rentabilidad = ((capital_actual - capital_inicial) / capital_inicial) * 100.0
    else:
        rentabilidad = 0.0

    resumen_datos.append({
        "Estrategia": nombre,
        "Inicial": capital_inicial,
        "Actual": capital_actual,
        "Rentab (%)": rentabilidad
    })

df_resumen = pd.DataFrame(resumen_datos)

# Función para formatear al estilo europeo/latino (10.000,00) sin sufijos largos
def formato_moneda_latino(val):
    # Formatea con comas para miles y punto para decimales temporalmente, luego invierte
    s = f"{val:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"${s}"

df_resumen["Inicial"] = df_resumen["Inicial"].apply(formato_moneda_latino)
df_resumen["Actual"] = df_resumen["Actual"].apply(formato_moneda_latino)
df_resumen["Rentab (%)"] = df_resumen["Rentab (%)"].apply(lambda x: f"{'+' if x >= 0 else ''}{x:.2f}%")

st.dataframe(df_resumen, use_container_width=True, hide_index=True)
