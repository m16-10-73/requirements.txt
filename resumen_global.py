import os
import json
import streamlit as st

st.set_page_config(
    page_title="Inspección de Bitácoras",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 Inspector de Estructuras JSON (Sin alterar datos)")

archivos_bots = [
    {"Nombre": "Bot Dinámico", "Archivo": "bitacora_dinamica.json"},
    {"Nombre": "Bot Valoris", "Archivo": "bitacora.valoris.json"},
    {"Nombre": "Bot Emergente", "Archivo": "bitacora_emerging.json"},
    {"Nombre": "Bot Eventos", "Archivo": "bitacora_eventos.json"}
]

for bot in archivos_bots:
    st.subheader(f"Estrategia: {bot['Nombre']} (`{bot['Archivo']}`)")
    
    if os.path.exists(bot["Archivo"]):
        try:
            with open(bot["Archivo"], "r", encoding="utf-8") as f:
                data = json.load(f)
                st.json(data) # Muestra el contenido exacto desplegable en pantalla
        except Exception as e:
            st.error(f"Error leyendo el archivo: {e}")
    else:
      st.warning(f"El archivo `{bot['Archivo']}` no se encuentra en el directorio.")
