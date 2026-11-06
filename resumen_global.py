import os
import json
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
    /* Estilo de tarjeta vertical optimizada para celular */
    .bot-card {
        background: white;
        border-radius: 8px;
        padding: 12px 15px;
        margin-bottom: 10px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        border-left: 4px solid #4ca1af;
    }
    .bot-title {
        font-weight: bold;
        font-size: 1rem;
        color: #2c3e50;
        margin-bottom: 8px;
        border-bottom: 1px solid #eee;
        padding-bottom: 5px;
    }
    .bot-row {
        display: flex;
        justify-content: space-between;
        font-size: 0.88rem;
        padding: 4px 0;
    }
    .bot-label {
        color: #666;
    }
    .bot-value {
        font-weight: 600;
        color: #333;
    }
    .positive {
        color: #2e7d32;
    }
    .negative {
        color: #c62828;
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

    rent_class = "positive" if rentabilidad >= 0 else "negative"
    rent_sign = "+" if rentabilidad >= 0 else ""

    # Tarjeta vertical compacta
    st.markdown(f"""
    <div class="bot-card">
        <div class="bot-title">{nombre}</div>
        <div class="bot-row">
            <span class="bot-label">Cap. Inicial:</span>
            <span class="bot-value">${capital_inicial:,.2f}</span>
        </div>
        <div class="bot-row">
            <span class="bot-label">Cap. Actual:</span>
            <span class="bot-value">${capital_actual:,.2f}</span>
        </div>
        <div class="bot-row">
            <span class="bot-label">Rentabilidad:</span>
            <span class="bot-value {rent_class}">{rent_sign}{rentabilidad:.2f}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
