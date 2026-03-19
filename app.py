import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# 1. Configuración
st.set_page_config(page_title="Bio Sport Pro", page_icon="⚡", layout="centered")

# 2. Conexión a Base de Datos
@st.cache_resource
def conectar_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_info = json.loads(st.secrets["google_credentials"], strict=False)
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        return gspread.authorize(creds)
    except:
        return None

# 3. Funciones Visuales
def crear_radar(puntos_actual, puntos_previo=None):
    categories = list(puntos_actual.keys())
    fig = go.Figure()
    # Datos Actuales
    val_act = list(puntos_actual.values())
    val_act += val_act[:1]
    fig.add_trace(go.Scatterpolar(r=val_act, theta=categories + [categories[0]], fill='toself', name='Actual', line_color='#1E90FF'))
    
    # Datos Previos (si existen)
    if puntos_previo:
        val_prev = list(puntos_previo.values())
        val_prev += val_prev[:1]
        fig.add_trace(go.Scatterpolar(r=val_prev, theta=categories + [categories[0]], fill='toself', name='Anterior', line_color='rgba(128, 128, 128, 0.5)'))
    
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), showlegend=True, height=400)
    return fig

# --- LÓGICA DE BÚSQUEDA ---
cliente = conectar_sheets()
data_historica = pd.DataFrame()
if cliente:
    try:
        hoja = cliente.open("BioSport_BD").sheet1
        data_historica = pd.DataFrame(hoja.get_all_records())
    except:
        pass

# --- INTERFAZ ---
st.image("logo.png", width=180)
st.title("⚡ Evaluación Evolutiva")

# Buscador de Atleta Existente
lista_atletas = ["Nuevo Atleta"]
if not data_historica.empty:
    lista_atletas += sorted(data_historica['Nombre'].unique().tolist())

atleta_sel = st.selectbox("🔍 Seleccionar Atleta o Crear Nuevo", lista_atletas)

with st.form("form_eval"):
    nombre = st.text_input("Nombre", value="" if atleta_sel == "Nuevo Atleta" else atleta_sel)
    c1, c2 = st.columns(2)
    with c1:
        peso = st.number_input("Peso (kg)", min_value=1.0, step=0.1)
        imtp = st.number_input("IMTP (N)", step=10.0)
    with c2:
        sj = st.number_input("SJ (cm)", step=0.1)
        cmj = st.number_input("CMJ (cm)", step=0.1)
    
    ca, cb = st.columns(2)
    with ca: aduc = st.number_input("Aductores (N)", step=1.0)
    with cb: abduc = st.number_input("Abductores (N)", step=1.0)
    
    enviar = st.form_submit_button("📊 GUARDAR Y COMPARAR")

if enviar:
    if nombre and peso > 0:
        f_rel = round(imtp / peso, 1)
        ratio = round(aduc / abduc, 1) if abduc > 0 else 0
        fecha = datetime.now().strftime("%d/%m/%Y")
        
        # Buscar evaluación anterior
        eval_previa = None
        if not data_historica.empty:
            anteriores = data_historica[data_historica['Nombre'] == nombre]
            if not anteriores.empty:
                eval_previa = anteriores.iloc[-1] # Tomamos la última registrada

        # Guardar en Sheets
        if cliente:
            try:
                hoja.append_row([fecha, nombre, 0, peso, "", imtp, f_rel, "", sj, cmj, 0, aduc, abduc, ratio, "", ""])
                st.success(f"✅ ¡Datos guardados! Evolución procesada.")
            except: st.error("Error al guardar.")

        # --- REPORTE COMPARATIVO ---
        st.header(f"📈 Evolución: {nombre}")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            delta_f = round(f_rel - float(eval_previa['Fuerza_Relativa']), 1) if eval_previa is not None else None
            st.metric("Fuerza Relativa", f"{f_rel} N/kg", delta=delta_f)
        with col_m2:
            delta_r = round(ratio - float(eval_previa['Ratio']), 1) if eval_previa is not None else None
            st.metric("Ratio Cadera", f"{ratio}", delta=delta_r)

        # Gráfico Radar con Comparativa
        puntos_act = {"Fuerza": min((f_rel/4.5), 10), "SJ": min((sj/5), 10), "CMJ": min((cmj/6), 10), "Balance": max(0, 10 - abs(1-ratio)*10)}
        puntos_prev = None
        if eval_previa is not None:
            p_f = float(eval_previa['Fuerza_Relativa'])
            p_sj = float(eval_previa['SJ'])
            p_cmj = float(eval_previa['CMJ'])
            p_rat = float(eval_previa['Ratio'])
            puntos_prev = {"Fuerza": min((p_f/4.5), 10), "SJ": min((p_sj/5), 10), "CMJ": min((p_cmj/6), 10), "Balance": max(0, 10 - abs(1-p_rat)*10)}
        
        st.plotly_chart(crear_radar(puntos_act, puntos_prev), use_container_width=True)
        st.info("💡 La sombra gris representa la evaluación anterior del atleta.")
