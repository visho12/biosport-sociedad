import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime
import plotly.graph_objects as go

# 1. Configuración de página
st.set_page_config(page_title="Bio Sport - Evaluaciones", page_icon="⚡", layout="centered")

# 2. Función de conexión profesional
def conectar_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        # El parámetro strict=False previene el error de "Invalid control character"
        creds_info = json.loads(st.secrets["google_credentials"], strict=False)
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"⚠️ Error en la configuración de la llave: {e}")
        return None

# 3. Funciones para Gráficos (Velocímetros y Radar)
def crear_radar(dict_puntos):
    categories = list(dict_puntos.keys())
    valores = list(dict_puntos.values())
    valores += valores[:1]
    categories += categories[:1]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=valores, theta=categories, fill='toself', line_color='#1E90FF', fillcolor='rgba(30, 144, 255, 0.4)'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), showlegend=False, height=400, title={'text': "🕸️ Perfil de Rendimiento", 'x': 0.5})
    return fig

def crear_velocimetro(titulo, valor, min_val, max_val, z_roja, z_ama, z_ver):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = valor, title = {'text': titulo, 'font': {'size': 16}},
        gauge = {'axis': {'range': [min_val, max_val]}, 'bar': {'color': "black"},
                 'steps': [{'range': z_roja, 'color': "#ff4b4b"}, {'range': z_ama, 'color': "#ffa500"}, {'range': z_ver, 'color': "#00cc96"}]}))
    fig.update_layout(height=220, margin=dict(l=30, r=30, t=50, b=20))
    return fig

# --- INTERFAZ VISUAL ---
st.image("logo.png", width=200)
st.markdown("## Sistema de Evaluación Bio Sport")

with st.form("evaluacion_completa"):
    st.write("### 📝 Datos del Atleta")
    c1, c2 = st.columns(2)
    with c1:
        nombre = st.text_input("Nombre completo")
        peso = st.number_input("Peso (kg)", min_value=1.0, step=0.1)
    with c2:
        deporte = st.text_input("Deporte / Posición")
        edad = st.number_input("Edad", min_value=5, step=1)
    
    st.write("---")
    st.write("### 🚀 Saltometría y Fuerza")
    f1, f2, f3 = st.columns(3)
    with f1:
        imtp = st.number_input("IMTP (N)", step=10.0)
        sj = st.number_input("SJ (cm)", step=0.1)
    with f2:
        cmj = st.number_input("CMJ (cm)", step=0.1)
        abalakov = st.number_input("Abalakov (cm)", step=0.1)
    with f3:
        notas = st.text_area("Notas / Observaciones")

    st.write("### ⚖️ Dinamometría de Cadera")
    ca, cb = st.columns(2)
    with ca:
        aduc = st.number_input("Aductores (N)", step=1.0)
    with cb:
        abduc = st.number_input("Abductores (N)", step=1.0)
    
    enviar = st.form_submit_button("📊 GUARDAR Y GENERAR INFORME", use_container_width=True)

# --- LÓGICA DE PROCESAMIENTO ---
if enviar:
    if nombre and peso > 0:
        cliente = conectar_sheets()
        if cliente:
            try:
                hoja = cliente.open("BioSport_BD").sheet1
                fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
                
                # Cálculos
                f_rel = imtp / peso
                ratio = aduc / abduc if abduc > 0 else 0
                
                # Lógica de estados para el Excel
                est_fuerza = "Óptimo" if f_rel > 40 else "Medio" if f_rel >= 30 else "Déficit"
                est_ratio = "Simetría" if 0.9 <= ratio <= 1.1 else "Precaución" if 0.8 <= ratio <= 1.2 else "Desbalance"

                # Guardar fila completa en Sheets
                nueva_fila = [
                    fecha, nombre, edad, peso, deporte, 
                    imtp, round(f_rel, 2), est_fuerza,
                    sj, cmj, abalakov, 
                    aduc, abduc, round(ratio, 2), est_ratio, 
                    notas
                ]
                hoja.append_row(nueva_fila)
                st.success(f"✅ ¡Evaluación de {nombre} guardada con éxito en BioSport_BD!")
                
                # --- REPORTE VISUAL ---
                st.markdown("---")
                st.header(f"📊 Informe: {nombre}")
                
                # Velocímetros
                col_v1, col_v2 = st.columns(2)
                with col_v1:
                    st.plotly_chart(crear_velocimetro("Fuerza Relativa (N/kg)", f_rel, 0, 60, [0, 30], [30, 40], [40, 60]), use_container_width=True)
                with col_v2:
                    st.plotly_chart(crear_velocimetro("Ratio Cadera (Ad/Ab)", ratio, 0, 2, [0, 0.8], [0.8, 0.9], [0.9, 1.1]), use_container_width=True)
                
                # Gráfico de Radar
                puntos_radar = {
                    "Fuerza Rel.": min((f_rel/45)*10, 10),
                    "SJ (Salto)": min((sj/50)*10, 10),
                    "CMJ (Salto)": min((cmj/60)*10, 10),
                    "Abalakov": min((abalakov/70)*10, 10),
                    "Salud Cadera": max(0, 10 - abs(1-ratio)*10)
                }
                st.plotly_chart(crear_radar(puntos_radar), use_container_width=True)
                
                st.info("💡 **Tip:** Toma una captura de pantalla de este reporte para enviárselo al deportista por WhatsApp.")

            except Exception as e:
                st.error(f"❌ Error al escribir en la planilla: {e}")
    else:
        st.warning("⚠️ El nombre y el peso son obligatorios para calcular.")
