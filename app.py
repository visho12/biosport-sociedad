import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from PIL import Image as PILImage, ImageDraw

# ==========================================
# ⚙️ ZONA DE BAREMOS (EL "10 PERFECTO")
# ==========================================
MAX_SJ = 50.0          
MAX_CMJ = 60.0         
MAX_ABALAKOV = 70.0    
MAX_F_REL = 50.0       
MAX_RSI = 3.0          
MAX_CMJ_BARRA = 80.0   
# ==========================================

st.set_page_config(page_title="Bio Sport Pro", page_icon="⚡", layout="centered")

if "informe_actual" not in st.session_state:
    st.session_state.informe_actual = None

# --- CONEXIÓN A SHEETS Y CARGA DE HISTORIAL ---
@st.cache_resource
def conectar_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_info = json.loads(st.secrets["google_credentials"], strict=False)
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        return gspread.authorize(creds)
    except: return None

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
    except: pass

# --- FUNCIONES GRÁFICAS (STREAMLIT) ---
def crear_velocimetro(titulo, valor, min_val, max_val, z_roja, z_ama, z_ver):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = valor, title = {'text': titulo, 'font': {'size': 14}},
        gauge = {'axis': {'range': [min_val, max_val]}, 'bar': {'color': "black"},
                 'steps': [{'range': z_roja, 'color': "#ff4b4b"}, {'range': z_ama, 'color': "#ffa500"}, {'range': z_ver, 'color': "#00cc96"}]}
    ))
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=30, b=10))
    return fig

def crear_radar_streamlit(puntos_actual, puntos_previo=None):
    categories = list(puntos_actual.keys())
    fig = go.Figure()
    
    # Datos Actuales
    val_act = list(puntos_actual.values())
    val_act += val_act[:1]
    fig.add_trace(go.Scatterpolar(r=val_act, theta=categories + [categories[0]], fill='toself', name='Actual', line_color='#1E90FF'))
    
    # Datos Previos (Sombra)
    if puntos_previo:
        val_prev = list(puntos_previo.values())
        val_prev += val_prev[:1]
        fig.add_trace(go.Scatterpolar(r=val_prev, theta=categories + [categories[0]], fill='toself', name='Anterior', line_color='rgba(128, 128, 128, 0.5)'))
        
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), showlegend=True, height=350)
    return fig

# --- MAGIA DEL PDF CON TU PLANTILLA ---
def dibujar_arana_png(puntos_actual, etiquetas, puntos_previo=None):
    size = 400
    img = PILImage.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    x_c, y_c = size//2, size//2
    radio_max = 130
    num_puntos = len(etiquetas)
    
    # Fondo concéntrico
    colores = [(255,0,0), (255,165,0), (0,255,0)]
    for i, color in enumerate(colores):
        poligono = []
        for j in range(num_puntos):
            angulo = j * (2 * 3.14159 / num_puntos) - 3.14159 / 2
            radio = (radio_max / 3) * (i + 1)
            px = x_c + radio * PILImage.math.cos(angulo)
            py = y_c + radio * PILImage.math.sin(angulo)
            poligono.append((px, py))
        draw.polygon(poligono, outline=color, width=2)

    # Polígono Anterior (Gris)
    if puntos_previo:
        poligono_viejo = []
        for j, (etiqueta, valor) in enumerate(puntos_previo.items()):
            angulo = j * (2 * 3.14159 / num_puntos) - 3.14159 / 2
            radio = (float(valor) / 10) * radio_max
            px = x_c + radio * PILImage.math.cos(angulo)
            py = y_c + radio * PILImage.math.sin(angulo)
            poligono_viejo.append((px, py))
        draw.polygon(poligono_viejo, outline=(128, 128, 128, 255), fill=(128, 128, 128, 100), width=2)

    # Polígono Actual (Azul)
    poligono_nuevo = []
    for j, (etiqueta, valor) in enumerate(puntos_actual.items()):
        angulo = j * (2 * 3.14159 / num_puntos) - 3.14159 / 2
        radio = (float(valor) / 10) * radio_max
        px = x_c + radio * PILImage.math.cos(angulo)
        py = y_c + radio * PILImage.math.sin(angulo)
        poligono_nuevo.append((px, py))
    draw.polygon(poligono_nuevo, outline=(30, 144, 255, 255), fill=(30, 144, 255, 120), width=3)
    
    temp_path = "radar_temp.png"
    img.save(temp_path)
    return temp_path

