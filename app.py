import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Bio Sport - Evaluaciones", page_icon="⚡", layout="centered")

# --- FUNCIÓN PARA CONECTAR A GOOGLE SHEETS ---
@st.cache_resource
def conectar_sheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # Lee los secretos que guardaste en Streamlit
    creds_dict = json.loads(st.secrets["google_credentials"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client

# --- ENCABEZADO CON LOGO ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
   with col2:
    st.image("logo.png", use_container_width=True)

st.markdown("<h4 style='text-align: center; color: gray;'>Sistema de Evaluación de Rendimiento</h4>", unsafe_allow_html=True)
st.markdown("---")

# --- FORMULARIO ---
with st.expander("📝 INGRESAR DATOS DEL ATLETA", expanded=True):
    st.write("##### Perfil Básico")
    col1, col2 = st.columns(2)
    with col1:
        nombre = st.text_input("Nombre")
        edad = st.number_input("Edad", min_value=10, max_value=100, step=1)
    with col2:
        peso = st.number_input("Peso (kg)", min_value=30.0, max_value=150.0, step=0.1)
        deporte = st.text_input("Deporte / Posición")

    st.markdown("---")
    st.write("##### Datos de Tecnología Garrido")
    imtp = st.number_input("Tirón Isométrico (IMTP) - Newtons", min_value=0.0, step=10.0)
    
    st.write("Saltometría (cm)")
    col_sj, col_cmj, col_aba = st.columns(3)
    with col_sj:
        sj = st.number_input("SJ", min_value=0.0, step=0.1)
    with col_cmj:
        cmj = st.number_input("CMJ", min_value=0.0, step=0.1)
    with col_aba:
        abalakov = st.number_input("Abalakov", min_value=0.0, step=0.1)

    st.write("Dinamometría de Cadera")
    col_ad, col_ab = st.columns(2)
    with col_ad:
        aductores = st.number_input("Aductores", min_value=0.0, step=1.0)
    with col_ab:
        abductores = st.number_input("Abductores", min_value=0.0, step=1.0)

    notas = st.text_area("Notas del Día (Opcional)")

# --- BOTÓN DE CÁLCULO Y GUARDADO ---
st.markdown("<br>", unsafe_allow_html=True)
calcular = st.button("📊 CALCULAR Y GUARDAR RESULTADOS", type="primary", use_container_width=True)

# --- LÓGICA DE RESULTADOS ---
if calcular:
    if peso > 0 and nombre != "":
        # Cálculos
        fuerza_relativa = imtp / peso
        
        # Lógica de estados
        if fuerza_relativa > 40:
            estado_fuerza = "🟢 Óptimo"
        elif 30 <= fuerza_relativa <= 40:
            estado_fuerza = "🟡 Medio"
        else:
            estado_fuerza = "🔴 Déficit"
            
        ratio = 0
        estado_ratio = "-"
        if abductores > 0:
            ratio = aductores / abductores
            if 0.90 <= ratio <= 1.10:
                estado_ratio = "🟢 Simetría"
            elif (0.80 <= ratio < 0.90) or (1.10 < ratio <= 1.20):
                estado_ratio = "🟡 Precaución"
            else:
                estado_ratio = "🔴 Desbalance"

        # --- GUARDAR EN GOOGLE SHEETS ---
        try:
            with st.spinner('Procesando y guardando datos en la base de datos...'):
                cliente = conectar_sheets()
                # MUY IMPORTANTE: El nombre aquí debe ser exactamente el nombre de tu archivo en Google Drive
                hoja = cliente.open("BioSport_BD").sheet1
                
                fecha_actual = datetime.now().strftime("%d-%m-%Y %H:%M")
                
                nueva_fila = [
                    fecha_actual, nombre, edad, peso, deporte, 
                    imtp, round(fuerza_relativa, 2), estado_fuerza, 
                    sj, cmj, abalakov, 
                    aductores, abductores, round(ratio, 2) if abductores > 0 else 0, estado_ratio, 
                    notas
                ]
                hoja.append_row(nueva_fila)
                
            st.success(f"✅ ¡Atleta {nombre} evaluado y guardado en Google Sheets con éxito!")
        except Exception as e:
            st.error(f"❌ Error al guardar en la nube. Revisa que el nombre de la planilla sea exactamente BioSport_BD. Detalle: {e}")

        # --- MOSTRAR INFORME EN PANTALLA ---
        st.markdown("---")
        st.markdown("<h2 style='text-align: center;'>INFORME DEL ATLETA</h2>", unsafe_allow_html=True)
        
        st.write("### 🏋️ Fuerza Relativa (IMTP)")
        color_fuerza = "normal" if "Óptimo" in estado_fuerza else "off" if "Medio" in estado_fuerza else "inverse"
        st.metric(label="Newtons por Kg", value=f"{fuerza_relativa:.2f} N/kg", delta=estado_fuerza, delta_color=color_fuerza)
        
        st.write("### ⚖️ Balance de Cadera")
        if abductores > 0:
            color_ratio = "normal" if "Simetría" in estado_ratio else "off" if "Precaución" in estado_ratio else "inverse"
            st.metric(label="Ratio (Aductores/Abductores)", value=f"{ratio:.2f}", delta=estado_ratio, delta_color=color_ratio)
            col_bar1, col_bar2 = st.columns(2)
            with col_bar1:
                st.info(f"**Aductores:** {aductores} N")
            with col_bar2:
                st.warning(f"**Abductores:** {abductores} N")
    else:
        st.error("⚠️ Es obligatorio ingresar al menos el Nombre y el Peso del atleta.")
