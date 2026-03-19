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

# 4. Lógica de Datos Históricos
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
st.title("⚡ Evaluación Bio Sport")

# Selector de Atleta
lista_atletas = ["Nuevo Atleta"]
if not data_historica.empty:
    lista_atletas += sorted(data_historica['Nombre'].unique().tolist())

atleta_sel = st.selectbox("🔍 Buscar Atleta", lista_atletas)

# SEGURO CONTRA ENTER: Usamos columnas y inputs normales fuera de un 'st.form' 
# para tener más control, o un form con un botón de validación.
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

st.write("### ⚖️ Dinamometría")
ca, cb = st.columns(2)
with ca: aduc = st.number_input("Aductores (N)", step=1.0)
with cb: abduc = st.number_input("Abductores (N)", step=1.0)

st.write("---")
# --- EL SEGURO DE VIDA ---
st.warning("🔒 **Seguro de Guardado:** Activa el interruptor para habilitar el botón.")
confirmar = st.toggle("Confirmar que los datos son correctos")

# El botón solo se activa si 'confirmar' es True
btn_guardar = st.button("📊 GUARDAR Y GENERAR INFORME", type="primary", use_container_width=True, disabled=not confirmar)

if btn_guardar:
    if nombre and peso > 0:
        # Cálculos con un decimal
        f_rel = round(imtp / peso, 1)
        ratio = round(aduc / abduc, 1) if abduc > 0 else 0
        fecha = datetime.now().strftime("%d/%m/%Y")
        
        # Buscar previa
        eval_previa = None
        if not data_historica.empty:
            anteriores = data_historica[data_historica['Nombre'] == nombre]
            if not anteriores.empty:
                eval_previa = anteriores.iloc[-1]

        # Guardar en Sheets
        try:
            hoja.append_row([fecha, nombre, edad, peso, "", imtp, f_rel, "", sj, cmj, abalakov, aduc, abduc, ratio, "", ""])
            st.success(f"✅ ¡Datos de {nombre} guardados!")
            
            # --- MOSTRAR MÉTRICAS ---
            st.divider()
            m1, m2 = st.columns(2)
            with m1:
                diff_f = round(f_rel - float(eval_previa['Fuerza_Relativa']), 1) if eval_previa is not None else None
                st.metric("Fuerza Relativa", f"{f_rel} N/kg", delta=diff_f)
            with m2:
                diff_r = round(ratio - float(eval_previa['Ratio']), 1) if eval_previa is not None else None
                st.metric("Ratio Cadera", f"{ratio}", delta=diff_r)

            # Radar Comparativo (Solo un decimal en los puntos)
            def normalizar(v, escala): return round(min((v/escala)*10, 10), 1)
            
            puntos_act = {
                "Fuerza": normalizar(f_rel, 4.5), 
                "SJ": normalizar(sj, 5), 
                "CMJ": normalizar(cmj, 6), 
                "Balance": round(max(0, 10 - abs(1-ratio)*10), 1)
            }
            
            # Mostrar gráfico (puedes reutilizar la función crear_radar anterior)
            # ... (omito la función por brevedad, usa la del código anterior) ...
            
        except Exception as e:
            st.error(f"Error al conectar con Sheets: {e}")
    else:
        st.error("Faltan datos obligatorios (Nombre/Peso)")
