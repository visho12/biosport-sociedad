import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(page_title="Bio Sport - Evaluaciones", page_icon="⚡", layout="centered")

# --- FUNCIÓN CONECTAR A GOOGLE SHEETS ---
@st.cache_resource
def conectar_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["google_credentials"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client

# --- FUNCIÓN PARA CREAR GRÁFICO DE VELOCÍMETRO ---
def crear_velocimetro(titulo, valor, min_val, max_val, zona_roja, zona_amarilla, zona_verde):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = valor,
        title = {'text': titulo, 'font': {'size': 18}},
        gauge = {
            'axis': {'range': [min_val, max_val]},
            'bar': {'color': "black"},
            'steps': [
                {'range': zona_roja, 'color': "#ff4b4b"},
                {'range': zona_amarilla, 'color': "#ffa500"},
                {'range': zona_verde, 'color': "#00cc96"}
            ],
        }
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
    return fig

# --- ENCABEZADO CON LOGO ---
col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
with col_logo2:
    st.image("logo.png", use_container_width=True)

st.markdown("<h4 style='text-align: center; color: gray;'>Sistema de Evaluación de Rendimiento</h4>", unsafe_allow_html=True)
st.markdown("---")

# --- FORMULARIO ---
with st.expander("📝 REGISTRO DE EVALUACIÓN", expanded=True):
    col_a, col_b = st.columns(2)
    with col_a:
        nombre = st.text_input("Nombre del Atleta")
        peso = st.number_input("Peso (kg)", min_value=1.0, step=0.1)
    with col_b:
        deporte = st.text_input("Deporte")
        edad = st.number_input("Edad", min_value=5, step=1)

    st.write("---")
    st.write("**Datos de Fuerza y Saltos**")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        imtp = st.number_input("IMTP (Newtons)", min_value=0.0, step=10.0)
        sj = st.number_input("SJ (cm)", min_value=0.0, step=0.1)
    with col_f2:
        cmj = st.number_input("CMJ (cm)", min_value=0.0, step=0.1)
        abalakov = st.number_input("Abalakov (cm)", min_value=0.0, step=0.1)

    st.write("**Dinamometría Cadera**")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        aduc = st.number_input("Aductores (N)", min_value=0.0, step=1.0)
    with col_c2:
        abduc = st.number_input("Abductores (N)", min_value=0.0, step=1.0)

# --- PROCESAMIENTO ---
if st.button("📊 GENERAR INFORME Y GUARDAR", type="primary", use_container_width=True):
    if nombre and peso > 0:
        # Cálculos Lógicos
        fuerza_rel = imtp / peso
        ratio = aduc / abduc if abduc > 0 else 0
        promedio_saltos = (sj + cmj + abalakov) / 3

        # Guardar en Sheets
        try:
            cliente = conectar_sheets()
            hoja = cliente.open("BioSport_BD").sheet1
            fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
            hoja.append_row([fecha, nombre, edad, peso, deporte, imtp, round(fuerza_rel, 2), sj, cmj, abalakov, aduc, abduc, round(ratio, 2)])
            st.success("✅ Datos guardados en Google Sheets")
        except Exception as e:
            st.error(f"Error al guardar: {e}")

        # --- SECCIÓN DE INFORME VISUAL ---
        st.markdown("---")
        st.header(f"📊 Informe: {nombre}")
        
        # Fila de Gráficos
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            # Gauge de Fuerza Relativa (Roj: <30, Ama: 30-40, Ver: >40)
            fig_fuerza = crear_velocimetro("Fuerza Rel. (N/kg)", fuerza_rel, 0, 60, [0, 30], [30, 40], [40, 60])
            st.plotly_chart(fig_fuerza, use_container_width=True)

        with col_g2:
            # Gauge de Ratio (Rojo: <0.8 o >1.2, Verde: 0.9-1.1)
            fig_ratio = crear_velocimetro("Ratio Cadera", ratio, 0, 2, [0, 0.8], [0.8, 0.9], [0.9, 1.1])
            st.plotly_chart(fig_ratio, use_container_width=True)

        # Resumen de Saltos
        st.subheader("🚀 Rendimiento en Saltos")
        st.write(f"Promedio de Potencia: **{promedio_saltos:.2f} cm**")
        st.progress(min(promedio_saltos/70, 1.0)) # Barra de progreso visual

        st.info("💡 **Consejo:** Puedes sacar una captura de pantalla a este informe para enviárselo al preparador físico.")
    else:
        st.warning("⚠️ Ingresa el nombre y el peso del atleta.")
