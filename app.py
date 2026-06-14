"""
Bio Sport Pro — Versión 3.5
Fix: data_historica y lista_atletas en session_state para que
se actualicen correctamente en cada rerun tras guardar.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
import math
import os
import json
import gspread
from google.oauth2.service_account import Credentials

# ─────────────────────────────────────────────────────────────
# BAREMOS CIENTÍFICOS DINÁMICOS
# ─────────────────────────────────────────────────────────────
BAREMOS_DEPORTIVOS = {
    "Fútbol":                 {"SJ": 46.0, "CMJ": 56.0, "Abalakov": 66.0, "F_Rel": 35.0, "RSI": 2.6},
    "Básquetbol":             {"SJ": 55.0, "CMJ": 68.0, "Abalakov": 78.0, "F_Rel": 35.0, "RSI": 3.0},
    "Voleibol":               {"SJ": 60.0, "CMJ": 75.0, "Abalakov": 88.0, "F_Rel": 32.0, "RSI": 3.2},
    "General / Recreacional": {"SJ": 40.0, "CMJ": 48.0, "Abalakov": 58.0, "F_Rel": 28.0, "RSI": 2.2},
}

COLUMNAS_SHEETS = [
    "Fecha", "Nombre", "Edad", "Peso_kg", "Estatura_m", "Deporte",
    "IMTP_N", "F_Rel_NKg", "SJ_cm", "CMJ_cm", "Abalakov_cm",
    "RSI_Mod", "Aduc_N", "Abduc_N", "Ratio_AdAb"
]

# ─────────────────────────────────────────────
#  PAGE CONFIG & CSS
# ─────────────────────────────────────────────
st.set_page_config(page_title="Bio Sport Pro", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #0a0e1a; color: #e8eaf0; }
.hero-title { font-size: 2.2rem; font-weight: 900; letter-spacing: -0.5px; color: #ffffff; margin: 0; }
.hero-subtitle { font-size: 0.95rem; color: #7ea8d8; margin: 4px 0 0 0; font-weight: 400; }
.accent { color: #00d4ff; }
.section-card { background: #111827; border: 1px solid #1f2d45; border-radius: 12px; padding: 24px 28px; margin-bottom: 20px; }
.section-title { font-size: 0.75rem; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: #00d4ff; margin-bottom: 16px; }
.metric-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }
.metric-chip { background: #1a2744; border: 1px solid #2a3f6f; border-radius: 10px; padding: 14px 20px; min-width: 130px; flex: 1; text-align: center; }
.metric-chip .val { font-size: 1.7rem; font-weight: 700; color: #00d4ff; line-height: 1; }
.metric-chip .lbl { font-size: 0.72rem; color: #8899bb; margin-top: 4px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; }
.score-badge { background: linear-gradient(135deg, #0f3460, #1a4f8a); border: 2px solid #00d4ff; border-radius: 50%; width: 110px; height: 110px; display: flex; flex-direction: column; align-items: center; justify-content: center; margin: 0 auto 20px auto; }
.score-badge .num { font-size: 2.4rem; font-weight: 900; color: #fff; line-height: 1; }
.score-badge .denom { font-size: 0.8rem; color: #7ea8d8; }
div.stButton > button[kind="primary"] { background: linear-gradient(90deg, #0066cc, #00aaff); color: white; border: none; border-radius: 10px; font-weight: 700; letter-spacing: 0.5px; font-size: 0.95rem; padding: 0.65rem 2rem; transition: opacity 0.2s; }
div.stButton > button[kind="primary"]:hover { opacity: 0.88; }
.stTabs [data-baseweb="tab-list"] { background: #111827; border-radius: 10px; padding: 4px; gap: 4px; border: 1px solid #1f2d45; }
.stTabs [data-baseweb="tab"] { background: transparent; color: #8899bb; border-radius: 8px; font-weight: 600; font-size: 0.85rem; }
.stTabs [aria-selected="true"] { background: #1a2744 !important; color: #00d4ff !important; }
hr { border-color: #1f2d45 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  ESTADO DE SESIÓN
# ─────────────────────────────────────────────
for k, v in {"informe_actual": None, "cache_ver": 0, "_df": None, "_local_rows": []}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
#  GOOGLE SHEETS
# ─────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def conectar_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    try:
        creds_info = json.loads(st.secrets["google_credentials"], strict=False)
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception:
        return None

@st.cache_data(ttl=30, show_spinner=False)
def _fetch_sheets(_ver, _cliente):
    """La clave _ver fuerza recarga cuando se incrementa."""
    if _cliente is None:
        return pd.DataFrame()
    try:
        hoja = _cliente.open("BioSport_BD").sheet1
        registros = hoja.get_all_records()
        if not registros:
            return pd.DataFrame()
        df = pd.DataFrame(registros)
        df.columns = [str(c).strip() for c in df.columns]
        ALIAS = {
            "nombre":"Nombre","fecha":"Fecha","deporte":"Deporte","edad":"Edad",
            "peso":"Peso_kg","Peso":"Peso_kg","estatura":"Estatura_m","Estatura":"Estatura_m",
            "SJ":"SJ_cm","sj":"SJ_cm","CMJ":"CMJ_cm","cmj":"CMJ_cm",
            "Abalakov":"Abalakov_cm","abalakov":"Abalakov_cm",
            "IMTP":"IMTP_N","imtp":"IMTP_N","F_Rel":"F_Rel_NKg","f_rel":"F_Rel_NKg",
            "RSI":"RSI_Mod","rsi":"RSI_Mod","Aduc":"Aduc_N","aduc":"Aduc_N",
            "Abduc":"Abduc_N","abduc":"Abduc_N","Ratio":"Ratio_AdAb","ratio":"Ratio_AdAb",
        }
        df.rename(columns=ALIAS, inplace=True)
        for col in ["Nombre","Fecha","Deporte"]:
            if col not in df.columns: df[col] = ""
        for col in ["Edad","Peso_kg","Estatura_m","IMTP_N","F_Rel_NKg",
                    "SJ_cm","CMJ_cm","Abalakov_cm","RSI_Mod","Aduc_N","Abduc_N","Ratio_AdAb"]:
            if col not in df.columns: df[col] = 0.0
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        return df
    except Exception as ex:
        st.warning(f"Error al cargar historial: {ex}")
        return pd.DataFrame()

def get_df():
    """
    Devuelve el DataFrame combinando:
      1. Datos de Google Sheets (si hay conexión)
      2. Registros guardados localmente en esta sesión (_local_rows)
    Así los atletas ingresados SIN Sheets aparecen igual en el historial.
    """
    if st.session_state["_df"] is None:
        st.session_state["_df"] = _fetch_sheets(st.session_state["cache_ver"], cliente_sheets)

    df_sheets = st.session_state["_df"]

    # Combinar con filas locales de la sesión
    local = st.session_state.get("_local_rows", [])
    if not local:
        return df_sheets

    df_local = pd.DataFrame(local, columns=COLUMNAS_SHEETS)
    # Normalizar tipos numéricos en local
    for col in ["Edad","Peso_kg","Estatura_m","IMTP_N","F_Rel_NKg",
                "SJ_cm","CMJ_cm","Abalakov_cm","RSI_Mod","Aduc_N","Abduc_N","Ratio_AdAb"]:
        df_local[col] = pd.to_numeric(df_local[col], errors="coerce").fillna(0)

    if df_sheets.empty:
        return df_local

    # Evitar duplicar filas que ya llegaron de Sheets
    combined = pd.concat([df_sheets, df_local], ignore_index=True)
    combined = combined.drop_duplicates(subset=["Fecha","Nombre","CMJ_cm"], keep="first")
    return combined


def invalidar_y_recargar():
    """Incrementa versión → próximo get_df() va directo a Sheets."""
    st.session_state["cache_ver"] += 1
    st.session_state["_df"] = None


def guardar_fila(cliente, fila: list) -> bool:
    """
    Guarda en Google Sheets SI hay conexión.
    SIEMPRE guarda en _local_rows de session_state para que
    el historial y el selector de atletas se actualicen de inmediato.
    """
    # Guardar localmente siempre (modo offline o con Sheets)
    st.session_state["_local_rows"].append(fila)
    st.session_state["_df"] = None  # forzar recomposición en próximo get_df()

    # Intentar sincronizar con Sheets
    if cliente is None:
        return False
    try:
        hoja = cliente.open("BioSport_BD").sheet1
        if len(hoja.get_all_values()) == 0:
            hoja.append_row(COLUMNAS_SHEETS)
        hoja.append_row(fila)
        invalidar_y_recargar()  # refrescar desde Sheets para no tener duplicados
        return True
    except Exception as e:
        st.warning(f"Sin conexión a Sheets — guardado solo en sesión local: {e}")
        return False

# ─────────────────────────────────────────────
#  CÁLCULOS
# ─────────────────────────────────────────────
def calcular_puntos(sj, cmj, abalakov, f_rel, ratio_adab, deporte) -> dict:
    perfil = BAREMOS_DEPORTIVOS.get(deporte, BAREMOS_DEPORTIVOS["General / Recreacional"])
    def puntuar(val, max_val):
        return round(min((float(val) / max_val) * 10, 10), 2) if max_val and float(val) > 0 else 0.0
    equil = round(max(0.0, 10.0 - abs(1.0 - float(ratio_adab)) * 20.0), 1) if float(ratio_adab) > 0 else 5.0
    return {
        "Squat Jump":  puntuar(sj,       perfil["SJ"]),
        "CMJ":         puntuar(cmj,      perfil["CMJ"]),
        "Abalakov":    puntuar(abalakov, perfil["Abalakov"]),
        "F. Relativa": puntuar(f_rel,    perfil["F_Rel"]),
        "Equilibrio":  equil,
    }

def nota_global(puntos: dict) -> float:
    return round(sum(puntos.values()) / len(puntos), 1)

def clasificar(nota: float) -> tuple[str, str]:
    if nota >= 8:   return "ÉLITE",        "#00d4ff"
    if nota >= 6.5: return "AVANZADO",     "#00cc88"
    if nota >= 5:   return "INTERMEDIO",   "#ffa500"
    return               "EN DESARROLLO",  "#ff4b4b"

# ─────────────────────────────────────────────
#  GRÁFICOS
# ─────────────────────────────────────────────
def chart_velocimetro(titulo, valor, max_val, zona_r, zona_a, zona_v):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=valor,
        title={"text": titulo, "font": {"size": 13, "color": "#c8d8f0", "family": "Inter"}},
        number={"font": {"size": 26, "color": "#ffffff"}},
        gauge={
            "axis": {"range": [0, max_val], "tickcolor": "#4a6080", "tickfont": {"color": "#4a6080", "size": 9}},
            "bar": {"color": "#00aaff", "thickness": 0.25},
            "bgcolor": "#1a2744", "borderwidth": 0,
            "steps": [{"range": zona_r, "color": "#3d1515"}, {"range": zona_a, "color": "#3d2c0a"}, {"range": zona_v, "color": "#0d3320"}],
            "threshold": {"line": {"color": "#00d4ff", "width": 3}, "value": valor},
        },
    ))
    fig.update_layout(height=180, margin=dict(l=10,r=10,t=30,b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

def chart_radar(puntos_actual: dict, puntos_previo: dict | None = None):
    cats = list(puntos_actual.keys())
    fig = go.Figure()
    if puntos_previo:
        v = list(puntos_previo.values()) + [list(puntos_previo.values())[0]]
        fig.add_trace(go.Scatterpolar(r=v, theta=cats+[cats[0]], fill="toself", name="Evaluación anterior",
            line=dict(color="rgba(120,140,180,0.6)", width=1.5), fillcolor="rgba(120,140,180,0.08)"))
    v = list(puntos_actual.values()) + [list(puntos_actual.values())[0]]
    fig.add_trace(go.Scatterpolar(r=v, theta=cats+[cats[0]], fill="toself", name="Evaluación actual",
        line=dict(color="#00aaff", width=2.5), fillcolor="rgba(0,170,255,0.12)"))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0,10], tickfont=dict(color="#4a6080",size=9), gridcolor="#1f2d45"),
                   angularaxis=dict(tickfont=dict(color="#c8d8f0",size=11)), bgcolor="rgba(0,0,0,0)"),
        showlegend=True, legend=dict(font=dict(color="#c8d8f0",size=11), bgcolor="rgba(0,0,0,0)"),
        height=380, paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=40,r=40,t=20,b=20))
    return fig

def chart_evolucion(df_atleta: pd.DataFrame, metrica: str, label: str):
    if df_atleta.empty or metrica not in df_atleta.columns: return None
    df = df_atleta.copy()
    try:
        df["_dt"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
        df = df.sort_values("_dt").tail(8)
    except Exception:
        df = df.tail(8)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df[metrica], mode="lines+markers+text",
        text=[f"{v:.1f}" for v in df[metrica]], textposition="top center",
        line=dict(color="#00aaff",width=2.5), marker=dict(size=9,color="#00d4ff"),
        textfont=dict(color="#c8d8f0",size=10)))
    fig.update_layout(title=dict(text=f"Evolución — {label}", font=dict(color="#c8d8f0",size=13)),
        xaxis=dict(tickfont=dict(color="#4a6080"), gridcolor="#1f2d45"),
        yaxis=dict(tickfont=dict(color="#4a6080"), gridcolor="#1f2d45"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(16,26,48,0.6)",
        height=220, margin=dict(l=10,r=10,t=40,b=10))
    return fig

def chart_barras_grupo(df: pd.DataFrame, metrica: str, label: str):
    if df.empty or metrica not in df.columns: return None
    df_plot = df[["Nombre",metrica]].dropna().copy()
    df_plot[metrica] = pd.to_numeric(df_plot[metrica], errors="coerce").fillna(0)
    df_plot = df_plot[df_plot[metrica] > 0].sort_values(metrica, ascending=True)
    if df_plot.empty: return None
    med = df_plot[metrica].median()
    colores = ["#ff4b4b" if v < med*0.85 else "#ffa500" if v < med*1.1 else "#00cc88" for v in df_plot[metrica]]
    fig = go.Figure(go.Bar(x=df_plot[metrica], y=df_plot["Nombre"], orientation="h", marker_color=colores,
        text=[f"{v:.1f}" for v in df_plot[metrica]], textposition="outside", textfont=dict(color="#c8d8f0",size=10)))
    fig.update_layout(title=dict(text=label, font=dict(color="#c8d8f0",size=13)),
        xaxis=dict(tickfont=dict(color="#4a6080"), gridcolor="#1f2d45"),
        yaxis=dict(tickfont=dict(color="#c8d8f0",size=11)),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(16,26,48,0.6)",
        height=max(250,35*len(df_plot)), margin=dict(l=10,r=50,t=40,b=10))
    return fig

# ─────────────────────────────────────────────
#  PDF
# ─────────────────────────────────────────────
def generar_pdf_informe(datos: dict, puntos_act: dict, puntos_prev: dict | None = None) -> BytesIO:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    W, H = A4

    AZUL_OSCURO=(0.04,0.07,0.13); AZUL_MEDIO=(0.05,0.13,0.25); AZUL_PANEL=(0.07,0.14,0.26)
    AZUL_FILA_A=(0.07,0.12,0.22); AZUL_FILA_B=(0.05,0.09,0.17); AZUL_HEADER=(0.04,0.20,0.38)
    CIAN=(0.00,0.83,1.00); BLANCO=(1.00,1.00,1.00); GRIS_TEXTO=(0.78,0.86,0.95)
    GRIS_LABEL=(0.49,0.66,0.86); VERDE=(0.00,0.80,0.53); NARANJA=(1.00,0.65,0.00); ROJO=(1.00,0.29,0.29)

    def fill(rgb):   c.setFillColorRGB(*rgb)
    def stroke(rgb): c.setStrokeColorRGB(*rgb)
    def rect_f(x,y,w,h,rgb): fill(rgb); c.rect(x,y,w,h,fill=1,stroke=0)
    def rect_s(x,y,w,h,rgb,lw=1): stroke(rgb); c.setLineWidth(lw); c.rect(x,y,w,h,fill=0,stroke=1)

    nota = nota_global(puntos_act)
    nivel_str, color_nivel = clasificar(nota)

    def hexagono(cx,cy,r,cf,cs,lw=2):
        pts=[(cx+r*math.cos(math.radians(60*i-30)),cy+r*math.sin(math.radians(60*i-30))) for i in range(6)]
        p=c.beginPath(); p.moveTo(*pts[0])
        for px,py in pts[1:]: p.lineTo(px,py)
        p.close(); fill(cf); c.drawPath(p,fill=1,stroke=0); stroke(cs); c.setLineWidth(lw); c.drawPath(p,fill=0,stroke=1)

    # ── Página 1 ──────────────────────────────────────────────────────────
    rect_f(0,0,W,H,AZUL_OSCURO); rect_f(0,H-220,W,220,AZUL_MEDIO); rect_f(0,0,6,H,CIAN)
    stroke(CIAN); c.setLineWidth(2); c.line(6,H-220,W,H-220)
    stroke((0.08,0.25,0.45)); c.setLineWidth(0.5)
    for off in range(0,120,18): c.line(W-160+off*0.3,H-10,W-10,H-160+off*0.3)

    hexagono(55,H-68,28,AZUL_PANEL,CIAN,2); hexagono(55,H-68,18,AZUL_OSCURO,CIAN,1)
    fill(CIAN); c.setFont("Helvetica-Bold",20); c.drawCentredString(55,H-74,"B")
    fill(BLANCO); c.setFont("Helvetica-Bold",26); c.drawString(92,H-58,"BIO SPORT")
    fill(CIAN);   c.setFont("Helvetica-Bold",26); c.drawString(222,H-58," PRO")
    fill(GRIS_LABEL); c.setFont("Helvetica",9); c.drawString(93,H-74,"EVALUACIÓN DEPORTIVA DE ALTO RENDIMIENTO")
    fill(GRIS_LABEL); c.setFont("Helvetica",9); c.drawRightString(W-30,H-58,datos["fecha"])

    y_c = H-320
    fill(AZUL_PANEL); c.roundRect(30,y_c-40,W-60,80,6,fill=1,stroke=0); rect_s(30,y_c-40,W-60,80,CIAN,1)
    fill(CIAN); c.setFont("Helvetica",8); c.drawString(48,y_c+30,"INFORME DE EVALUACIÓN  ·  ATLETA")
    fill(BLANCO); c.setFont("Helvetica-Bold",22); c.drawString(48,y_c+8,datos["nombre"].upper())
    fill(GRIS_LABEL); c.setFont("Helvetica",10)
    c.drawString(48,y_c-22,f"{datos['deporte'].upper()}   ·   {datos['edad']} años   ·   {datos['peso']} kg   ·   {datos['estatura']} m")

    fichas=[("DEPORTE",datos["deporte"]),("EDAD",f"{datos['edad']} años"),("PESO",f"{datos['peso']} kg"),("ESTATURA",f"{datos['estatura']} m")]
    fw=(W-60)/4
    for i,(lbl,val) in enumerate(fichas):
        fx=30+i*fw; fy=y_c-130
        rect_f(fx+2,fy,fw-4,70,AZUL_PANEL); rect_s(fx+2,fy,fw-4,70,(0.10,0.24,0.44),0.6)
        fill(GRIS_LABEL); c.setFont("Helvetica",7); c.drawCentredString(fx+fw/2,fy+54,lbl)
        fill(BLANCO); c.setFont("Helvetica-Bold",13); c.drawCentredString(fx+fw/2,fy+32,val)
        fill(CIAN); c.rect(fx+2,fy,fw-4,3,fill=1,stroke=0)

    bcx=W/2; bcy=y_c-270
    for r,alpha in [(80,0.08),(68,0.15),(56,1.0)]:
        if r==56: hexagono(bcx,bcy,r,AZUL_PANEL,CIAN,2.5)
        else: stroke(CIAN); c.setLineWidth(0.5); c.setStrokeAlpha(alpha); c.circle(bcx,bcy,r,fill=0,stroke=1)
    c.setStrokeAlpha(1.0)
    fill(BLANCO); c.setFont("Helvetica-Bold",36); c.drawCentredString(bcx,bcy+2,f"{nota:.1f}")
    fill(GRIS_LABEL); c.setFont("Helvetica",10); c.drawCentredString(bcx,bcy-18,"/ 10  NOTA GLOBAL")
    r_hex=tuple(int(color_nivel.lstrip("#")[i:i+2],16)/255 for i in (0,2,4))
    rect_f(bcx-55,bcy-50,110,20,r_hex); fill(AZUL_OSCURO); c.setFont("Helvetica-Bold",9); c.drawCentredString(bcx,bcy-44,nivel_str)

    by=bcy-110; bw=320; bx0=(W-bw)/2
    fill(GRIS_LABEL); c.setFont("Helvetica-Bold",7); c.drawCentredString(W/2,by+20,"PERFIL DE CAPACIDADES")
    for i,(cat,val) in enumerate(puntos_act.items()):
        row_y=by-i*22
        fill(GRIS_LABEL); c.setFont("Helvetica",8); c.drawString(bx0,row_y,cat)
        rect_f(bx0+110,row_y,bw-110,10,(0.08,0.14,0.26))
        if puntos_prev and cat in puntos_prev:
            vp=min(puntos_prev[cat],10)/10; fill((0.35,0.42,0.55)); c.rect(bx0+110,row_y,(bw-110)*vp,10,fill=1,stroke=0)
        va=min(val,10)/10; cb=VERDE if val>=6.5 else NARANJA if val>=5 else ROJO
        rect_f(bx0+110,row_y,(bw-110)*va,10,cb)
        fill(BLANCO); c.setFont("Helvetica-Bold",8); c.drawRightString(bx0+bw+28,row_y+2,f"{val:.1f}")
    if puntos_prev:
        fill(GRIS_LABEL); c.setFont("Helvetica",7)
        byl=by-len(puntos_act)*22-10; rect_f(bx0+110,byl,10,8,(0.35,0.42,0.55)); c.drawString(bx0+124,byl,"Evaluación anterior")

    rect_f(0,0,W,28,(0.03,0.05,0.10)); stroke((0.08,0.20,0.38)); c.setLineWidth(0.5); c.line(6,28,W,28)
    fill(GRIS_LABEL); c.setFont("Helvetica",7)
    c.drawString(20,10,"Bio Sport Pro  ·  Evaluación Deportiva de Alto Rendimiento")
    c.drawRightString(W-20,10,f"Página 1 de 2  ·  {datos['fecha']}")

    # ── Página 2 ──────────────────────────────────────────────────────────
    c.showPage()
    rect_f(0,0,W,H,AZUL_OSCURO); rect_f(0,0,6,H,CIAN); rect_f(0,H-60,W,60,AZUL_MEDIO)
    stroke(CIAN); c.setLineWidth(1.5); c.line(6,H-60,W,H-60)
    fill(BLANCO); c.setFont("Helvetica-Bold",13); c.drawString(24,H-35,"RESULTADOS TÉCNICOS")
    fill(GRIS_LABEL); c.setFont("Helvetica",9); c.drawString(24,H-50,f"{datos['nombre'].upper()}  ·  {datos['deporte']}  ·  {datos['fecha']}")
    fill(GRIS_LABEL); c.setFont("Helvetica",8); c.drawRightString(W-20,H-38,"02")

    y_t=H-80
    perfil_max=BAREMOS_DEPORTIVOS.get(datos["deporte"],BAREMOS_DEPORTIVOS["General / Recreacional"])
    metricas_tabla=[
        ("Squat Jump (SJ)",   datos["sj"],      "cm",   perfil_max["SJ"]),
        ("CMJ",               datos["cmj"],     "cm",   perfil_max["CMJ"]),
        ("Abalakov",          datos["abalakov"],"cm",   perfil_max["Abalakov"]),
        ("IMTP",              datos["imtp"],    "N",    None),
        ("Fuerza Relativa",   datos["f_rel"],   "N/kg", perfil_max["F_Rel"]),
        ("RSI Modificado",    datos["rsi"],     "",     perfil_max["RSI"]),
        ("Ratio Aduc/Abduc",  datos["ratio"],   "",     None),
    ]
    col_x=[24,180,285,355,470]; fila_h=24
    rect_f(6,y_t-fila_h,W-6,fila_h,AZUL_HEADER)
    for hx,htxt in zip(col_x,["PRUEBA","RESULTADO","RENDIMIENTO","PUNT.","NIVEL"]):
        fill(CIAN); c.setFont("Helvetica-Bold",8); c.drawString(hx+6,y_t-fila_h+8,htxt)
    y_t-=fila_h

    for i,(prueba,val_raw,unidad,max_v) in enumerate(metricas_tabla):
        bg=AZUL_FILA_A if i%2==0 else AZUL_FILA_B; rect_f(6,y_t-fila_h,W-6,fila_h,bg)
        fill(GRIS_TEXTO); c.setFont("Helvetica",9); c.drawString(col_x[0]+6,y_t-fila_h+8,prueba)
        vf=f"{float(val_raw):.2f}".rstrip("0").rstrip(".") if val_raw else "0"
        fill(BLANCO); c.setFont("Helvetica-Bold",9); c.drawString(col_x[1]+6,y_t-fila_h+8,f"{vf} {unidad}".strip())
        if max_v and float(val_raw or 0)>0:
            puntaje=min((float(val_raw)/max_v)*10,10); cb=VERDE if puntaje>=6.5 else NARANJA if puntaje>=5 else ROJO
            bx2=col_x[2]+6; bw2=90; by2=y_t-fila_h+8
            rect_f(bx2,by2,bw2,8,(0.08,0.14,0.26)); rect_f(bx2,by2,bw2*(puntaje/10),8,cb)
            fill(BLANCO); c.setFont("Helvetica-Bold",9); c.drawCentredString(col_x[3]+20,y_t-fila_h+8,f"{puntaje:.1f}/10")
            rect_f(col_x[4]+2,y_t-fila_h+5,90,14,cb); nl,_=clasificar(puntaje)
            fill(AZUL_OSCURO); c.setFont("Helvetica-Bold",7); c.drawCentredString(col_x[4]+47,y_t-fila_h+10,nl)
        else:
            fill(GRIS_LABEL); c.setFont("Helvetica",8); c.drawString(col_x[2]+6,y_t-fila_h+8,"—")
        y_t-=fila_h

    y_sec=y_t-20
    fill(CIAN); c.setFont("Helvetica-Bold",8); c.drawString(24,y_sec,"PERFIL RADAR DE CAPACIDADES")

    rcx=130; rcy=y_sec-110; rr=85; n=len(puntos_act); cats=list(puntos_act.keys())
    def rpt(idx,radio):
        ang=idx*(2*math.pi/n)-math.pi/2
        return rcx+radio*math.cos(ang), rcy+radio*math.sin(ang)

    for nr in [1,2,3]:
        ring=[rpt(j,rr*nr/3) for j in range(n)]
        p=c.beginPath(); p.moveTo(*ring[0])
        for px2,py2 in ring[1:]: p.lineTo(px2,py2)
        p.close()
        fill([(0.18,0.07,0.07),(0.18,0.14,0.04),(0.04,0.18,0.12)][nr-1]); c.drawPath(p,fill=1,stroke=0)
        stroke((0.12,0.22,0.38)); c.setLineWidth(0.4); c.drawPath(p,fill=0,stroke=1)

    stroke((0.15,0.28,0.48)); c.setLineWidth(0.6)
    for j in range(n): ex,ey=rpt(j,rr); c.line(rcx,rcy,ex,ey)

    if puntos_prev:
        pp=[rpt(j,(min(puntos_prev.get(k,0),10)/10)*rr) for j,k in enumerate(cats)]
        p=c.beginPath(); p.moveTo(*pp[0])
        for px2,py2 in pp[1:]: p.lineTo(px2,py2)
        p.close(); fill((0.25,0.30,0.40)); c.drawPath(p,fill=1,stroke=0)
        stroke((0.45,0.55,0.70)); c.setLineWidth(1.2); c.drawPath(p,fill=0,stroke=1)

    pa=[rpt(j,(min(v,10)/10)*rr) for j,(_,v) in enumerate(puntos_act.items())]
    p=c.beginPath(); p.moveTo(*pa[0])
    for px2,py2 in pa[1:]: p.lineTo(px2,py2)
    p.close(); fill((0.0,0.42,0.70)); c.drawPath(p,fill=1,stroke=0)
    stroke(CIAN); c.setLineWidth(2); c.drawPath(p,fill=0,stroke=1)

    for j,(k,v) in enumerate(puntos_act.items()):
        px2,py2=rpt(j,(min(v,10)/10)*rr); fill(CIAN); c.circle(px2,py2,3.5,fill=1,stroke=0)
        lx,ly=rpt(j,rr+14); fill(GRIS_TEXTO); c.setFont("Helvetica",7); c.drawCentredString(lx,ly-3,k)

    dx=260; dy=y_sec-10
    fill(CIAN); c.setFont("Helvetica-Bold",8); c.drawString(dx,dy,"DETALLE COMPARATIVO"); dy-=16
    for cat,val in puntos_act.items():
        rect_f(dx,dy-4,W-dx-20,20,AZUL_FILA_A)
        fill(GRIS_TEXTO); c.setFont("Helvetica",8); c.drawString(dx+5,dy+2,cat)
        cv=VERDE if val>=6.5 else NARANJA if val>=5 else ROJO; fill(cv); c.setFont("Helvetica-Bold",9); c.drawRightString(dx+120,dy+2,f"{val:.1f}")
        if puntos_prev and cat in puntos_prev:
            diff=val-puntos_prev[cat]
            fill(VERDE if diff>0.2 else ROJO if diff<-0.2 else GRIS_LABEL)
            arrow=f"▲ +{diff:.1f}" if diff>0.2 else (f"▼ {diff:.1f}" if diff<-0.2 else "= =")
            c.setFont("Helvetica-Bold",8); c.drawString(dx+130,dy+2,arrow)
            fill(GRIS_LABEL); c.setFont("Helvetica",7); c.drawRightString(W-26,dy+2,f"ant: {puntos_prev[cat]:.1f}")
        dy-=22
    if puntos_prev:
        dy-=4; fill(GRIS_LABEL); c.setFont("Helvetica",7); c.drawString(dx,dy,"▲▼ variación respecto evaluación anterior")

    b2cx=dx+100; b2cy=dy-55
    hexagono(b2cx,b2cy,42,AZUL_PANEL,CIAN,2)
    fill(BLANCO); c.setFont("Helvetica-Bold",22); c.drawCentredString(b2cx,b2cy+4,f"{nota:.1f}")
    fill(GRIS_LABEL); c.setFont("Helvetica",7); c.drawCentredString(b2cx,b2cy-10,"NOTA GLOBAL / 10")
    _,cn2=clasificar(nota); rh2=tuple(int(cn2.lstrip("#")[i:i+2],16)/255 for i in (0,2,4))
    rect_f(b2cx-38,b2cy-30,76,14,rh2); fill(AZUL_OSCURO); c.setFont("Helvetica-Bold",7); c.drawCentredString(b2cx,b2cy-24,nivel_str)

    rect_f(0,0,W,28,(0.03,0.05,0.10)); stroke((0.08,0.20,0.38)); c.setLineWidth(0.5); c.line(6,28,W,28)
    fill(GRIS_LABEL); c.setFont("Helvetica",7)
    c.drawString(20,10,"Bio Sport Pro  ·  Evaluación Deportiva de Alto Rendimiento")
    c.drawRightString(W-20,10,f"Página 2 de 2  ·  {datos['fecha']}")

    c.save(); buffer.seek(0)
    return buffer

def generar_pdf_grupal(df: pd.DataFrame) -> BytesIO:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    ancho,alto=A4
    c.setFillColorRGB(0.04,0.07,0.13); c.rect(0,0,ancho,alto,fill=1,stroke=0)
    c.setFillColorRGB(0.05,0.13,0.25); c.rect(0,alto-100,ancho,100,fill=1,stroke=0)
    c.setStrokeColorRGB(0,0.83,1); c.setLineWidth(3); c.line(0,alto-100,ancho,alto-100)
    c.setFillColorRGB(0,0.83,1); c.setFont("Helvetica-Bold",18)
    c.drawString(40,alto-50,"BIO SPORT PRO — INFORME GRUPAL")
    c.setFont("Helvetica",10); c.setFillColorRGB(0.5,0.7,0.9)
    fh=datetime.now().strftime("%d/%m/%Y"); c.drawString(40,alto-70,f"Generado el {fh}  ·  {len(df)} atletas evaluados")
    _cc=[("Nombre","Nombre"),("Deporte","Deporte"),("SJ_cm","SJ"),("CMJ_cm","CMJ"),("Abalakov_cm","Abalakov"),("F_Rel_NKg","F.Rel N/kg"),("RSI_Mod","RSI")]
    cols_m=[col for col,_ in _cc if col in df.columns]
    cols_l=[lbl for col,lbl in _cc if col in df.columns]
    df_show=df[cols_m].tail(50).copy()
    td=[cols_l]+[[str(row[col])[:18] for col in cols_m] for _,row in df_show.iterrows()]
    _w=[110,80,50,50,55,60,50]
    t=Table(td,colWidths=_w[:len(cols_m)])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0f3460")),("TEXTCOLOR",(0,0),(-1,0),colors.HexColor("#00d4ff")),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#111827"),colors.HexColor("#0d1627")]),
        ("TEXTCOLOR",(0,1),(-1,-1),colors.HexColor("#c8d8f0")),("FONTSIZE",(0,1),(-1,-1),8),
        ("ALIGN",(2,0),(-1,-1),"CENTER"),("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#1f2d45")),
        ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
    ]))
    t.wrapOn(c,ancho-80,alto); t.drawOn(c,40,alto-150-len(td)*17)
    c.setFillColorRGB(0.04,0.07,0.13); c.rect(0,0,ancho,30,fill=1,stroke=0)
    c.setFont("Helvetica",7); c.setFillColorRGB(0.35,0.50,0.70)
    c.drawString(40,10,"Generado por Bio Sport Pro  ·  Informe Grupal"); c.drawRightString(ancho-40,10,fh)
    c.save(); buffer.seek(0)
    return buffer

# ═══════════════════════════════════════════════════════════════════
#  INICIO — conexión y carga inicial
# ═══════════════════════════════════════════════════════════════════
cliente_sheets = conectar_sheets()

# get_df() siempre devuelve el DataFrame desde session_state,
# recargando desde Sheets solo cuando cache_ver cambió.
data_historica = get_df()

# lista_atletas se recalcula EN CADA RERUN desde el df actualizado
lista_atletas = ["➕ Nuevo Atleta"]
if not data_historica.empty and "Nombre" in data_historica.columns:
    nombres_unicos = sorted(data_historica["Nombre"].dropna().unique().tolist())
    lista_atletas += [n for n in nombres_unicos if str(n).strip()]

# ─────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────
col_logo, col_titulo = st.columns([1,6])
with col_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=80)
    else: st.markdown("<div style='font-size:3rem;'>⚡</div>", unsafe_allow_html=True)
with col_titulo:
    st.markdown("""
    <div style="padding:12px 0">
      <p class="hero-title">Bio Sport <span class="accent">Pro</span></p>
      <p class="hero-subtitle">Plataforma de Evaluación Deportiva de Alto Rendimiento</p>
    </div>""", unsafe_allow_html=True)

st.divider()

tab_eval, tab_historial, tab_grupo = st.tabs(["📋 Nueva Evaluación","📈 Historial Individual","👥 Informe Grupal"])

# ════════════════════════════════════════════════
#  TAB 1 — NUEVA EVALUACIÓN
# ════════════════════════════════════════════════
with tab_eval:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">Identificación del Atleta</p>', unsafe_allow_html=True)

    c_sel, c_new = st.columns([2,3])
    with c_sel:
        atleta_sel = st.selectbox("Buscar en historial", lista_atletas)
    with c_new:
        valor_nombre = "" if atleta_sel == "➕ Nuevo Atleta" else atleta_sel
        nombre = st.text_input("Nombre completo", value=valor_nombre, placeholder="Ej: Carlos Pérez")

    c1,c2,c3,c4 = st.columns(4)
    with c1: edad     = st.number_input("Edad",          min_value=10, max_value=60, step=1,   value=22)
    with c2: peso     = st.number_input("Peso (kg)",     min_value=30.0, max_value=180.0, step=0.1, value=75.0)
    with c3: estatura = st.number_input("Estatura (m)",  min_value=1.40, max_value=2.20, step=0.01, value=1.75)
    with c4: deporte  = st.selectbox("Deporte / Disciplina", options=list(BAREMOS_DEPORTIVOS.keys()), index=0)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">Pruebas de Potencia y Salto</p>', unsafe_allow_html=True)
    p1,p2,p3,p4 = st.columns(4)
    with p1: sj       = st.number_input("SJ (cm)",        min_value=0.0, max_value=100.0, step=0.1, value=0.0)
    with p2: cmj      = st.number_input("CMJ (cm)",       min_value=0.0, max_value=100.0, step=0.1, value=0.0)
    with p3: abalakov = st.number_input("Abalakov (cm)",  min_value=0.0, max_value=100.0, step=0.1, value=0.0)
    with p4: rsi      = st.number_input("RSI Modificado", min_value=0.0, max_value=5.0,   step=0.01,value=0.0)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">Fuerza Isométrica y Dinamometría</p>', unsafe_allow_html=True)
    f1,f2,f3 = st.columns(3)
    with f1: imtp  = st.number_input("IMTP (N)",       min_value=0.0, step=10.0, value=0.0)
    with f2: aduc  = st.number_input("Aductores (N)",  min_value=0.0, step=1.0,  value=0.0)
    with f3: abduc = st.number_input("Abductores (N)", min_value=0.0, step=1.0,  value=0.0)
    st.markdown('</div>', unsafe_allow_html=True)

    if any([sj>0, cmj>0, abalakov>0, imtp>0]):
        f_rel_live = round(imtp/peso,1) if peso>0 else 0
        ratio_live = round(aduc/abduc,2) if abduc>0 else 1.0
        pts_live   = calcular_puntos(sj,cmj,abalakov,f_rel_live,ratio_live,deporte)
        nota_live  = nota_global(pts_live)
        nivel_live, color_live = clasificar(nota_live)
        mx = BAREMOS_DEPORTIVOS.get(deporte, BAREMOS_DEPORTIVOS["General / Recreacional"])

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Vista Previa en Tiempo Real</p>', unsafe_allow_html=True)
        chips = '<div class="metric-row">'
        for cat,val in pts_live.items():
            chips += f'<div class="metric-chip"><div class="val">{val:.1f}</div><div class="lbl">{cat}</div></div>'
        chips += f'<div class="metric-chip" style="border-color:#00d4ff;"><div class="val" style="color:#fff">{nota_live}</div><div class="lbl" style="color:{color_live}">{nivel_live}</div></div></div>'
        st.markdown(chips, unsafe_allow_html=True)
        vm1,vm2,vm3 = st.columns(3)
        with vm1: st.plotly_chart(chart_velocimetro("SJ",sj,mx["SJ"],[0,mx["SJ"]*0.5],[mx["SJ"]*0.5,mx["SJ"]*0.7],[mx["SJ"]*0.7,mx["SJ"]]), use_container_width=True, key="pv_sj")
        with vm2: st.plotly_chart(chart_velocimetro("CMJ",cmj,mx["CMJ"],[0,mx["CMJ"]*0.5],[mx["CMJ"]*0.5,mx["CMJ"]*0.7],[mx["CMJ"]*0.7,mx["CMJ"]]), use_container_width=True, key="pv_cmj")
        with vm3: st.plotly_chart(chart_velocimetro("RSI",rsi,mx["RSI"],[0,mx["RSI"]*0.33],[mx["RSI"]*0.33,mx["RSI"]*0.55],[mx["RSI"]*0.55,mx["RSI"]]), use_container_width=True, key="pv_rsi")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("")
    confirmar = st.toggle("✅ Confirmo que los datos son correctos y están listos para guardar")
    col_btn1,_ = st.columns([3,1])
    with col_btn1:
        btn_guardar = st.button("💾 GUARDAR Y GENERAR INFORME PDF", type="primary", use_container_width=True, disabled=not confirmar)

    if btn_guardar:
        errores = []
        if not nombre.strip():                          errores.append("El nombre es obligatorio.")
        if peso <= 0:                                   errores.append("El peso debe ser mayor a 0.")
        if all(v==0 for v in [sj,cmj,abalakov,imtp]): errores.append("Registra al menos una prueba.")
        if errores:
            for e in errores: st.error(f"⚠️ {e}")
        else:
            f_rel = round(imtp/peso,1) if peso>0 else 0
            ratio = round(aduc/abduc,2) if abduc>0 else 1.0
            fecha = datetime.now().strftime("%d/%m/%Y")
            datos_eval = {
                "nombre": nombre.strip(), "edad": int(edad), "peso": round(peso,1),
                "estatura": round(estatura,2), "deporte": deporte, "fecha": fecha,
                "cmj": cmj, "sj": sj, "abalakov": abalakov,
                "imtp": imtp, "f_rel": f_rel, "rsi": rsi,
                "aduc": aduc, "abduc": abduc, "ratio": ratio,
            }

            # Eval previa desde el df ACTUAL en session_state
            eval_previa = None
            df_actual = get_df()
            if not df_actual.empty and "Nombre" in df_actual.columns:
                mask = df_actual["Nombre"] == nombre.strip()
                if mask.any():
                    eval_previa = df_actual[mask].iloc[-1].to_dict()

            # Guardar — siempre en local, opcionalmente en Sheets
            fila = [fecha, nombre.strip(), int(edad), round(peso,1), round(estatura,2),
                    deporte, imtp, f_rel, sj, cmj, abalakov, rsi, aduc, abduc, ratio]
            guardado_sheets = guardar_fila(cliente_sheets, fila)
            if guardado_sheets:
                st.success("✅ Evaluación guardada en Google Sheets.")
            else:
                st.info("💾 Evaluación guardada en sesión local (sin conexión a Sheets).")

            puntos_act = calcular_puntos(sj,cmj,abalakov,f_rel,ratio,deporte)
            puntos_prev = None
            if eval_previa:
                try:
                    dep_prev = str(eval_previa.get("Deporte", deporte))
                    if dep_prev not in BAREMOS_DEPORTIVOS: dep_prev = "General / Recreacional"
                    puntos_prev = calcular_puntos(
                        float(eval_previa.get("SJ_cm",0)), float(eval_previa.get("CMJ_cm",0)),
                        float(eval_previa.get("Abalakov_cm",0)), float(eval_previa.get("F_Rel_NKg",0)),
                        float(eval_previa.get("Ratio_AdAb",1)), dep_prev)
                except Exception: pass

            with st.spinner("Generando informe PDF…"):
                pdf_buffer = generar_pdf_informe(datos_eval, puntos_act, puntos_prev)

            st.session_state.informe_actual = {
                "datos": datos_eval, "pdf": pdf_buffer,
                "radar_act": puntos_act, "radar_prev": puntos_prev,
            }
            # Rerun para que lista_atletas y los tabs se actualicen
            st.rerun()

    if st.session_state.informe_actual:
        inf=st.session_state.informe_actual; d=inf["datos"]; ra=inf["radar_act"]; rp=inf["radar_prev"]
        nota=nota_global(ra); nivel,color_nivel=clasificar(nota)
        st.divider(); st.markdown(f"### 📊 Resultados — {d['nombre']}")
        col_badge,col_radar=st.columns([1,2])
        with col_badge:
            st.markdown(f"""
            <div style="text-align:center;margin-top:20px">
                <div class="score-badge"><span class="num">{nota}</span><span class="denom">/ 10</span></div>
                <p style="font-size:1rem;font-weight:700;color:{color_nivel};letter-spacing:1px;margin-top:8px">{nivel}</p>
                <p style="font-size:0.8rem;color:#7ea8d8">{d['fecha']}</p>
            </div>""", unsafe_allow_html=True)
        with col_radar:
            st.plotly_chart(chart_radar(ra,rp), use_container_width=True, key="res_radar")
        if rp: st.info("💡 La sombra representa la evaluación anterior del atleta.")
        mx2=BAREMOS_DEPORTIVOS.get(d["deporte"],BAREMOS_DEPORTIVOS["General / Recreacional"])
        v1,v2=st.columns(2)
        with v1: st.plotly_chart(chart_velocimetro("CMJ",d["cmj"],mx2["CMJ"],[0,mx2["CMJ"]*0.5],[mx2["CMJ"]*0.5,mx2["CMJ"]*0.7],[mx2["CMJ"]*0.7,mx2["CMJ"]]), use_container_width=True, key="res_cmj")
        with v2: st.plotly_chart(chart_velocimetro("RSI Modificado",d["rsi"],mx2["RSI"],[0,mx2["RSI"]*0.33],[mx2["RSI"]*0.33,mx2["RSI"]*0.55],[mx2["RSI"]*0.55,mx2["RSI"]]), use_container_width=True, key="res_rsi")
        st.download_button(label="📥 DESCARGAR INFORME OFICIAL (PDF)", data=inf["pdf"],
            file_name=f"BioSport_{d['nombre'].replace(' ','_')}_{d['fecha'].replace('/','')}.pdf",
            mime="application/pdf", use_container_width=True)

# ════════════════════════════════════════════════
#  TAB 2 — HISTORIAL INDIVIDUAL
# ════════════════════════════════════════════════
with tab_historial:
    df_hist = get_df()
    if df_hist.empty or "Nombre" not in df_hist.columns:
        st.info("Aún no hay evaluaciones guardadas. Completa una evaluación para empezar.")
    else:
        nombres_hist = sorted([n for n in df_hist["Nombre"].dropna().unique().tolist() if str(n).strip()])
        if not nombres_hist:
            st.info("No se encontraron atletas en el historial.")
        else:
            atleta_hist = st.selectbox("Seleccionar atleta", nombres_hist, key="hist_sel")
            df_at = df_hist[df_hist["Nombre"]==atleta_hist].copy()
            if df_at.empty:
                st.warning("No hay registros para este atleta.")
            else:
                st.markdown(f"**{len(df_at)} evaluación(es) encontrada(s)**")
                ultima=df_at.iloc[-1]
                col_m1,col_m2,col_m3,col_m4,col_m5=st.columns(5)
                for col,(lab,ck,uni) in zip([col_m1,col_m2,col_m3,col_m4,col_m5],[
                    ("SJ","SJ_cm","cm"),("CMJ","CMJ_cm","cm"),
                    ("Abalakov","Abalakov_cm","cm"),("F. Relativa","F_Rel_NKg","N/kg"),("RSI","RSI_Mod","")]):
                    col.metric(label=lab, value=f"{float(ultima.get(ck,0) or 0):.1f} {uni}".strip())
                st.markdown("#### Evolución Histórica")
                evo=[("SJ_cm","Squat Jump (cm)"),("CMJ_cm","CMJ (cm)"),("Abalakov_cm","Abalakov (cm)"),("F_Rel_NKg","Fuerza Relativa (N/kg)")]
                for ca,cb in zip(evo[::2],evo[1::2]):
                    c1e,c2e=st.columns(2)
                    with c1e:
                        fig=chart_evolucion(df_at,ca[0],ca[1])
                        if fig: st.plotly_chart(fig,use_container_width=True,key=f"h_{ca[0]}")
                    with c2e:
                        fig=chart_evolucion(df_at,cb[0],cb[1])
                        if fig: st.plotly_chart(fig,use_container_width=True,key=f"h_{cb[0]}")
                with st.expander("Ver tabla completa"):
                    st.dataframe(df_at, use_container_width=True)

# ════════════════════════════════════════════════
#  TAB 3 — INFORME GRUPAL
# ════════════════════════════════════════════════
with tab_grupo:
    df_grp_src = get_df()
    if df_grp_src.empty or "Nombre" not in df_grp_src.columns:
        st.info("Aún no hay evaluaciones en el sistema.")
    else:
        st.markdown("#### Comparativa del Grupo")
        deportes_lista = sorted([str(d) for d in df_grp_src["Deporte"].dropna().unique() if str(d).strip()]) if "Deporte" in df_grp_src.columns else []
        deporte_filtro = st.selectbox("Filtrar por deporte / posición", ["Todos"]+deportes_lista)

        df_grupo = df_grp_src.copy()
        if deporte_filtro != "Todos" and "Deporte" in df_grupo.columns:
            df_grupo = df_grupo[df_grupo["Deporte"]==deporte_filtro]
        if "Fecha" in df_grupo.columns and "Nombre" in df_grupo.columns:
            try: df_grupo = df_grupo.sort_values("Fecha").groupby("Nombre").last().reset_index()
            except Exception: pass

        st.markdown(f"**{len(df_grupo)} atleta(s) en el grupo**")
        for ca,cb in zip([("CMJ_cm","CMJ (cm)"),("F_Rel_NKg","Fuerza Relativa (N/kg)")],
                         [("SJ_cm","Squat Jump (cm)"),("RSI_Mod","RSI Modificado")]):
            c1g,c2g=st.columns(2)
            with c1g:
                fig=chart_barras_grupo(df_grupo,ca[0],ca[1])
                if fig: st.plotly_chart(fig,use_container_width=True,key=f"g_{ca[0]}")
            with c2g:
                fig=chart_barras_grupo(df_grupo,cb[0],cb[1])
                if fig: st.plotly_chart(fig,use_container_width=True,key=f"g_{cb[0]}")

        st.markdown("#### Tabla Resumen")
        cd=[c for c in ["Nombre","Deporte","Fecha","SJ_cm","CMJ_cm","Abalakov_cm","F_Rel_NKg","RSI_Mod"] if c in df_grupo.columns]
        st.dataframe(df_grupo[cd] if cd else df_grupo, use_container_width=True)

        with st.spinner("Preparando PDF grupal…"):
            pdf_grupo=generar_pdf_grupal(df_grupo)
        st.download_button(
            label="📥 DESCARGAR INFORME GRUPAL (PDF)", data=pdf_grupo,
            file_name=f"BioSport_Grupal_{deporte_filtro.replace(' ','_')}_{datetime.now().strftime('%d%m%Y')}.pdf",
            mime="application/pdf", use_container_width=True)
