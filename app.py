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
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from PIL import Image as PILImage, ImageDraw

# 1. Configuración
st.set_page_config(page_title="Bio Sport Pro", page_icon="⚡", layout="centered")

# --- MEMORIA DE LA APP ---
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

# Funciones Visuales para Streamlit
def crear_velocimetro(titulo, valor, min_val, max_val, z_roja, z_ama, z_ver):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = valor,
        title = {'text': titulo, 'font': {'size': 16}},
        gauge = {'axis': {'range': [min_val, max_val]}, 'bar': {'color': "black"},
                 'steps': [{'range': z_roja, 'color': "#ff4b4b"}, {'range': z_ama, 'color': "#ffa500"}, {'range': z_ver, 'color': "#00cc96"}]}
    ))
    fig.update_layout(height=220, margin=dict(l=30, r=30, t=50, b=20))
    return fig

def crear_radar_streamlit(puntos_actual, puntos_previo=None):
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

# --- FUNCIONES PARA GENERAR EL PDF ESTILO IMAGEN ---
def dibujar_grafico_barra_color(draw, x, y, ancho, alto, titulo, valor, max_valor):
    colores_barra = [(colors.red, 0, 20), (colors.orange, 20, 40), (colors.yellow, 40, 50), (colors.lightgreen, 50, 70), (colors.darkgreen, 70, 100)]
    for color, inicio, fin in colores_barra:
        x_inicio = x + (inicio / 100) * ancho
        x_fin = x + (fin / 100) * ancho
        pil_color = (int(color.red * 255), int(color.green * 255), int(color.blue * 255))
        draw.rectangle([x_inicio, y, x_fin, y + alto], fill=pil_color)

    pos_x = x + (valor / max_valor) * ancho
    draw.polygon([pos_x, y - 5, pos_x - 5, y - 15, pos_x + 5, y - 15], fill=(0, 0, 139))
    draw.text((pos_x + 10, y - 15), str(valor), fill="black")
    draw.text((x, y + alto + 5), titulo, fill="black")

def dibujar_grafico_arana(draw, x_centro, y_centro, radio_max, puntos_actual, etiquetas):
    num_puntos = len(etiquetas)
    colores_leyenda = [(colors.red, "LIMITADO"), (colors.orange, "REGULAR"), (colors.lightgreen, "ÓPTIMO"), (colors.darkgreen, "SUPERIOR")]
    
    for i, (color, _) in enumerate(colores_leyenda):
        pil_color = (int(color.red * 255), int(color.green * 255), int(color.blue * 255))
        puntos_poligono = []
        for j in range(num_puntos):
            angulo = j * (2 * 3.14159 / num_puntos) - 3.14159 / 2
            radio = (radio_max / 4) * (i + 1)
            px = x_centro + radio * PILImage.math.cos(angulo)
            py = y_centro + radio * PILImage.math.sin(angulo)
            puntos_poligono.append((px, py))
        draw.polygon(puntos_poligono, outline=pil_color)

    puntos_jugador = []
    for j, (etiqueta, valor) in enumerate(puntos_actual.items()):
        angulo = j * (2 * 3.14159 / num_puntos) - 3.14159 / 2
        radio = (float(valor) / 10) * radio_max
        px = x_centro + radio * PILImage.math.cos(angulo)
        py = y_centro + radio * PILImage.math.sin(angulo)
        puntos_jugador.append((px, py))
    draw.polygon(puntos_jugador, outline=(30, 144, 255), fill=(30, 144, 255, 100))

    for j, etiqueta in enumerate(etiquetas):
        angulo = j * (2 * 3.14159 / num_puntos) - 3.14159 / 2
        px = x_centro + (radio_max + 10) * PILImage.math.cos(angulo)
        py = y_centro + (radio_max + 10) * PILImage.math.sin(angulo)
        draw.text((px - 20, py), etiqueta, fill="black")

