import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

st.set_page_config(page_title="Bio Sport Pro", page_icon="⚡", layout="centered")

# --- MEMORIA DE LA APP (Clave para que el informe no desaparezca) ---
if "informe_actual" not in st.session_state:
    st.session_state.informe_actual = None

# --- CONEXIÓN Y FUNCIONES ---
@st.cache_resource
def conectar_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_info = json.loads(st.secrets["google_credentials"], strict=False)
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        return gspread.authorize(creds)
    except:
        return None

def crear_velocimetro(titulo, valor, min_val, max_val, z_roja, z_ama, z_ver):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = valor,
        title = {'text': titulo, 'font': {'size': 16}},
        gauge = {'axis': {'range': [min_val, max_val]}, 'bar': {'color': "black"},
                 'steps': [{'range': z_roja, 'color': "#ff4b4b"}, {'range': z_ama, 'color': "#ffa500"}, {'range': z_ver, 'color': "#00cc96"}]}
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

# --- CARGAR HISTORIAL ---
cliente = conectar_sheets()
data_historica = pd.DataFrame()
lista_atletas = ["Nuevo Atleta"]

if cliente:
    try:
        hoja = cliente.open("BioSport_BD").sheet1
        registros = hoja.get_all_records()
        if registros:
            data_historica = pd.DataFrame(registros)
            data_historica.columns = [str(c).strip() for c in data_historica.columns]
            if 'Nombre' in data_historica.columns:
                lista_unique = sorted(data_historica['Nombre'].unique().tolist())
                lista_atletas += [n for n in lista_unique if n]
    except:
        pass

# --- INTERFAZ DE INGRESO ---
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
confirmar = st.toggle("Confirmar que los datos son correctos")
btn_guardar = st.button("📊 GUARDAR DATOS", type="primary", use_container_width=True, disabled=not confirmar)

# --- PROCESAMIENTO AL GUARDAR ---
if btn_guardar:
    if nombre and peso > 0:
        f_rel = round(imtp / peso, 1)
        ratio = round(aduc / abduc, 1) if abduc > 0 else 0
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        
        est_fuerza = "Óptimo" if f_rel > 40 else "Medio" if f_rel >= 30 else "Déficit"
        est_ratio = "Simetría" if 0.9 <= ratio <= 1.1 else "Precaución" if 0.8 <= ratio <= 1.2 else "Desbalance"

        eval_previa = None
        if not data_historica.empty and 'Nombre' in data_historica.columns:
            anteriores = data_historica[data_historica['Nombre'] == nombre]
            if not anteriores.empty:
                eval_previa = anteriores.iloc[-1].to_dict() # Convertimos a diccionario para guardarlo

        try:
            hoja = cliente.open("BioSport_BD").sheet1
            hoja.append_row([fecha_actual, nombre, edad, peso, "", imtp, f_rel, est_fuerza, sj, cmj, abalakov, aduc, abduc, ratio, est_ratio, notas])
            
            # --- GUARDAMOS LOS DATOS EN LA MEMORIA ---
            st.session_state.informe_actual = {
                "fecha": fecha_actual, "nombre": nombre, "peso": peso, "imtp": imtp,
                "f_rel": f_rel, "est_fuerza": est_fuerza, "sj": sj, "cmj": cmj, "abalakov": abalakov,
                "aduc": aduc, "abduc": abduc, "ratio": ratio, "est_ratio": est_ratio,
                "notas": notas, "eval_previa": eval_previa
            }
        except Exception as e:
            st.error(f"Error al guardar: {e}")
    else:
        st.error("⚠️ Falta Nombre o Peso.")

# --- GENERACIÓN DEL INFORME (SE MANTIENE VISIBLE) ---
if st.session_state.informe_actual:
    datos = st.session_state.informe_actual
    
    st.markdown("---")
    st.success(f"✅ ¡Evaluación de {datos['nombre']} guardada en Excel!")
    st.header(f"📊 Informe Visual")
    
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.plotly_chart(crear_velocimetro("Fuerza Relativa (N/kg)", datos['f_rel'], 0, 60, [0, 30], [30, 40], [40, 60]), use_container_width=True)
    with col_v2:
        st.plotly_chart(crear_velocimetro("Ratio Cadera", datos['ratio'], 0, 2, [0, 0.8], [0.8, 0.9], [0.9, 1.1]), use_container_width=True)
    
    def norm(v, esc): 
        try: return round(min((float(v)/esc)*10, 10), 1)
        except: return 0
    
    puntos_act = {
        "Fuerza Rel.": norm(datos['f_rel'], 4.5), "SJ": norm(datos['sj'], 5), 
        "CMJ": norm(datos['cmj'], 6), "Abalakov": norm(datos['abalakov'], 7), 
        "Salud Cadera": round(max(0, 10 - abs(1-datos['ratio'])*10), 1)
    }
    
    puntos_prev = None
    if datos['eval_previa']:
        try:
            prev = datos['eval_previa']
            puntos_prev = {
                "Fuerza Rel.": norm(prev.get('Fuerza_Relativa', 0), 4.5), 
                "SJ": norm(prev.get('SJ', 0), 5), "CMJ": norm(prev.get('CMJ', 0), 6), 
                "Abalakov": norm(prev.get('Abalakov', 0), 7),
                "Salud Cadera": round(max(0, 10 - abs(1-float(prev.get('Ratio', 1)))*10), 1)
            }
        except: pass
            
    st.plotly_chart(crear_radar(puntos_act, puntos_prev), use_container_width=True)

    # --- DOCUMENTO DESCARGABLE ---
    texto_informe = f"""======================================
         INFORME DE RENDIMIENTO
              BIO SPORT
======================================
Fecha: {datos['fecha']}
Atleta: {datos['nombre']}
Peso: {datos['peso']} kg

1. PERFIL DE FUERZA
-------------------
IMTP: {datos['imtp']} N
Fuerza Relativa: {datos['f_rel']} N/kg
Estado: {datos['est_fuerza']}

2. PERFIL DE SALTOMETRÍA
------------------------
Squat Jump (SJ): {datos['sj']} cm
Counter Movement Jump (CMJ): {datos['cmj']} cm
Abalakov: {datos['abalakov']} cm

3. SALUD ARTICULAR (CADERA)
---------------------------
Aductores: {datos['aduc']} N
Abductores: {datos['abduc']} N
Ratio (Ad/Ab): {datos['ratio']}
Estado: {datos['est_ratio']}

OBSERVACIONES:
{datos['notas'] if datos['notas'] else "Sin observaciones en esta sesión."}
======================================"""

    st.download_button(
        label="📥 DESCARGAR INFORME COMO ARCHIVO",
        data=texto_informe,
        file_name=f"BioSport_Informe_{datos['nombre'].replace(' ', '_')}.txt",
        mime="text/plain"
    )
