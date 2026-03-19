import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# 1. Configuración de página
st.set_page_config(page_title="Bio Sport Pro", page_icon="⚡", layout="centered")

# 2. Función de conexión
@st.cache_resource
def conectar_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_info = json.loads(st.secrets["google_credentials"], strict=False)
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        return gspread.authorize(creds)
    except:
        return None

# 3. Función para Gráfico Radar (Comparativo)
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
        fig.add_trace(go.Scatterpolar(r=val_prev, theta=categories + [categories[0]], fill='toself', name='Anterior', line_color='rgba(128, 128, 128, 0.4)'))
    
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), showlegend=True, height=400, title="Evolución de Rendimiento")
    return fig

# 4. Carga de Datos Históricos
cliente = conectar_sheets()
data_historica = pd.DataFrame()
lista_atletas = ["Nuevo Atleta"]

if cliente:
    try:
        hoja = cliente.open("BioSport_BD").sheet1
        registros = hoja.get_all_records()
        if registros:
            data_historica = pd.DataFrame(registros)
            # Limpiamos nombres de columnas (quitar espacios y poner minúsculas para evitar el KeyError)
            data_historica.columns = data_historica.columns.str.strip()
            if 'Nombre' in data_historica.columns:
                lista_unique = sorted(data_historica['Nombre'].unique().tolist())
                lista_atletas += [n for n in lista_unique if n]
    except Exception as e:
        st.sidebar.error(f"Aviso: No se pudo cargar historial: {e}")

# --- INTERFAZ ---
st.image("logo.png", width=180)
st.title("⚡ Evaluación Bio Sport")

atleta_sel = st.selectbox("🔍 Buscar Atleta", lista_atletas)

st.write("### 📝 Ingreso de Datos")
nombre = st.text_input("Nombre del Atleta", value="" if atleta_sel == "Nuevo Atleta" else atleta_sel)

c1, c2 = st.columns(2)
with c1:
    peso = st.number_input("Peso (kg)", min_value=0.0, step=0.1, format="%.1f")
    imtp = st.number_input("IMTP (N)", step=10.0)
    sj = st.number_input("SJ (cm)", step=0.1, format="%.1f")
with c2:
    cmj = st.number_input("CMJ (cm)", step=0.1, format="%.1f")
    abalakov = st.number_input("Abalakov (cm)", step=0.1, format="%.1f")
    edad = st.number_input("Edad", min_value=0, step=1)

st.write("### ⚖️ Dinamometría de Cadera")
ca, cb = st.columns(2)
with ca: aduc = st.number_input("Aductores (N)", step=1.0)
with cb: abduc = st.number_input("Abductores (N)", step=1.0)

st.divider()
st.warning("🔒 **Seguro de Guardado:** Activa el interruptor para habilitar el botón.")
confirmar = st.toggle("Confirmar que los datos son correctos")

btn_guardar = st.button("📊 GUARDAR Y GENERAR INFORME", type="primary", use_container_width=True, disabled=not confirmar)

if btn_guardar:
    if nombre and peso > 0:
        f_rel = round(imtp / peso, 1)
        ratio = round(aduc / abduc, 1) if abduc > 0 else 0
        fecha = datetime.now().strftime("%d/%m/%Y")
        
        # Buscar evaluación anterior del mismo atleta
        eval_previa = None
        if not data_historica.empty and nombre != "":
            anteriores = data_historica[data_historica['Nombre'] == nombre]
            if not anteriores.empty:
                eval_previa = anteriores.iloc[-1]

        # Guardar en Sheets
        try:
            hoja = cliente.open("BioSport_BD").sheet1
            hoja.append_row([fecha, nombre, edad, peso, "", imtp, f_rel, "", sj, cmj, abalakov, aduc, abduc, ratio, "", ""])
            st.success(f"✅ ¡Datos de {nombre} guardados!")
            
            # --- REPORTE ---
            st.header(f"📈 Informe: {nombre}")
            m1, m2 = st.columns(2)
            with m1:
                diff_f = round(f_rel - float(eval_previa['Fuerza_Relativa']), 1) if eval_previa is not None else None
                st.metric("Fuerza Relativa", f"{f_rel} N/kg", delta=diff_f)
            with m2:
                diff_r = round(ratio - float(eval_previa['Ratio']), 1) if eval_previa is not None else None
                st.metric("Ratio Cadera", f"{ratio}", delta=diff_r)

            # Radar Comparativo
            def norm(v, esc): return round(min((v/esc)*10, 10), 1)
            
            puntos_act = {
                "Fuerza": norm(f_rel, 4.5), "SJ": norm(sj, 5), 
                "CMJ": norm(cmj, 6), "Balance": round(max(0, 10 - abs(1-ratio)*10), 1)
            }
            
            puntos_prev = None
            if eval_previa is not None:
                p_f = float(eval_previa['Fuerza_Relativa'])
                p_sj = float(eval_previa['SJ'])
                p_cmj = float(eval_previa['CMJ'])
                p_rat = float(eval_previa['Ratio'])
                puntos_prev = {
                    "Fuerza": norm(p_f, 4.5), "SJ": norm(p_sj, 5), 
                    "CMJ": norm(p_cmj, 6), "Balance": round(max(0, 10 - abs(1-p_rat)*10), 1)
                }
            
            st.plotly_chart(crear_radar(puntos_act, puntos_prev), use_container_width=True)
            
        except Exception as e:
            st.error(f"Error al guardar: {e}")
    else:
        st.error("⚠️ Falta Nombre o Peso.")
