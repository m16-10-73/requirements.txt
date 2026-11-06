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

archivos_bots = [
    {"Nombre": "Bot Dinámico", "Archivo": "bitacora_dinamica.json"},
    {"Nombre": "Bot Valoris", "Archivo": "bitacora.valoris.json"},
    {"Nombre": "Bot Emergente", "Archivo": "bitacora_emerging.json"},
    {"Nombre": "Bot Eventos", "Archivo": "bitacora_eventos.json"}
]

resumen_datos = []
debug_info = {}

for bot in archivos_bots:
    nombre = bot["Nombre"]
    archivo = bot["Archivo"]
    
    capital_inicial = 10000.0
    capital_actual = 10000.0
    origen_logica = "Por defecto"
    
    if os.path.exists(archivo):
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # Detectar estructura basada en claves raíz e historial
                tiene_capital_raiz = "capital_inicial" in data
                historial = data.get("historial_rendimiento", [])
                
                if tiene_capital_raiz:
                    capital_inicial = float(data["capital_inicial"])
                
                if historial and isinstance(historial, list) and len(historial) > 0:
                    # Si hay historial, el actual es el último registro
                    ultimo_reg = historial[-1]
                    for c_key in ["Capital", "capital", "capital_actual"]:
                        if c_key in ultimo_reg:
                            capital_actual = float(ultimo_reg[c_key])
                            break
                    if not tiene_capital_raiz:
                        # Si no hay capital inicial en raíz, tomamos el primer historial como base
                        primer_reg = historial[0]
                        for c_key in ["Capital", "capital"]:
                            if c_key in primer_reg:
                                capital_inicial = float(primer_reg[c_key])
                                break
                else:
                    if "capital_actual" in data:
                        capital_actual = float(data["capital_actual"])
                    else:
                        capital_actual = capital_inicial
                        
                origen_logica = f"Raíz init: {capital_inicial}, Historial len: {len(historial)}"
        except Exception as e:
            origen_logica = f"Error: {e}"

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
    
    debug_info[nombre] = origen_logica

df_resumen = pd.DataFrame(resumen_datos)

df_resumen["Capital Inicial / Base"] = df_resumen["Capital Inicial / Base"].apply(lambda x: f"${x:,.2f} USD")
df_resumen["Capital Actual / Cierre"] = df_resumen["Capital Actual / Cierre"].apply(lambda x: f"${x:,.2f} USD")
df_resumen["Rentabilidad (%)"] = df_resumen["Rentabilidad (%)"].apply(lambda x: f"{'+' if x >= 0 else ''}{x:.2f}%")

st.dataframe(df_resumen, use_container_width=True, hide_index=True)

# Panel de transparencia para ver cómo leyó cada archivo
with st.expander("🔍 Ver diagnóstico de lectura de cada bitácora"):
    st.json(debug_info)
