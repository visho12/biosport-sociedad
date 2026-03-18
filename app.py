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

# --- FUNCIÓN PARA EL GRÁFICO DE ARAÑA (RADAR) ---
def crear_radar(dict_puntos):
    categories = list(dict_puntos.keys())
    valores = list(dict_puntos.values())
    
    # Cerramos el círculo del radar volviendo al primer punto
    valores += valores[:1]
    categories += categories[:1]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=valores,
        theta=categories,
        fill='toself',
        name='Perfil Atleta',
        line_color='#1E90FF',
        fillcolor='rgba(30, 144, 255, 0.4)'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 10])
        ),
        showlegend=False,
        height=450,
        title={'text': "🕸️ Perfil de Rendimiento (Escala 0-10)", 'x': 0.5}
    )
    return fig

# --- FUNCIÓN PARA EL VELOCÍMETRO ---
def crear_velocimetro(titulo, valor, min_val, max_val, zona_roja, zona_amarilla, zona_verde):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = valor,
        title = {'text': titulo, 'font': {'size': 16}},
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
    fig.update_layout(height=220, margin=dict(l=30, r=30, t=50, b=20))
    return fig

# --- ENCABEZADO ---
col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
with col_logo2:
    st.image("logo.png", use_container_width=True)

st.markdown("<h4 style='text-align: center; color: gray;'>Sistema de Evaluación Bio Sport</h4>", unsafe_allow_html=True)
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
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        imtp = st.number_input("IMTP (Newtons)", min_value=0.0, step=10.0)
        sj = st.number_input("SJ (cm)", min_value=0.0, step=0.1)
    with col_f2:
        cmj = st.number_input("CMJ (cm)", min_value=0.0, step=0.1)
        abalakov = st.number_input("Abalakov (cm)", min_value=0.0, step=0.1)

    st.write("---")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        aduc = st.number_input("Aductores (N)", min_value=0.0, step=1.0)
    with col_c2:
        abduc = st.number_input("Abductores (N)", min_value=0.0, step=1.0)

# --- PROCESAMIENTO ---
if st.button("📊 GENERAR INFORME Y GUARDAR", type="primary", use_container_width=True):
    if nombre and peso > 0:
        # Cálculos de rendimiento
        fuerza_rel = imtp / peso
        ratio = aduc / abduc if abduc > 0 else 0
        
        # Normalización a escala 0-10 para el Radar (Basado en tus criterios de Bio Sport)
        puntos_sj = min((sj / 50) * 10, 10)
        puntos_cmj = min((cmj / 60) * 10, 10)
        puntos_aba = min((abalakov / 70) * 10, 10)
        puntos_fuerza = min((fuerza_rel / 45) * 10, 10)
        # El ratio es mejor cerca de 1.0
        puntos_ratio = max(0, 10 - abs(1 - ratio) * 10)

        perfil_datos = {
            "SJ (Potencia)": puntos_sj,
            "CMJ (Elasticidad)": puntos_cmj,
            "Abalakov": puntos_aba,
            "Fuerza Rel.": puntos_fuerza,
            "Ratio Cadera": puntos_ratio
        }

        # Guardar en Sheets
        try:
            cliente = conectar_sheets()
            hoja = cliente.open("BioSport_BD").sheet1
            fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
            hoja.append_row([fecha, nombre, edad, peso, deporte, imtp, round(fuerza_rel, 2), sj, cmj, abalakov, aduc, abduc, round(ratio, 2)])
            st.success("✅ Datos guardados y perfil generado")
        except:
            st.error("Error al conectar con la base de datos.")

        # --- SECCIÓN VISUAL ---
        st.markdown("---")
        st.header(f"📊 Reporte: {nombre}")
        
        # Fila 1: Velocímetros
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.plotly_chart(crear_velocimetro("Fuerza Rel. (N/kg)", fuerza_rel, 0, 60, [0, 30], [30, 40], [40, 60]), use_container_width=True)
        with col_g2:
            st.plotly_chart(crear_velocimetro("Ratio Cadera", ratio, 0, 2, [0, 0.8], [0.8, 0.9], [0.9, 1.1]), use_container_width=True)

        # Fila 2: Gráfico de Araña (Centro)
        st.plotly_chart(crear_radar(perfil_datos), use_container_width=True)
        
        st.info("📌 **Nota:** El gráfico de araña muestra el equilibrio del atleta. Un área más grande y circular indica un atleta más completo.")
    else:
        st.warning("⚠️ Completa el nombre y el peso.")
