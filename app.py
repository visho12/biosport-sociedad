import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime
import plotly.graph_objects as go

# 1. Configuración de página
st.set_page_config(page_title="Bio Sport - Evaluaciones", page_icon="⚡", layout="centered")

# 2. Función de conexión con manejo de errores limpio
def conectar_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        # El parámetro strict=False ayuda a ignorar caracteres invisibles en el JSON
        creds_info = json.loads(st.secrets["google_credentials"], strict=False)
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"⚠️ Error en la llave JSON de los Secrets: {e}")
        return None

# 3. Funciones para Gráficos
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

# --- INTERFAZ VISUAL ---
st.image("logo.png", width=200)
st.markdown("## Sistema de Evaluación Bio Sport")

with st.form("evaluacion_form"):
    st.write("### 📝 Datos del Atleta")
    col1, col2 = st.columns(2)
    with col1:
        nombre = st.text_input("Nombre completo")
        peso = st.number_input("Peso (kg)", min_value=1.0)
    with col2:
        deporte = st.text_input("Deporte")
        edad = st.number_input("Edad", min_value=5)
    
    st.write("---")
    st.write("### 🏋️ Resultados de Pruebas")
    c1, c2, c3 = st.columns(3)
    with c1:
        imtp = st.number_input("IMTP (N)")
    with c2:
        sj = st.number_input("SJ (cm)")
    with c3:
        cmj = st.number_input("CMJ (cm)")
        
    st.write("### ⚖️ Dinamometría de Cadera")
    ca, cb = st.columns(2)
    with ca:
        aduc = st.number_input("Aductores (N)")
    with cb:
        abduc = st.number_input("Abductores (N)")
    
    enviar = st.form_submit_button("📊 GUARDAR Y GENERAR INFORME", use_container_width=True)

# --- LÓGICA AL PRESIONAR EL BOTÓN ---
if enviar:
    if nombre and peso > 0:
        cliente = conectar_sheets()
        if cliente:
            try:
                # El nombre de la planilla debe ser EXACTO en tu Google Drive
                hoja = cliente.open("BioSport_BD").sheet1
                fecha = datetime.now().strftime("%d/%m/%Y")
                
                # Cálculos
                f_rel = imtp/peso
                ratio = aduc/abduc if abduc > 0 else 0
                
                # Guardar fila
                hoja.append_row([fecha, nombre, peso, imtp, sj, cmj, aduc, abduc, round(f_rel,2), round(ratio,2)])
                st.success(f"✅ ¡Datos de {nombre} guardados con éxito!")
                
                # Mostrar Reporte Visual
                st.markdown("---")
                st.header(f"📊 Informe de Rendimiento")
                
                st.plotly_chart(crear_velocimetro("Fuerza Relativa (N/kg)", f_rel, 0, 60, [0,30], [30,40], [40,60]))
                
                # Normalización para el radar (escala 0-10)
                puntos = {
                    "Fuerza": min((f_rel/45)*10, 10),
                    "Salto SJ": min((sj/50)*10, 10),
                    "Salto CMJ": min((cmj/60)*10, 10),
                    "Balance": max(0, 10 - abs(1-ratio)*10)
                }
                st.plotly_chart(crear_radar(puntos))
                
            except Exception as e:
                st.error(f"❌ Error en la planilla: {e}")
                st.info("Asegúrate de que el archivo se llame BioSport_BD y tenga una pestaña llamada Sheet1.")
    else:
        st.warning("⚠️ Por favor, ingresa al menos el Nombre y el Peso.")