def generar_pdf_plantilla(datos, puntos_radar_actual, puntos_radar_previo=None):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4 
    
    try:
        c.drawImage("plantilla.jpg", 0, 0, width=width, height=height)
    except:
        return None 
        
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.black)
    c.drawCentredString(485, height - 150, str(datos['nombre']).upper())
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.white)
    c.drawCentredString(485, height - 170, str(datos['deporte']).upper())
    
    c.setFont("Helvetica-Bold", 11)
    c.drawString(295, height - 110, f"{datos['edad']} años")
    c.drawString(295, height - 153, f"{datos['peso']} kg")
    c.drawString(295, height - 195, f"{datos['estatura']} m")
    
    def dibujar_marcador(canvas, x_inicio, x_fin, y_barra, valor, valor_max):
        porcentaje = min(max(valor / valor_max, 0), 1)
        x_pos = x_inicio + (x_fin - x_inicio) * porcentaje
        canvas.setFillColor(colors.black)
        canvas.rect(x_pos - 15, y_barra + 10, 30, 15, fill=1, stroke=0) 
        p = canvas.beginPath()
        p.moveTo(x_pos, y_barra)
        p.lineTo(x_pos - 5, y_barra + 10)
        p.lineTo(x_pos + 5, y_barra + 10)
        p.close()
        canvas.drawPath(p, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawCentredString(x_pos, y_barra + 14, str(valor))

    dibujar_marcador(c, 135, 470, height - 340, datos['cmj'], MAX_CMJ_BARRA)
    dibujar_marcador(c, 135, 470, height - 440, datos['rsi'], MAX_RSI)

    ruta_radar = dibujar_arana_png(puntos_radar_actual, list(puntos_radar_actual.keys()), puntos_radar_previo)
    c.drawImage(ruta_radar, 80, height - 760, width=180, height=180, mask='auto')
    
    c.save()
    buffer.seek(0)
    return buffer

# --- INTERFAZ STREAMLIT ---
st.image("logo.png", width=120) 
st.title("⚡ Evaluación Bio Sport")

atleta_sel = st.selectbox("🔍 Buscar Atleta (Historial)", lista_atletas)

st.write("### 📝 Datos del Atleta")
c1, c2, c3 = st.columns(3)
with c1:
    nombre = st.text_input("Nombre", value="" if atleta_sel == "Nuevo Atleta" else atleta_sel)
    deporte = st.text_input("Deporte / Posición", value="Fútbol")
with c2:
    peso = st.number_input("Peso (kg)", min_value=0.0, step=0.1, format="%.1f")
    edad = st.number_input("Edad", min_value=0, step=1)
with c3:
    estatura = st.number_input("Estatura (m)", value=1.75, step=0.01)

st.write("### 🚀 Pruebas de Rendimiento")
f1, f2, f3 = st.columns(3)
with f1:
    imtp = st.number_input("IMTP (Fuerza N)", step=10.0)
    sj = st.number_input("SJ (cm)", step=0.1)
with f2:
    cmj = st.number_input("CMJ (cm)", step=0.1)
    abalakov = st.number_input("Abalakov (cm)", step=0.1)
with f3:
    rsi = st.number_input("RSI Modificado", step=0.01)

st.write("### ⚖️ Dinamometría de Cadera")
ca, cb = st.columns(2)
with ca: aduc = st.number_input("Aductores (N)", step=1.0)
with cb: abduc = st.number_input("Abductores (N)", step=1.0)

st.divider()
confirmar = st.toggle("Confirmar que los datos son correctos")
btn_guardar = st.button("📊 GUARDAR Y GENERAR INFORME", type="primary", use_container_width=True, disabled=not confirmar)

# --- PROCESAMIENTO ---
if btn_guardar:
    if nombre and peso > 0:
        f_rel = round(imtp / peso, 1)
        ratio = round(aduc / abduc, 2) if abduc > 0 else 0
        fecha = datetime.now().strftime("%d/%m/%Y")

        datos_eval = {
            "nombre": nombre, "edad": edad, "peso": peso, "estatura": estatura, 
            "deporte": deporte, "fecha": fecha, "cmj": cmj, "sj": sj, 
            "abalakov": abalakov, "imtp": imtp, "f_rel": f_rel, 
            "rsi": rsi, "ratio": ratio
        }

        # Búsqueda de evaluación previa para la comparativa
        eval_previa = None
        if not data_historica.empty and 'Nombre' in data_historica.columns:
            anteriores = data_historica[data_historica['Nombre'] == nombre]
            if not anteriores.empty:
                eval_previa = anteriores.iloc[-1].to_dict()

        if cliente:
            try:
                hoja = cliente.open("BioSport_BD").sheet1
                # Orden de las columnas. ¡Asegúrate de que en Google Sheets coincida!
                hoja.append_row([fecha, nombre, edad, peso, estatura, deporte, imtp, f_rel, sj, cmj, abalakov, rsi, aduc, abduc, ratio])
                st.success("✅ Guardado en Google Sheets.")
            except: pass

        # Cálculo de los puntos actuales
        puntos_act = {
            "TEST MIRAELI": min((sj / MAX_SJ) * 10, 10),
            "TEST WLST": min((cmj / MAX_CMJ) * 10, 10),
            "TEST BKO": min((abalakov / MAX_ABALAKOV) * 10, 10),
            "TEST PIRAMIDAL": min((f_rel / MAX_F_REL) * 10, 10),
            "MOVILIDAD": round(max(0, 10 - abs(1 - ratio) * 20), 1)
        }
        
        # Cálculo de los puntos históricos (si existen)
        puntos_prev = None
        if eval_previa:
            try:
                # Intenta extraer los datos asumiendo que las columnas del Excel se llaman así
                puntos_prev = {
                    "TEST MIRAELI": min((float(eval_previa.get('SJ', 0)) / MAX_SJ) * 10, 10),
                    "TEST WLST": min((float(eval_previa.get('CMJ', 0)) / MAX_CMJ) * 10, 10),
                    "TEST BKO": min((float(eval_previa.get('Abalakov', 0)) / MAX_ABALAKOV) * 10, 10),
                    "TEST PIRAMIDAL": min((float(eval_previa.get('F_Rel', 0)) / MAX_F_REL) * 10, 10),
                    "MOVILIDAD": round(max(0, 10 - abs(1 - float(eval_previa.get('Ratio', 1))) * 20), 1)
                }
            except: pass

        with st.spinner("Ensamblando PDF comparativo con la plantilla..."):
            pdf_buffer = generar_pdf_plantilla(datos_eval, puntos_act, puntos_prev)

        if pdf_buffer:
            st.session_state.informe_actual = {
                "datos": datos_eval, "pdf": pdf_buffer, "radar_act": puntos_act, "radar_prev": puntos_prev
            }
        else:
            st.error("❌ No se encontró 'plantilla.jpg' en GitHub. Súbela para generar el PDF.")
    else:
        st.error("⚠️ Falta Nombre o Peso.")

# --- MOSTRAR BOTÓN DE DESCARGA Y VISTA WEB ---
if st.session_state.informe_actual:
    d = st.session_state.informe_actual["datos"]
    radar_act = st.session_state.informe_actual["radar_act"]
    radar_prev = st.session_state.informe_actual["radar_prev"]
    
    st.markdown("---")
    st.header(f"📈 Vista Previa Evolutiva: {d['nombre']}")
    
    col1, col2 = st.columns(2)
    with col1: st.plotly_chart(crear_velocimetro("CMJ", d['cmj'], 0, MAX_CMJ_BARRA, [0,30], [30,40], [40,MAX_CMJ_BARRA]), use_container_width=True)
    with col2: st.plotly_chart(crear_velocimetro("RSI", d['rsi'], 0, MAX_RSI, [0,1], [1,1.5], [1.5,MAX_RSI]), use_container_width=True)
    
    # Mostrar Radar Comparativo en web
    st.plotly_chart(crear_radar_streamlit(radar_act, radar_prev), use_container_width=True)
    if radar_prev:
        st.info("💡 La sombra gris representa la evaluación anterior del atleta.")

    st.download_button(
        label="📥 DESCARGAR INFORME OFICIAL (PDF)",
        data=st.session_state.informe_actual["pdf"],
        file_name=f"Informe_Evolutivo_{d['nombre'].replace(' ', '_')}.pdf",
        mime="application/pdf"
    )