def generar_pdf_estilo_imagen(datos, puntos_radar, logo_path):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    styles = getSampleStyleSheet()

    # --- ENCABEZADO ---
    try:
        img_logo = PILImage.new('RGBA', (100, 100), (255, 255, 255, 0))
        draw_logo = ImageDraw.Draw(img_logo)
        draw_logo.polygon([(50, 0), (93, 25), (93, 75), (50, 100), (7, 75), (7, 25)], outline=(0, 0, 139), fill=(30, 144, 255))
        draw_logo.text((25, 30), "BIO", fill="white", font_size=20)
        draw_logo.text((15, 60), "SPORT", fill="white", font_size=16)
        
        logo_temp_path = "logo_temp.png"
        img_logo.save(logo_temp_path)
        c.drawImage(logo_temp_path, 1 * cm, height - 3 * cm, width=2*cm, height=2*cm)
    except: pass

    c.setFont("Helvetica-Bold", 16)
    c.drawString(4 * cm, height - 1.5 * cm, "INFORME DE EVALUACIÓN")
    c.setFont("Helvetica", 10)
    c.drawString(4 * cm, height - 2 * cm, "EVALUADOR: Bio Sport Performance")
    
    c.setFillColor(colors.lightgrey)
    c.circle(width - 3 * cm, height - 2.5 * cm, 1 * cm, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.circle(width - 3 * cm, height - 2 * cm, 0.5 * cm, fill=1, stroke=0)
    
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width - 3 * cm, height - 4 * cm, str(datos['nombre']))
    c.setFillColor(colors.darkblue)
    c.rect(width - 4.5 * cm, height - 4.6 * cm, 3 * cm, 0.5 * cm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.drawCentredString(width - 3 * cm, height - 4.5 * cm, str(datos.get('deporte', 'ATLETA')).upper())
    c.setFillColor(colors.black)

    # --- SECCIÓN DE PERFIL ---
    y_perfil = height - 5 * cm
    def dibujar_recuadro_dato(canv, x, y, titulo, valor):
        canv.setFillColor(colors.darkblue)
        canv.rect(x, y, 3 * cm, 0.6 * cm, fill=1, stroke=0)
        canv.setFillColor(colors.white)
        canv.drawCentredString(x + 1.5 * cm, y + 0.1 * cm, titulo)
        canv.setFillColor(colors.white)
        canv.rect(x + 3.2 * cm, y, 2.5 * cm, 0.6 * cm, fill=1, stroke=1)
        canv.setFillColor(colors.black)
        canv.drawCentredString(x + 4.45 * cm, y + 0.1 * cm, str(valor))

    dibujar_recuadro_dato(c, 1 * cm, y_perfil, "EDAD", f"{datos['edad']} años")
    dibujar_recuadro_dato(c, 1 * cm, y_perfil - 0.8 * cm, "PESO", f"{datos['peso']} kg")
    dibujar_recuadro_dato(c, 1 * cm, y_perfil - 1.6 * cm, "FECHA", str(datos['fecha']))

    c.line(1 * cm, height - 7.5 * cm, width - 1 * cm, height - 7.5 * cm)

    # --- SECCIÓN RENDIMIENTO ---
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.black)
    c.rect(1 * cm, height - 8.2 * cm, 4 * cm, 0.6 * cm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.drawCentredString(3 * cm, height - 8.1 * cm, "RENDIMIENTO")
    c.setFillColor(colors.black)

    img_barras = PILImage.new('RGBA', (int(18 * cm), int(6 * cm)), (255, 255, 255, 0))
    draw_barras = ImageDraw.Draw(img_barras)
    
    dibujar_grafico_barra_color(draw_barras, 50, 50, int(14 * cm), 20, "CMJ (Potencia Salto)", datos['cmj'], 80)
    dibujar_grafico_barra_color(draw_barras, 50, 130, int(14 * cm), 20, "FUERZA RELATIVA (IMTP/Kg)", datos['f_rel'], 60)
    
    barras_temp_path = "barras_temp.png"
    img_barras.save(barras_temp_path)
    c.drawImage(barras_temp_path, 1 * cm, height - 12.5 * cm, width=18*cm, height=4*cm)

    # --- SECCIÓN FACTOR DE RIESGO ---
    c.line(1 * cm, height - 13.5 * cm, width - 1 * cm, height - 13.5 * cm)
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.black)
    c.rect(1 * cm, height - 14.2 * cm, 8 * cm, 0.6 * cm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.drawCentredString(5 * cm, height - 14.1 * cm, "PERFIL BIOMECÁNICO")
    c.setFillColor(colors.black)

    img_arana = PILImage.new('RGBA', (int(10 * cm), int(10 * cm)), (255, 255, 255, 0))
    draw_arana = ImageDraw.Draw(img_arana)
    
    # --- 4. PEGAR EL GRÁFICO DE ARAÑA ---
    
    # Baremos de Excelencia (El "10 perfecto")
    MAX_SJ = 50.0        # 50 cm es un salto SJ de élite
    MAX_CMJ = 60.0       # 60 cm es un CMJ de élite
    MAX_ABALAKOV = 70.0  # 70 cm es un Abalakov de élite
    MAX_F_REL = 50.0     # 50 N/kg de fuerza relativa es excelente

    # Mapeo de datos con la escala real
    puntos_radar = {
        "TEST MIRAELI": min((datos['sj'] / MAX_SJ) * 10, 10),
        "TEST WLST": min((datos['cmj'] / MAX_CMJ) * 10, 10),
        "TEST BKO": min((datos['abalakov'] / MAX_ABALAKOV) * 10, 10),
        "TEST PIRAMIDAL": min((datos['f_rel'] / MAX_F_REL) * 10, 10),
        
        # Fórmula de movilidad: 1.0 es perfecto (10 pts). 
        # Cada 0.1 de desbalance le resta 2 puntos.
        "MOVILIDAD": max(0, 10 - abs(1 - datos['ratio']) * 20)
    }
    
    ruta_radar = dibujar_arana_png(puntos_radar, list(puntos_radar.keys()))

    dibujar_grafico_arana(draw_arana, int(5 * cm), int(5 * cm), int(3.5 * cm), puntos_radar_imagen, etiquetas_radar)
    
    arana_temp_path = "arana_temp.png"
    img_arana.save(arana_temp_path)
    c.drawImage(arana_temp_path, 1 * cm, height - 20 * cm, width=8*cm, height=8*cm)
    
    # --- AQUÍ ESTÁ LA SOLUCIÓN AL ERROR DE LA LEYENDA ---
    colores_leyenda_pdf = [
        (colors.red, "DÉFICIT / ALERTA"),
        (colors.orange, "REGULAR"),
        (colors.lightgreen, "ÓPTIMO"),
        (colors.darkgreen, "SUPERIOR")
    ]
    y_leyenda = height - 16 * cm
    x_leyenda = 11 * cm
    c.setFont("Helvetica", 10)
    for color, texto in colores_leyenda_pdf:
        c.setFillColor(color)
        c.rect(x_leyenda, y_leyenda, 0.4 * cm, 0.4 * cm, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.drawString(x_leyenda + 0.6 * cm, y_leyenda + 0.1 * cm, texto)
        y_leyenda -= 0.8 * cm

    # --- OBSERVACIONES ---
    st.markdown("---")
    obs_style = styles["BodyText"]
    obs_text = str(datos['notas']) if datos['notas'] else "Sin observaciones en esta sesión."
    p_obs = Paragraph(f"<b>Observaciones:</b><br/>{obs_text}", obs_style)
    p_obs.wrapOn(c, width - 2 * cm, 4 * cm)
    p_obs.drawOn(c, 1 * cm, height - 25 * cm)

    c.save()
    buffer.seek(0)
    return buffer

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
    deporte = st.text_input("Deporte / Posición")
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
btn_guardar = st.button("📊 GUARDAR Y GENERAR INFORME PDF", type="primary", use_container_width=True, disabled=not confirmar)

# --- PROCESAMIENTO ---
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
                eval_previa = anteriores.iloc[-1].to_dict()

        try:
            hoja = cliente.open("BioSport_BD").sheet1
            hoja.append_row([fecha_actual, nombre, edad, peso, deporte, imtp, f_rel, est_fuerza, sj, cmj, abalakov, aduc, abduc, ratio, est_ratio, notas])
            
            def norm_st(v, esc): return round(min((v/esc)*10, 10), 1)
            puntos_act_st = {"Fuerza Rel.": norm_st(f_rel, 4.5), "SJ": norm_st(sj, 5), "CMJ": norm_st(cmj, 6), "Abalakov": norm_st(abalakov, 7), "Salud Cadera": round(max(0, 10 - abs(1-ratio)*10), 1)}
            
            puntos_prev_st = None
            if eval_previa:
                try: puntos_prev_st = {"Fuerza Rel.": norm_st(eval_previa.get('Fuerza_Relativa', 0), 4.5), "SJ": norm_st(eval_previa.get('SJ', 0), 5), "CMJ": norm_st(eval_previa.get('CMJ', 0), 6), "Abalakov": norm_st(eval_previa.get('Abalakov', 0), 7), "Salud Cadera": round(max(0, 10 - abs(1-float(eval_previa.get('Ratio', 1)))*10), 1)}
                except: pass

            with st.spinner("Generando informe PDF profesional..."):
                buffer_pdf = generar_pdf_estilo_imagen({
                    "fecha": fecha_actual, "nombre": nombre, "peso": peso, "imtp": imtp,
                    "f_rel": f_rel, "est_fuerza": est_fuerza, "sj": sj, "cmj": cmj, "abalakov": abalakov,
                    "aduc": aduc, "abduc": abduc, "ratio": ratio, "est_ratio": est_ratio,
                    "notas": notas, "edad": edad, "deporte": deporte
                }, puntos_act_st, "logo.png")

            st.session_state.informe_actual = {
                "fecha": fecha_actual, "nombre": nombre, "f_rel": f_rel, "ratio": ratio,
                "radar_actual": puntos_act_st, "radar_previo": puntos_prev_st,
                "pdf_buffer": buffer_pdf
            }
        except Exception as e:
            st.error(f"Error al guardar o generar PDF: {e}")
    else:
        st.error("⚠️ Falta Nombre o Peso.")

if st.session_state.informe_actual:
    datos = st.session_state.informe_actual
    
    st.markdown("---")
    st.success(f"✅ ¡Evaluación de {datos['nombre']} guardada y PDF generado!")
    st.header(f"📊 Vista Previa de Rendimiento")
    
    col_v1, col_v2 = st.columns(2)
    with col_v1: st.plotly_chart(crear_velocimetro("Fuerza Relativa (N/kg)", datos['f_rel'], 0, 60, [0, 30], [30, 40], [40, 60]), use_container_width=True)
    with col_v2: st.plotly_chart(crear_velocimetro("Ratio Cadera", datos['ratio'], 0, 2, [0, 0.8], [0.8, 0.9], [0.9, 1.1]), use_container_width=True)
    
    st.plotly_chart(crear_radar_streamlit(datos['radar_actual'], datos['radar_previo']), use_container_width=True)

    st.download_button(
        label="📥 DESCARGAR INFORME PDF PROFESIONAL",
        data=datos['pdf_buffer'],
        file_name=f"BioSport_Informe_{datos['nombre'].replace(' ', '_')}.pdf",
        mime="application/pdf"
    )
