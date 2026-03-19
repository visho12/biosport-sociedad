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

# 3. Funciones Visuales (Velocímetros y Radar)
def crear_velocimetro(titulo, valor, min_val, max_val, z_roja, z_ama, z_ver):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = valor,
        title = {'text': titulo, 'font': {'size': 16}},
        gauge = {
            'axis': {'range': [min_val, max_val]},
            'bar': {'color': "black"},
            'steps': [
                {'range': z_roja, 'color': "#ff4b4b"},
                {'range': z_ama, 'color': "#ffa500"},
                {'range': z_ver, 'color': "#00cc96"}
            ],
        }
    ))
    fig.update_layout(height=220, margin=dict(l=30, r=30, t=50, b=20))
    return fig

def crear_radar(puntos_actual, puntos_previo=None):
    categories = list(puntos_actual.keys())
    fig = go.Figure()
    val_act = list(puntos_actual.values())
    val_act += val_act[:1]
    fig.add_trace(go.Scatterpolar(r=val_act, theta=categories + [categories[0]], fill='toself', name='Actual', line_color='#1E90FF'))
    if puntos_previo:
        val_prev = list(puntos_previo.values())
        val_prev += val_prev[:1]
        fig.add_trace(go.Scatterpolar(r=val_prev, theta=categories + [categories[0]], fill='toself', name='Anterior', line_color='rgba(128, 128, 128, 0.4)'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), showlegend=True, height=400)
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
            # LIMPIEZA CRÍTICA: Quitar espacios en blanco de los nombres de columnas
            data_historica.columns = [str(c).strip() for c in data_historica.columns]
            if 'Nombre' in data_historica.columns:
                lista_unique = sorted(data_historica['Nombre'].unique().tolist())
                lista_atletas += [n for n in lista_unique if n]
    except:
        pass

# --- INTERFAZ ---
st.image("logo.png", width=180)
st.title("⚡ Evaluación Bio Sport")

atleta_sel = st.selectbox("🔍 Buscar Atleta", lista_atletas)

st.write("### 📝 Datos del Atleta")
nombre = st.text_input("Nombre completo", value="" if atleta_sel == "Nuevo Atleta" else atleta_sel)

c1, c2 = st.columns(2)
with c1:
    peso = st.number_input("Peso (kg)", min_value=0.0, step=0.1, format="%.1f")
    imtp = st.number_input("IMTP (N)", step=10.0)
    sj = st.number_input("SJ (cm)", step=0.1, format="%.1f")
with c2:
    cmj = st.number_input("CMJ (cm)", step=0.1, format="%.1f")
    abalakov = st.number_input("Abalakov (cm)", step=0.1, format="%.1f")
    edad = st.number_input("Edad", min_value=0, step=1)

st.write("### ⚖️ Dinamometría y Notas")
ca, cb, cc = st.columns([1,1,2])
with ca: aduc = st.number_input("Aductores (N)", step=1.0)
with cb: abduc = st.number_input("Abductores (N)", step=1.0)
with cc: notas = st.text_area("Notas / Observaciones")

st.divider()
st.warning("🔒 **Seguro de Guardado:** Activa para habilitar el botón.")
confirmar = st.toggle("Confirmar que los datos son correctos")

btn_guardar = st.button("📊 GUARDAR Y GENERAR INFORME", type="primary", use_container_width=True, disabled=not confirmar)

if btn_guardar:
    if nombre and peso > 0:
        # CÁLCULOS
        f_rel = round(imtp / peso, 1)
        ratio = round(aduc / abduc, 1) if abduc > 0 else 0
        fecha = datetime.now().strftime("%d/%m/%Y")
        
        # LÓGICA DE ESTADOS
        est_fuerza = "Óptimo" if f_rel > 40 else "Medio" if f_rel >= 30 else "Déficit"
        est_ratio = "Simetría" if 0.9 <= ratio <= 1.1 else "Precaución" if 0.8 <= ratio <= 1.2 else "Desbalance"

        # Buscar evaluación anterior (CON PROTECCIÓN CONTRA KEYERROR)
        eval_previa = None
        if not data_historica.empty and 'Nombre' in data_historica.columns:
            anteriores = data_historica[data_historica['Nombre'] == nombre]
            if not anteriores.empty:
                eval_previa = anteriores.iloc[-1]

        # Guardar en Sheets
        try:
            hoja = cliente.open("BioSport_BD").sheet1
            hoja.append_row([fecha, nombre, edad, peso, "", imtp, f_rel, est_fuerza, sj, cmj, abalakov, aduc, abduc, ratio, est_ratio, notas])
            st.success(f"✅ ¡Evaluación de {nombre} guardada con éxito!")
            
            # --- REPORTE VISUAL ---
            st.markdown("---")
            st.header(f"📊 Informe: {nombre}")
            
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                st.plotly_chart(crear_velocimetro("Fuerza Relativa (N/kg)", f_rel, 0, 60, [0, 30], [30, 40], [40, 60]), use_container_width=True)
            with col_v2:
                st.plotly_chart(crear_velocimetro("Ratio Cadera", ratio, 0, 2, [0, 0.8], [0.8, 0.9], [0.9, 1.1]), use_container_width=True)
            
            # Radar
            def norm(v, esc): 
                try: return round(min((float(v)/esc)*10, 10), 1)
                except: return 0
            
            puntos_act = {"Fuerza Rel.": norm(f_rel, 4.5), "SJ": norm(sj, 5), "CMJ": norm(cmj, 6), "Abalakov": norm(abalakov, 7), "Salud Cadera": round(max(0, 10 - abs(1-ratio)*10), 1)}
            
            puntos_prev = None
            # Solo intentamos crear la sombra gris si las columnas existen en el historial
            if eval_previa is not None:
                try:
                    puntos_prev = {
                        "Fuerza Rel.": norm(eval_previa.get('Fuerza_Relativa', 0), 4.5), 
                        "SJ": norm(eval_previa.get('SJ', 0), 5), 
                        "CMJ": norm(eval_previa.get('CMJ', 0), 6), 
                        "Abalakov": norm(eval_previa.get('Abalakov', 0), 7),
                        "Salud Cadera": round(max(0, 10 - abs(1-float(eval_previa.get('Ratio', 1)))*10), 1)
                    }
                except:
                    puntos_prev = None

            st.plotly_chart(crear_radar(puntos_act, puntos_prev), use_container_width=True)
            
        except Exception as e:
            st.error(f"Error al guardar: {e}")
    else:
        st.error("⚠️ Falta Nombre o Peso.")
