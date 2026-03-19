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
from reportlab.platypus import Paragraph, Image, Table, TableStyle
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

# Funciones Visuales para la pantalla de Streamlit
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
    # Colores imitando la imagen
    colores = [
        (colors.red, 0, 20),
        (colors.orange, 20, 40),
        (colors.yellow, 40, 50),
        (colors.lightgreen, 50, 70),
        (colors.darkgreen, 70, 100)
    ]
    
    for color, inicio, fin in colores:
        x_inicio = x + (inicio / 100) * ancho
        x_fin = x + (fin / 100) * ancho
        # Convertir colores de reportlab a PIL
        pil_color = (int(color.red * 255), int(color.green * 255), int(color.blue * 255))
        draw.rectangle([x_inicio, y, x_fin, y + alto], fill=pil_color)

    # Dibujar indicador triangular
    pos_x = x + (valor / max_valor) * ancho
    draw.polygon([pos_x, y - 5, pos_x - 5, y - 15, pos_x + 5, y - 15], fill=(0, 0, 139)) # Azul oscuro para "Jugador"

    # Etiqueta de valor
    draw.text((pos_x + 10, y - 15), str(valor), fill="black")

    # Título
    draw.text((x, y + alto + 5), titulo, fill="black")

def dibujar_grafico_arana(draw, x_centro, y_centro, radio_max, puntos_actual, etiquetas):
    num_puntos = len(etiquetas)
    # Dibujar pentágonos concéntricos de colores para leyenda
    colores_leyenda = [
        (colors.red, "LIMITADO"),
        (colors.orange, "REGULAR"),
        (colors.lightgreen, "ÓPTIMO"),
        (colors.darkgreen, "SUPERIOR") # Añadimos un nivel
    ]
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

    # Dibujar polígono del Jugador en azul
    puntos_jugador = []
    for j, (etiqueta, valor) in enumerate(puntos_actual.items()):
        angulo = j * (2 * 3.14159 / num_puntos) - 3.14159 / 2
        radio = (float(valor) / 10) * radio_max
        px = x_centro + radio * PILImage.math.cos(angulo)
        py = y_centro + radio * PILImage.math.sin(angulo)
        puntos_jugador.append((px, py))
    draw.polygon(puntos_jugador, outline=(30, 144, 255), fill=(30, 144, 255, 100)) # Azul aciano con transparencia

    # Dibujar etiquetas de tests
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
        # Recrear logotipo hexagonal azul imitando la imagen
        img_logo = PILImage.new('RGBA', (100, 100), (255, 255, 255, 0))
        draw_logo = ImageDraw.Draw(img_logo)
        draw_logo.polygon([(50, 0), (93, 25), (93, 75), (50, 100), (7, 75), (7, 25)], outline=(0, 0, 139), fill=(30, 144, 255))
        draw_logo.text((35, 30), "ST", fill="white", font_size=24)
        draw_logo.text((10, 60), "FORCE POWER", fill="white", font_size=10)
        
        logo_temp_path = "logo_temp.png"
        img_logo.save(logo_temp_path)
        c.drawImage(logo_temp_path, 1 * cm, height - 3 * cm, width=2*cm, height=2*cm)
    except: pass # Fallback if drawing fails

    c.setFont("Helvetica-Bold", 16)
    c.drawString(4 * cm, height - 1.5 * cm, "INFORME DE EVALUACIÓN")
    c.setFont("Helvetica", 10)
    c.drawString(4 * cm, height - 2 * cm, "EVALUADOR: FP. Andrés Lavanderos")
    
    # Avatar de marcador de posición imitando la imagen
    c.setFillColor(colors.lightgrey)
    c.circle(width - 3 * cm, height - 2.5 * cm, 1 * cm, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.circle(width - 3 * cm, height - 2 * cm, 0.5 * cm, fill=1, stroke=0)
    
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width - 3 * cm, height - 4 * cm, datos['nombre'])
    c.setFillColor(colors.darkblue)
    c.rect(width - 4.5 * cm, height - 4.6 * cm, 3 * cm, 0.5 * cm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.drawCentredString(width - 3 * cm, height - 4.5 * cm, "VOLANTE")
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
        canv.drawCentredString(x + 4.45 * cm, y + 0.1 * cm, valor)

    dibujar_recuadro_dato(c, 1 * cm, y_perfil, "EDAD", f"{datos['edad']} años")
    dibujar_recuadro_dato(c, 1 * cm, y_perfil - 0.8 * cm, "PESO", f"{datos['peso']} kilos")
    dibujar_recuadro_dato(c, 1 * cm, y_perfil - 1.6 * cm, "ESATURA", f"1,69m") # Estatura fija imitando la imagen

    c.line(1 * cm, height - 7.5 * cm, width - 1 * cm, height - 7.5 * cm)

    # --- SECCIÓN RENDIMIENTO ---
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.black)
    c.rect(1 * cm, height - 8.2 * cm, 4 * cm, 0.6 * cm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.drawCentredString(3 * cm, height - 8.1 * cm, "RENDIMIENTO")
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawString(width - 5 * cm, height - 8.1 * cm, "PIE HÁBIL: DERECHO")

    # Generar gráficos de barras coloridas usando Pillow imitando la imagen
    img_barras = PILImage.new('RGBA', (int(18 * cm), int(6 * cm)), (255, 255, 255, 0))
    draw_barras = ImageDraw.Draw(img_barras)
    
    y_barra1 = 50
    y_barra2 = 130
    ancho_barra = int(14 * cm)
    alto_barra = 20
    x_barra = 50

    # Usamos CMJ del usuario. Mapeamos Ratio Cadera al segundo gráfico.
    dibujar_grafico_barra_color(draw_barras, x_barra, y_barra1, ancho_barra, alto_barra, "CMJ", datos['cmj'], 100)
    # Mapeamos Ratio Cadera. Multiplicamos por 50 para que el valor de ~1 esté cerca del centro (50)
    dibujar_grafico_barra_color(draw_barras, x_barra, y_barra2, ancho_barra, alto_barra, "RATIO CADERA (Ad/Ab)", datos['ratio'] * 50, 100)
    
    barras_temp_path = "barras_temp.png"
    img_barras.save(barras_temp_path)
    c.drawImage(barras_temp_path, 1 * cm, height - 12.5 * cm, width=18*cm, height=4*cm)

    # --- SECCIÓN FACTOR DE RIESGO FUNCIONAL ---
    c.line(1 * cm, height - 13.5 * cm, width - 1 * cm, height - 13.5 * cm)
    
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.black)
    c.rect(1 * cm, height - 14.2 * cm, 8 * cm, 0.6 * cm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.drawCentredString(5 * cm, height - 14.1 * cm, "FACTOR DE RIESGO FUNCIONAL")
    c.setFillColor(colors.black)

    # Generar gráfico de araña imitando la imagen usando Pillow
    img_arana = PILImage.new('RGBA', (int(10 * cm), int(10 * cm)), (255, 255, 255, 0))
    draw_arana = ImageDraw.Draw(img_arana)
    
    # Mapeamos los datos de tests de saltos y fuerza al radar imitando las etiquetas de la imagen
    etiquetas_radar_imagen = ["TEST MHPFAKE", "TEST WBLT", "TEST BKBO", "TEST PYRAMIDAL", "MOVILIDAD"]
    
    # Re-mapeamos datos para que el gráfico sea "circular y grande" (grande = mejores puntajes)
    puntos_radar_imagen = {
        "TEST MHPFAKE": min((datos['sj'] / 35) * 10, 10),
        "TEST WBLT": min((datos['cmj'] / 45) * 10, 10),
        "TEST BKBO": min((datos['abalakov'] / 55) * 10, 10),
        "TEST PYRAMIDAL": min((datos['imtp'] / 2500) * 10, 10),
        "MOVILIDAD": round(max(0, 10 - abs(1-datos['ratio'])*10), 1)
    }

    dibujar_grafico_arana(draw_arana, int(5 * cm), int(5 * cm), int(4 * cm), puntos_radar_imagen, etiquetas_radar_imagen)
    
    arana_temp_path = "arana_temp.png"
    img_arana.save(arana_temp_path)
    c.drawImage(arana_temp_path, 1 * cm, height - 20 * cm, width=8*cm, height=8*cm)
    
    # Leyenda imitando la imagen
    y_leyenda = height - 19.5 * cm
    x_leyenda = 10 * cm
    for color, texto in colores_leyenda:
        pil_color = (int(color.red * 255), int(color.green * 255), int(color.blue * 255))
        c.setFillColor(color)
        c.circle(x_leyenda, y_leyenda, 0.15 * cm, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.drawString(x_leyenda + 0.3 * cm, y_leyenda - 0.1 * cm, texto)
        y_leyenda -= 0.6 * cm

    # --- OBSERVACIONES ---
    st.markdown("---")
    st.header("📝 Observaciones")
    obs_style = styles["BodyText"]
    obs_text = datos['notas'] if datos['notas'] else "Sin observaciones en esta sesión."
    p_obs = Paragraph(obs_text, obs_style)
    p_obs.wrapOn(c, width - 4 * cm, 4 * cm)
    p_obs.drawOn(c, 2 * cm, height - 24 * cm)

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

# --- INTERFAZ DE INGRESO ---
st.image("logo.png", width=180) # Logo original de Streamlit
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
btn_guardar = st.button("📊 GUARDAR DATOS Y GENERAR INFORME PDF", type="primary", use_container_width=True, disabled=not confirmar)

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
                eval_previa = anteriores.iloc[-1].to_dict()

        try:
            hoja = cliente.open("BioSport_BD").sheet1
            hoja.append_row([fecha_actual, nombre, edad, peso, "", imtp, f_rel, est_fuerza, sj, cmj, abalakov, aduc, abduc, ratio, est_ratio, notas])
            
            # Normalización para el radar de Streamlit (escala 0-10)
            def norm_streamlit(v, esc): return round(min((v/esc)*10, 10), 1)
            puntos_act_streamlit = {"Fuerza Rel.": norm_streamlit(f_rel, 4.5), "SJ": norm_streamlit(sj, 5), "CMJ": norm_streamlit(cmj, 6), "Abalakov": norm_streamlit(abalakov, 7), "Salud Cadera": round(max(0, 10 - abs(1-ratio)*10), 1)}
            puntos_prev_streamlit = None
            if eval_previa:
                try:
                    puntos_prev_streamlit = {"Fuerza Rel.": norm_streamlit(eval_previa.get('Fuerza_Relativa', 0), 4.5), "SJ": norm_streamlit(eval_previa.get('SJ', 0), 5), "CMJ": norm_streamlit(eval_previa.get('CMJ', 0), 6), "Abalakov": norm_streamlit(eval_previa.get('Abalakov', 0), 7), "Salud Cadera": round(max(0, 10 - abs(1-float(eval_previa.get('Ratio', 1)))*10), 1)}
                except: pass

            # --- GENERAMOS EL INFORME PDF ESTILO IMAGEN ---
            with st.spinner("Generando informe PDF profesional..."):
                buffer_pdf = generar_pdf_estilo_imagen({
                    "fecha": fecha_actual, "nombre": nombre, "peso": peso, "imtp": imtp,
                    "f_rel": f_rel, "est_fuerza": est_fuerza, "sj": sj, "cmj": cmj, "abalakov": abalakov,
                    "aduc": aduc, "abduc": abduc, "ratio": ratio, "est_ratio": est_ratio,
                    "notas": notas, "edad": edad
                }, puntos_act_streamlit, "logo.png") # Usamos el logo original para el PDF

            # --- GUARDAMOS LOS DATOS EN LA MEMORIA ---
            st.session_state.informe_actual = {
                "fecha": fecha_actual, "nombre": nombre, "f_rel": f_rel, "ratio": ratio,
                "radar_actual": puntos_act_streamlit, "radar_previo": puntos_prev_streamlit,
                "pdf_buffer": buffer_pdf
            }
        except Exception as e:
            st.error(f"Error al guardar o generar PDF: {e}")
    else:
        st.error("⚠️ Falta Nombre o Peso.")

# --- GENERACIÓN DEL INFORME (SE MANTIENE VISIBLE) ---
if st.session_state.informe_actual:
    datos = st.session_state.informe_actual
    
    st.markdown("---")
    st.success(f"✅ ¡Evaluación de {datos['nombre']} guardada y PDF generado!")
    st.header(f"📊 Informe Visual (Streamlit)")
    
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.plotly_chart(crear_velocimetro("Fuerza Relativa (N/kg)", datos['f_rel'], 0, 60, [0, 30], [30, 40], [40, 60]), use_container_width=True)
    with col_v2:
        st.plotly_chart(crear_velocimetro("Ratio Cadera", datos['ratio'], 0, 2, [0, 0.8], [0.8, 0.9], [0.9, 1.1]), use_container_width=True)
    
    st.plotly_chart(crear_radar_streamlit(datos['radar_actual'], datos['radar_previo']), use_container_width=True)
    if datos['radar_previo']:
        st.info("💡 La sombra gris representa la última evaluación registrada de este atleta.")

    # --- BOTÓN DE DESCARGA DEL PDF PROFESIONAL ---
    st.download_button(
        label="📥 DESCARGAR INFORME PDF PROFESIONAL (Estilo Imagen)",
        data=datos['pdf_buffer'],
        file_name=f"BioSport_Informe_{datos['nombre'].replace(' ', '_')}.pdf",
        mime="application/pdf"
    )
