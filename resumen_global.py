import os
import json
import pandas as pd
from datetime import datetime
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
        padding-top: 1.8rem !important;
        padding-bottom: 1rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    .stApp {
        background-color: #f8f9fa;
    }
    .master-header {
        background: linear-gradient(135deg, #2c3e50, #4ca1af);
        padding: 12px 14px;
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
        <p>Vista global de capitales, fechas y rendimiento actual</p>
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
datos_grafico = []
sum_rentabilidad = 0.0

def formato_moneda_latino(val):
    s = f"{val:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"${s}"

for bot in archivos_bots:
    nombre = bot["Nombre"]
    archivo = bot["Archivo"]
    
    capital_inicial = 10000.0
    capital_actual = 10000.0
    fecha_inicio = "-"
    fecha_cierre = "-"
    dias_acumulados = 0
    
    if os.path.exists(archivo):
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                data = json.load(f)
                historial = data.get("historial_rendimiento", [])
                
                if historial and isinstance(historial, list) and len(historial) > 0:
                    primer_reg = historial[0]
                    ultimo_reg = historial[-1]
                    
                    capital_inicial = float(primer_reg.get("Capital", 10000.0))
                    capital_actual = float(ultimo_reg.get("Capital", capital_inicial))
                    
                    fecha_inicio = primer_reg.get("Fecha", "-")
                    fecha_cierre = ultimo_reg.get("Fecha", "-")
                    
                    try:
                        f1 = datetime.strptime(fecha_inicio, "%d/%m/%Y")
                        f2 = datetime.strptime(fecha_cierre, "%d/%m/%Y")
                        dias_acumulados = (f2 - f1).days
                    except Exception:
                        dias_acumulados = len(historial) - 1
                else:
                    capital_inicial = float(data.get("capital_inicial", 10000.0))
                    capital_actual = capital_inicial
        except Exception:
            pass

    if capital_inicial > 0:
        rentabilidad = ((capital_actual - capital_inicial) / capital_inicial) * 100.0
    else:
        rentabilidad = 0.0

    sum_rentabilidad += rentabilidad

    resumen_datos.append({
        "Estrategia": nombre,
        "Inicio": fecha_inicio,
        "Cierre": fecha_cierre,
        "Días": dias_acumulados,
        "Inicial": formato_moneda_latino(capital_inicial),
        "Actual": formato_moneda_latino(capital_actual),
        "Rentab (%)": f"{'+' if rentabilidad >= 0 else ''}{rentabilidad:.2f}%"
    })

    # Guardar datos limpios para el gráfico de barras
    datos_grafico.append({
        "Estrategia": nombre.replace("Bot ", ""),
        "Rentabilidad (%)": round(rentabilidad, 2)
    })

# Fila de Promedio en la tabla
promedio_rentabilidad = sum_rentabilidad / len(archivos_bots) if archivos_bots else 0.0
resumen_datos.append({
    "Estrategia": "PROMEDIO",
    "Inicio": "-",
    "Cierre": "-",
    "Días": "-",
    "Inicial": "-",
    "Actual": "-",
    "Rentab (%)": f"{'+' if promedio_rentabilidad >= 0 else ''}{promedio_rentabilidad:.2f}%"
})

df_resumen = pd.DataFrame(resumen_datos)
st.dataframe(df_resumen, use_container_width=True, hide_index=True)

# Gráfico de barras interactivo de rentabilidad
st.markdown("### 📈 Comparativa de Rentabilidad (%)")
df_chart = pd.DataFrame(datos_grafico).set_index("Estrategia")
st.bar_chart(df_chart)
