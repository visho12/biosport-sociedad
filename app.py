import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# 1. Configuración de página
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
    
    # Datos Actuales (Azul)
    val_act = list(puntos_actual.values())
    val_act += val_act[:1]
    fig.add_trace(go.Scatterpolar(r=val_act, theta=categories + [categories[0]], fill='toself', name='Actual', line_color='#1E90FF'))
    
    # Datos Previos (Sombra Gris si existen)
    if puntos_previo:
        val_prev = list(puntos_previo.values())
        val_prev += val_prev[:1]
        fig.add_trace(go.Scatterpolar(r=val_prev, theta=categories + [categories[0]], fill='toself', name='Anterior', line_color='rgba(128, 128, 128, 0.4)'))
    
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), showlegend=True, height=400, title="Perfil de Rendimiento")
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
            data_historica.columns = data_historica.columns.str.strip()
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

st.write("### ⚖️ Dinamometría")
ca, cb = st.columns(2)
with ca: aduc = st.number_input("Aductores (N)", step=1.0)
with cb: abduc = st.number_input("Abductores (N)", step=1.0)

st.divider()
st.warning("🔒 **Seguro de Guardado:** Activa para habilitar el botón.")
confirmar = st.toggle("Confirmar que los datos son correctos")

btn_guardar = st.button("📊 GUARDAR Y GENERAR INFORME", type="primary", use_container_width=True, disabled=not confirmar)

if btn_guardar:
    if nombre and peso > 0:
        # CÁLCULOS (Un decimal)
        f_rel = round(imtp / peso, 1)
        ratio = round(aduc / abduc, 1) if abduc > 0 else 0
        fecha = datetime.now().strftime("%d/%m/%Y")
        
        # Buscar evaluación anterior
        eval_previa = None
        if not data_historica.empty:
            anteriores = data_historica[data_historica['Nombre'] == nombre]
            if not anteriores.empty:
                eval_previa = anteriores.iloc[-1]

        # Guardar en Sheets
        try:
            hoja = cliente.open("BioSport_BD").sheet1
            hoja.append_row([fecha, nombre, edad, peso, "", imtp, f_rel, "", sj, cmj, abalakov, aduc, abduc, ratio, "", ""])
            st.success(f"✅ ¡Datos de {nombre} guardados!")
            
            # --- REPORTE VISUAL (EL QUE TE GUSTABA) ---
            st.markdown("---")
            st.header(f"📊 Informe: {nombre}")
            
            # Velocímetros
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                st.plotly_chart(crear_velocimetro("Fuerza Relativa (N/kg)", f_rel, 0, 60, [0, 30], [30, 40], [40, 60]), use_container_width=True)
            with col_v2:
                st.plotly_chart(crear_velocimetro("Ratio Cadera", ratio, 0, 2, [0, 0.8], [0.8, 0.9], [0.9, 1.1]), use_container_width=True)
            
            # Gráfico de Radar Evolutivo
            def norm(v, esc): return round(min((float(v)/esc)*10, 10), 1)
            
            puntos_act = {
                "Fuerza Rel.": norm(f_rel, 4.5), "SJ": norm(sj, 5), 
                "CMJ": norm(cmj, 6), "Abalakov": norm(abalakov, 7),
                "Salud Cadera": round(max(0, 10 - abs(1-ratio)*10), 1)
            }
            
            puntos_prev = None
            if eval_previa is not None:
                p_f = eval_previa['Fuerza_Relativa']
                p_sj = eval_previa['SJ']
                p_cmj = eval_previa['CMJ']
                p_aba = eval_previa['Abalakov']
                p_rat = eval_previa['Ratio']
                puntos_prev = {
                    "Fuerza Rel.": norm(p_f, 4.5), "SJ": norm(p_sj, 5), 
                    "CMJ": norm(p_cmj, 6), "Abalakov": norm(p_aba, 7),
                    "Salud Cadera": round(max(0, 10 - abs(1-float(p_rat))*10), 1)
                }
            
            st.plotly_chart(crear_radar(puntos_act, puntos_prev), use_container_width=True)
            
            if eval_previa is not None:
                st.info("💡 La sombra gris representa la última evaluación registrada de este atleta.")

        except Exception as e:
            st.error(f"Error al guardar: {e}")
    else:
        st.error("⚠️ Falta Nombre o Peso.")
