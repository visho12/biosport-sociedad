import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime
import plotly.graph_objects as go

# 1. Configuración de página
st.set_page_config(page_title="Bio Sport - Evaluaciones", page_icon="⚡", layout="centered")

# 2. Función de conexión ultra-segura
def conectar_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    # Intentamos leer la llave de los Secretos de Streamlit
    try:
        # Dentro de la función conectar_sheets:
creds_info = json.loads(st.secrets["google_credentials"], strict=False)
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"⚠️ Error crítico con la llave JSON: {e}")
        return None

# --- LAS FUNCIONES DE GRÁFICOS SIGUEN IGUAL ---
def crear_radar(dict_puntos):
    categories = list(dict_puntos.keys())
    valores = list(dict_puntos.values())
    valores += valores[:1]
    categories += categories[:1]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=valores, theta=categories, fill='toself', line_color='#1E90FF'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), showlegend=False, height=400)
    return fig

def crear_velocimetro(titulo, valor, min_val, max_val, z_roja, z_ama, z_ver):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = valor, title = {'text': titulo},
        gauge = {'axis': {'range': [min_val, max_val]}, 'bar': {'color': "black"},
                 'steps': [{'range': z_roja, 'color': "#ff4b4b"}, {'range': z_ama, 'color': "#ffa500"}, {'range': z_ver, 'color': "#00cc96"}]}))
    fig.update_layout(height=220)
    return fig

# --- LOGO ---
st.image("logo.png", width=200) # Ajustado para que no falle si no hay columnas

# --- FORMULARIO ---
with st.form("evaluacion_form"):
    st.write("### 📝 Datos del Atleta")
    nombre = st.text_input("Nombre completo")
    peso = st.number_input("Peso (kg)", min_value=1.0)
    imtp = st.number_input("IMTP (N)")
    sj = st.number_input("SJ (cm)")
    cmj = st.number_input("CMJ (cm)")
    aduc = st.number_input("Aductores (N)")
    abduc = st.number_input("Abductores (N)")
    
    enviar = st.form_submit_button("📊 GUARDAR Y VER REPORTE")

if enviar:
    if nombre and peso > 0:
        # Intentar conexión
        cliente = conectar_sheets()
        if cliente:
            try:
                # OJO: Aquí es donde suele fallar. El nombre debe ser EXACTO.
                hoja = cliente.open("BioSport_BD").sheet1
                fecha = datetime.now().strftime("%d/%m/%Y")
                hoja.append_row([fecha, nombre, peso, imtp, sj, cmj, aduc, abduc])
                st.success("✅ Guardado correctamente en Google Sheets")
                
                # CÁLCULOS Y GRÁFICOS (Solo si guarda)
                f_rel = imtp/peso
                st.plotly_chart(crear_velocimetro("Fuerza Rel.", f_rel, 0, 60, [0,30], [30,40], [40,60]))
                st.plotly_chart(crear_radar({"Fuerza": f_rel/6, "Salto": sj/5, "Ratio": (aduc/abduc)*5 if abduc>0 else 0}))
                
            except Exception as e:
                st.error(f"❌ Error en la planilla: {e}")
                st.info("Revisa: 1. Que la planilla se llame BioSport_BD. 2. Que la compartiste con el correo del JSON.")
    else:
        st.warning("Escribe el nombre y el peso.")
