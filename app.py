"""
Bio Sport Pro — Evaluación Deportiva de Alto Rendimiento
Versión 2.0 — Refactorizado y mejorado
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from PIL import Image as PILImage, ImageDraw
import math
import os

# ─────────────────────────────────────────────
#  CONFIGURACIÓN DE BAREMOS (máximo = nota 10)
# ─────────────────────────────────────────────
BAREMOS = {
    "SJ":        {"max": 50.0,  "unidad": "cm",  "label": "Squat Jump"},
    "CMJ":       {"max": 60.0,  "unidad": "cm",  "label": "CMJ"},
    "Abalakov":  {"max": 70.0,  "unidad": "cm",  "label": "Abalakov"},
    "F_Rel":     {"max": 50.0,  "unidad": "N/kg","label": "Fuerza Relativa"},
    "RSI":       {"max": 3.0,   "unidad": "",    "label": "RSI Modificado"},
    "CMJ_Barra": {"max": 80.0,  "unidad": "cm",  "label": "CMJ c/Barra"},
}

RADAR_KEYS = {
    "SJ":       "Squat Jump",
    "CMJ":      "CMJ",
    "Abalakov": "Abalakov",
    "F_Rel":    "F. Relativa",
    "Ratio":    "Equilibrio",   # derivado de aduc/abduc
}

COLUMNAS_SHEETS = [
    "Fecha", "Nombre", "Edad", "Peso_kg", "Estatura_m", "Deporte",
    "IMTP_N", "F_Rel_NKg", "SJ_cm", "CMJ_cm", "Abalakov_cm",
    "RSI_Mod", "Aduc_N", "Abduc_N", "Ratio_AdAb"
]

# ─────────────────────────────────────────────
#  PAGE CONFIG & CSS
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Bio Sport Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* ── Tipografía y fondo ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
.stApp {
    background: #0a0e1a;
    color: #e8eaf0;
}

/* ── Encabezado hero ── */
.hero-block {
    background: linear-gradient(135deg, #0d1b2e 0%, #112240 60%, #0f3460 100%);
    border: 1px solid #1e3a5f;
    border-radius: 16px;
    padding: 32px 40px;
    margin-bottom: 28px;
    display: flex;
    align-items: center;
    gap: 20px;
}
.hero-title {
    font-size: 2.2rem;
    font-weight: 900;
    letter-spacing: -0.5px;
    color: #ffffff;
    margin: 0;
}
.hero-subtitle {
    font-size: 0.95rem;
    color: #7ea8d8;
    margin: 4px 0 0 0;
    font-weight: 400;
}
.accent { color: #00d4ff; }

/* ── Tarjetas de sección ── */
.section-card {
    background: #111827;
    border: 1px solid #1f2d45;
    border-radius: 12px;
    padding: 24px 28px;
    margin-bottom: 20px;
}
.section-title {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #00d4ff;
    margin-bottom: 16px;
}

/* ── Métricas rápidas ── */
.metric-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }
.metric-chip {
    background: #1a2744;
    border: 1px solid #2a3f6f;
    border-radius: 10px;
    padding: 14px 20px;
    min-width: 130px;
    flex: 1;
    text-align: center;
}
.metric-chip .val {
    font-size: 1.7rem;
    font-weight: 700;
    color: #00d4ff;
    line-height: 1;
}
.metric-chip .lbl {
    font-size: 0.72rem;
    color: #8899bb;
    margin-top: 4px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}

/* ── Indicador de nota global ── */
.score-badge {
    background: linear-gradient(135deg, #0f3460, #1a4f8a);
    border: 2px solid #00d4ff;
    border-radius: 50%;
    width: 110px; height: 110px;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    margin: 0 auto 20px auto;
}
.score-badge .num { font-size: 2.4rem; font-weight: 900; color: #fff; line-height: 1; }
.score-badge .denom { font-size: 0.8rem; color: #7ea8d8; }

/* ── Botón primario ── */
div.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #0066cc, #00aaff);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
    font-size: 0.95rem;
    padding: 0.65rem 2rem;
    transition: opacity 0.2s;
}
div.stButton > button[kind="primary"]:hover { opacity: 0.88; }

/* ── Inputs ── */
.stTextInput input, .stNumberInput input, .stSelectbox > div {
    background: #1a2035 !important;
    border: 1px solid #2a3f6f !important;
    color: #e8eaf0 !important;
    border-radius: 8px !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #111827;
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
    border: 1px solid #1f2d45;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #8899bb;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.85rem;
}
.stTabs [aria-selected="true"] {
    background: #1a2744 !important;
    color: #00d4ff !important;
}

/* ── Alertas ── */
.stSuccess { background: #0d2a1a !important; border-color: #00cc88 !important; }
.stError   { background: #2a0d0d !important; border-color: #ff4b4b !important; }
.stWarning { background: #2a1e0d !important; border-color: #ffa500 !important; }

/* ── Tabla de atletas ── */
.stDataFrame { border-radius: 10px; overflow: hidden; }

/* ── Divider ── */
hr { border-color: #1f2d45 !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  ESTADO DE SESIÓN
# ─────────────────────────────────────────────
defaults = {
    "informe_actual": None,
    "step": 1,
    "saved_ok": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────
#  CONEXIÓN A GOOGLE SHEETS
# ─────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def conectar_sheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    try:
        creds_info = json.loads(st.secrets["google_credentials"], strict=False)
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception:
        return None


@st.cache_data(ttl=120, show_spinner=False)
def cargar_historial(_cliente):
    """Retorna DataFrame con todo el historial; vacío si falla."""
    if _cliente is None:
        return pd.DataFrame()
    try:
        hoja = _cliente.open("BioSport_BD").sheet1
        registros = hoja.get_all_records()
        if not registros:
            return pd.DataFrame()
        df = pd.DataFrame(registros)
        df.columns = [str(c).strip() for c in df.columns]

        # ── Normalizar nombres de columna del sheet anterior al nuevo esquema ──
        # Mapeo: nombre_viejo -> nombre_nuevo
        ALIAS = {
            "nombre":    "Nombre",
            "Nombre":    "Nombre",
            "fecha":     "Fecha",
            "Fecha":     "Fecha",
            "deporte":   "Deporte",
            "Deporte":   "Deporte",
            "edad":      "Edad",
            "Edad":      "Edad",
            "peso":      "Peso_kg",
            "Peso":      "Peso_kg",
            "Peso_kg":   "Peso_kg",
            "estatura":  "Estatura_m",
            "Estatura":  "Estatura_m",
            "Estatura_m":"Estatura_m",
            "SJ":        "SJ_cm",
            "sj":        "SJ_cm",
            "SJ_cm":     "SJ_cm",
            "CMJ":       "CMJ_cm",
            "cmj":       "CMJ_cm",
            "CMJ_cm":    "CMJ_cm",
            "Abalakov":  "Abalakov_cm",
            "abalakov":  "Abalakov_cm",
            "Abalakov_cm":"Abalakov_cm",
            "IMTP":      "IMTP_N",
            "imtp":      "IMTP_N",
            "IMTP_N":    "IMTP_N",
            "F_Rel":     "F_Rel_NKg",
            "f_rel":     "F_Rel_NKg",
            "F_Rel_NKg": "F_Rel_NKg",
            "RSI":       "RSI_Mod",
            "rsi":       "RSI_Mod",
            "RSI_Mod":   "RSI_Mod",
            "Aduc":      "Aduc_N",
            "aduc":      "Aduc_N",
            "Aduc_N":    "Aduc_N",
            "Abduc":     "Abduc_N",
            "abduc":     "Abduc_N",
            "Abduc_N":   "Abduc_N",
            "Ratio":     "Ratio_AdAb",
            "ratio":     "Ratio_AdAb",
            "Ratio_AdAb":"Ratio_AdAb",
        }
        df.rename(columns=ALIAS, inplace=True)

        # Asegurarse de que siempre existan las columnas clave aunque estén vacías
        for col in ["Nombre", "Fecha", "Deporte"]:
            if col not in df.columns:
                df[col] = ""

        # Limpiar columnas numéricas
        num_cols = ["Edad","Peso_kg","Estatura_m","IMTP_N","F_Rel_NKg",
                    "SJ_cm","CMJ_cm","Abalakov_cm","RSI_Mod","Aduc_N","Abduc_N","Ratio_AdAb"]
        for col in num_cols:
            if col not in df.columns:
                df[col] = 0.0
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        return df
    except Exception as ex:
        st.warning(f"Error al cargar historial: {ex}")
        return pd.DataFrame()


def guardar_fila(cliente, fila: list) -> bool:
    try:
        hoja = cliente.open("BioSport_BD").sheet1
        # Crear encabezados si la hoja está vacía
        if len(hoja.get_all_values()) == 0:
            hoja.append_row(COLUMNAS_SHEETS)
        hoja.append_row(fila)
        return True
    except Exception as e:
        st.warning(f"No se pudo guardar en Sheets: {e}")
        return False


# ─────────────────────────────────────────────
#  CÁLCULOS
# ─────────────────────────────────────────────
def calcular_puntos(sj, cmj, abalakov, f_rel, ratio_adab) -> dict:
    """Normaliza cada métrica a escala 0-10 según los baremos."""
    def puntuar(val, max_val):
        return round(min((val / max_val) * 10, 10), 2) if max_val else 0

    equil = round(max(0, 10 - abs(1 - ratio_adab) * 20), 1) if ratio_adab else 5.0

    return {
        "Squat Jump":   puntuar(sj,       BAREMOS["SJ"]["max"]),
        "CMJ":          puntuar(cmj,      BAREMOS["CMJ"]["max"]),
        "Abalakov":     puntuar(abalakov, BAREMOS["Abalakov"]["max"]),
        "F. Relativa":  puntuar(f_rel,    BAREMOS["F_Rel"]["max"]),
        "Equilibrio":   equil,
    }


def nota_global(puntos: dict) -> float:
    return round(sum(puntos.values()) / len(puntos), 1)


def clasificar(nota: float) -> tuple[str, str]:
    """Retorna (etiqueta, color_hex)."""
    if nota >= 8:   return "ÉLITE",         "#00d4ff"
    if nota >= 6.5: return "AVANZADO",      "#00cc88"
    if nota >= 5:   return "INTERMEDIO",    "#ffa500"
    return              "EN DESARROLLO",    "#ff4b4b"


# ─────────────────────────────────────────────
#  GRÁFICOS (PLOTLY)
# ─────────────────────────────────────────────
def chart_velocimetro(titulo, valor, max_val, zona_r, zona_a, zona_v):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        title={"text": titulo, "font": {"size": 13, "color": "#c8d8f0", "family": "Inter"}},
        number={"font": {"size": 26, "color": "#ffffff"}},
        gauge={
            "axis": {"range": [0, max_val], "tickcolor": "#4a6080", "tickfont": {"color": "#4a6080", "size": 9}},
            "bar": {"color": "#00aaff", "thickness": 0.25},
            "bgcolor": "#1a2744",
            "borderwidth": 0,
            "steps": [
                {"range": zona_r, "color": "#3d1515"},
                {"range": zona_a, "color": "#3d2c0a"},
                {"range": zona_v, "color": "#0d3320"},
            ],
            "threshold": {"line": {"color": "#00d4ff", "width": 3}, "value": valor},
        },
    ))
    fig.update_layout(
        height=180,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def chart_radar(puntos_actual: dict, puntos_previo: dict | None = None):
    cats = list(puntos_actual.keys())
    fig = go.Figure()

    if puntos_previo:
        v = list(puntos_previo.values()) + [list(puntos_previo.values())[0]]
        fig.add_trace(go.Scatterpolar(
            r=v, theta=cats + [cats[0]],
            fill="toself", name="Evaluación anterior",
            line=dict(color="rgba(120,140,180,0.6)", width=1.5),
            fillcolor="rgba(120,140,180,0.08)",
        ))

    v = list(puntos_actual.values()) + [list(puntos_actual.values())[0]]
    fig.add_trace(go.Scatterpolar(
        r=v, theta=cats + [cats[0]],
        fill="toself", name="Evaluación actual",
        line=dict(color="#00aaff", width=2.5),
        fillcolor="rgba(0,170,255,0.12)",
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 10], tickfont=dict(color="#4a6080", size=9), gridcolor="#1f2d45"),
            angularaxis=dict(tickfont=dict(color="#c8d8f0", size=11)),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
        legend=dict(font=dict(color="#c8d8f0", size=11), bgcolor="rgba(0,0,0,0)"),
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=20, b=20),
    )
    return fig


def chart_evolucion(df_atleta: pd.DataFrame, metrica: str, label: str):
    if df_atleta.empty or metrica not in df_atleta.columns:
        return None
    df = df_atleta.sort_values("Fecha").tail(8)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Fecha"], y=df[metrica],
        mode="lines+markers+text",
        text=[f"{v:.1f}" for v in df[metrica]],
        textposition="top center",
        line=dict(color="#00aaff", width=2.5),
        marker=dict(size=9, color="#00d4ff"),
        textfont=dict(color="#c8d8f0", size=10),
    ))
    fig.update_layout(
        title=dict(text=f"Evolución — {label}", font=dict(color="#c8d8f0", size=13)),
        xaxis=dict(tickfont=dict(color="#4a6080"), gridcolor="#1f2d45"),
        yaxis=dict(tickfont=dict(color="#4a6080"), gridcolor="#1f2d45"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(16,26,48,0.6)",
        height=220,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def chart_barras_grupo(df: pd.DataFrame, metrica: str, label: str):
    if df.empty or metrica not in df.columns:
        return None
    df_sorted = df[["Nombre", metrica]].dropna().sort_values(metrica, ascending=True)
    colores_barra = [
        "#ff4b4b" if v < df_sorted[metrica].median() * 0.85 else
        "#ffa500" if v < df_sorted[metrica].median() * 1.1 else
        "#00cc88"
        for v in df_sorted[metrica]
    ]
    fig = go.Figure(go.Bar(
        x=df_sorted[metrica], y=df_sorted["Nombre"],
        orientation="h",
        marker_color=colores_barra,
        text=[f"{v:.1f}" for v in df_sorted[metrica]],
        textposition="outside",
        textfont=dict(color="#c8d8f0", size=10),
    ))
    fig.update_layout(
        title=dict(text=label, font=dict(color="#c8d8f0", size=13)),
        xaxis=dict(tickfont=dict(color="#4a6080"), gridcolor="#1f2d45"),
        yaxis=dict(tickfont=dict(color="#c8d8f0"), tickfont_size=11),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(16,26,48,0.6)",
        height=max(250, 35 * len(df_sorted)),
        margin=dict(l=10, r=50, t=40, b=10),
    )
    return fig


# ─────────────────────────────────────────────
#  GENERACIÓN DE PDF
# ─────────────────────────────────────────────
def _dibujar_radar_png(puntos_actual: dict, puntos_previo: dict | None = None, size=360) -> str:
    """Genera un PNG del radar en disco y retorna la ruta."""
    img = PILImage.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    r_max = 130
    n = len(puntos_actual)

    def punto(idx, radio):
        angulo = idx * (2 * math.pi / n) - math.pi / 2
        return (cx + radio * math.cos(angulo), cy + radio * math.sin(angulo))

    # Anillos de fondo
    for nivel, color_fill in enumerate([(60,20,20,80),(60,45,10,80),(10,50,30,80)], 1):
        pts = [punto(j, r_max * nivel / 3) for j in range(n)]
        draw.polygon(pts, outline=(100,130,180,120), fill=color_fill, width=1)

    # Ejes
    for j in range(n):
        draw.line([( cx, cy), punto(j, r_max)], fill=(60,90,130,160), width=1)

    # Polígono anterior
    if puntos_previo:
        pts = [punto(j, (min(v,10)/10)*r_max) for j,(k,v) in enumerate(puntos_previo.items())]
        draw.polygon(pts, outline=(160,170,190,200), fill=(120,130,150,60), width=2)

    # Polígono actual
    pts = [punto(j, (min(v,10)/10)*r_max) for j,(k,v) in enumerate(puntos_actual.items())]
    draw.polygon(pts, outline=(0,170,255,255), fill=(0,170,255,80), width=3)

    # Puntos
    for j,(k,v) in enumerate(puntos_actual.items()):
        px, py = punto(j, (min(v,10)/10)*r_max)
        draw.ellipse([(px-5, py-5),(px+5, py+5)], fill=(0,210,255,255))

    path = "/tmp/bio_radar.png"
    img.save(path)
    return path


def generar_pdf_informe(datos: dict, puntos_act: dict, puntos_prev: dict | None = None) -> BytesIO:
    """
    PDF individual 100% generado por código — sin imágenes externas.
    Página 1: Portada con identidad Bio Sport + datos del atleta + nota global.
    Página 2: Tabla de resultados + radar + detalle comparativo.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    W, H = A4   # 595.28 x 841.89 pts

    # ── Helpers de color ────────────────────────────────────────────────────
    AZUL_OSCURO  = (0.04, 0.07, 0.13)
    AZUL_MEDIO   = (0.05, 0.13, 0.25)
    AZUL_PANEL   = (0.07, 0.14, 0.26)
    AZUL_FILA_A  = (0.07, 0.12, 0.22)
    AZUL_FILA_B  = (0.05, 0.09, 0.17)
    AZUL_HEADER  = (0.04, 0.20, 0.38)
    CIAN         = (0.00, 0.83, 1.00)
    BLANCO       = (1.00, 1.00, 1.00)
    GRIS_TEXTO   = (0.78, 0.86, 0.95)
    GRIS_LABEL   = (0.49, 0.66, 0.86)
    VERDE        = (0.00, 0.80, 0.53)
    NARANJA      = (1.00, 0.65, 0.00)
    ROJO         = (1.00, 0.29, 0.29)

    def fill(rgb):  c.setFillColorRGB(*rgb)
    def stroke(rgb): c.setStrokeColorRGB(*rgb)
    def rect_f(x, y, w, h, rgb): fill(rgb); c.rect(x, y, w, h, fill=1, stroke=0)
    def rect_s(x, y, w, h, rgb, lw=1): stroke(rgb); c.setLineWidth(lw); c.rect(x, y, w, h, fill=0, stroke=1)

    nota   = nota_global(puntos_act)
    nivel_str, _ = clasificar(nota)

    # ════════════════════════════════════════════════════════════════════════
    #  PÁGINA 1 — PORTADA
    # ════════════════════════════════════════════════════════════════════════

    # Fondo total
    rect_f(0, 0, W, H, AZUL_OSCURO)

    # ── Banda superior decorativa ──────────────────────────────────────────
    rect_f(0, H - 220, W, 220, AZUL_MEDIO)

    # Acento vertical izquierdo
    rect_f(0, 0, 6, H, CIAN)

    # Línea horizontal separadora
    stroke(CIAN); c.setLineWidth(2); c.line(6, H - 220, W, H - 220)

    # Líneas decorativas paralelas (parte superior derecha)
    stroke((0.08, 0.25, 0.45)); c.setLineWidth(0.5)
    for offset in range(0, 120, 18):
        c.line(W - 160 + offset * 0.3, H - 10, W - 10, H - 160 + offset * 0.3)

    # ── Logotipo / Marca ───────────────────────────────────────────────────
    # Hexágono decorativo (símbolo)
    import math as _math
    def hexagono(cx, cy, r, color_fill, color_stroke, lw=2):
        pts = [(cx + r * _math.cos(_math.radians(60 * i - 30)),
                cy + r * _math.sin(_math.radians(60 * i - 30))) for i in range(6)]
        p = c.beginPath()
        p.moveTo(*pts[0])
        for px, py in pts[1:]: p.lineTo(px, py)
        p.close()
        fill(color_fill); c.drawPath(p, fill=1, stroke=0)
        stroke(color_stroke); c.setLineWidth(lw); c.drawPath(p, fill=0, stroke=1)

    hexagono(55, H - 68, 28, AZUL_PANEL, CIAN, 2)
    hexagono(55, H - 68, 18, AZUL_OSCURO, CIAN, 1)
    # Rayo dentro del hexágono
    fill(CIAN); c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(55, H - 74, "B")

    # Nombre de empresa
    fill(BLANCO); c.setFont("Helvetica-Bold", 26)
    c.drawString(92, H - 58, "BIO SPORT")
    fill(CIAN); c.setFont("Helvetica-Bold", 26)
    c.drawString(92 + 130, H - 58, " PRO")
    fill(GRIS_LABEL); c.setFont("Helvetica", 9)
    c.drawString(93, H - 74, "EVALUACIÓN DEPORTIVA DE ALTO RENDIMIENTO")

    # Fecha — esquina derecha
    fill(GRIS_LABEL); c.setFont("Helvetica", 9)
    c.drawRightString(W - 30, H - 58, datos["fecha"])

    # ── Bloque central: Nombre del atleta ──────────────────────────────────
    y_centro = H - 320

    fill(AZUL_PANEL)
    c.roundRect(30, y_centro - 40, W - 60, 80, 6, fill=1, stroke=0)
    rect_s(30, y_centro - 40, W - 60, 80, CIAN, 1)

    fill(CIAN); c.setFont("Helvetica", 8)
    c.drawString(48, y_centro + 30, "INFORME DE EVALUACIÓN  ·  ATLETA")
    fill(BLANCO); c.setFont("Helvetica-Bold", 22)
    c.drawString(48, y_centro + 8, datos["nombre"].upper())
    fill(GRIS_LABEL); c.setFont("Helvetica", 10)
    c.drawString(48, y_centro - 22, f"{datos['deporte'].upper()}   ·   {datos['edad']} años   ·   {datos['peso']} kg   ·   {datos['estatura']} m")

    # ── Cuatro fichas de datos personales ─────────────────────────────────
    fichas = [
        ("DEPORTE / POSICIÓN", datos["deporte"]),
        ("EDAD",    f"{datos['edad']} años"),
        ("PESO",    f"{datos['peso']} kg"),
        ("ESTATURA",f"{datos['estatura']} m"),
    ]
    ficha_w = (W - 60) / 4
    for i, (lbl, val) in enumerate(fichas):
        fx = 30 + i * ficha_w
        fy = y_centro - 130
        rect_f(fx + 2, fy, ficha_w - 4, 70, AZUL_PANEL)
        rect_s(fx + 2, fy, ficha_w - 4, 70, (0.10, 0.24, 0.44), 0.6)
        fill(GRIS_LABEL); c.setFont("Helvetica", 7)
        c.drawCentredString(fx + ficha_w / 2, fy + 54, lbl)
        fill(BLANCO); c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(fx + ficha_w / 2, fy + 32, val)
        # Línea acento inferior de cada ficha
        fill(CIAN); c.rect(fx + 2, fy, ficha_w - 4, 3, fill=1, stroke=0)

    # ── Badge Nota Global (centro de la portada) ───────────────────────────
    badge_cx = W / 2
    badge_cy = y_centro - 270

    # Círculo exterior decorativo (anillos)
    for r, alpha in [(80, 0.08), (68, 0.15), (56, 1.0)]:
        if r == 56:
            hexagono(badge_cx, badge_cy, r, AZUL_PANEL, CIAN, 2.5)
        else:
            stroke(CIAN); c.setLineWidth(0.5)
            c.setStrokeAlpha(alpha)
            c.circle(badge_cx, badge_cy, r, fill=0, stroke=1)
    c.setStrokeAlpha(1.0)

    # Nota numérica
    fill(BLANCO); c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(badge_cx, badge_cy + 2, f"{nota:.1f}")
    fill(GRIS_LABEL); c.setFont("Helvetica", 10)
    c.drawCentredString(badge_cx, badge_cy - 18, "/ 10  NOTA GLOBAL")

    # Nivel texto con rectángulo de color
    _, color_nivel = clasificar(nota)
    r_hex = tuple(int(color_nivel.lstrip("#")[i:i+2], 16) / 255 for i in (0, 2, 4))
    rect_f(badge_cx - 55, badge_cy - 50, 110, 20, r_hex)
    fill(AZUL_OSCURO); c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(badge_cx, badge_cy - 44, nivel_str)

    # ── Mini barras resumen (debajo del badge) ─────────────────────────────
    barra_y = badge_cy - 110
    barra_w_total = 320
    barra_x0 = (W - barra_w_total) / 2

    fill(GRIS_LABEL); c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(W / 2, barra_y + 20, "PERFIL DE CAPACIDADES")

    for i, (cat, val) in enumerate(puntos_act.items()):
        bx = barra_x0
        by = barra_y - i * 22
        # Etiqueta
        fill(GRIS_LABEL); c.setFont("Helvetica", 8)
        c.drawString(bx, by, cat)
        # Fondo barra
        rect_f(bx + 110, by, barra_w_total - 110, 10, (0.08, 0.14, 0.26))
        # Barra anterior (gris)
        if puntos_prev and cat in puntos_prev:
            vp = min(puntos_prev[cat], 10) / 10
            fill((0.35, 0.42, 0.55)); c.rect(bx + 110, by, (barra_w_total - 110) * vp, 10, fill=1, stroke=0)
        # Barra actual
        va = min(val, 10) / 10
        color_b = VERDE if val >= 6.5 else NARANJA if val >= 5 else ROJO
        rect_f(bx + 110, by, (barra_w_total - 110) * va, 10, color_b)
        # Valor
        fill(BLANCO); c.setFont("Helvetica-Bold", 8)
        c.drawRightString(bx + barra_w_total + 28, by + 2, f"{val:.1f}")

    if puntos_prev:
        fill(GRIS_LABEL); c.setFont("Helvetica", 7)
        bx_legend = barra_x0 + 110
        by_legend = barra_y - len(puntos_act) * 22 - 10
        rect_f(bx_legend, by_legend, 10, 8, (0.35, 0.42, 0.55))
        c.drawString(bx_legend + 14, by_legend, "Evaluación anterior")

    # ── Pie de página ──────────────────────────────────────────────────────
    rect_f(0, 0, W, 28, (0.03, 0.05, 0.10))
    stroke((0.08, 0.20, 0.38)); c.setLineWidth(0.5); c.line(6, 28, W, 28)
    fill(GRIS_LABEL); c.setFont("Helvetica", 7)
    c.drawString(20, 10, "Bio Sport Pro  ·  Evaluación Deportiva de Alto Rendimiento")
    c.drawRightString(W - 20, 10, f"Página 1 de 2  ·  {datos['fecha']}")

    # ════════════════════════════════════════════════════════════════════════
    #  PÁGINA 2 — DETALLE TÉCNICO
    # ════════════════════════════════════════════════════════════════════════
    c.showPage()
    rect_f(0, 0, W, H, AZUL_OSCURO)
    rect_f(0, 0, 6, H, CIAN)

    # Encabezado página 2
    rect_f(0, H - 60, W, 60, AZUL_MEDIO)
    stroke(CIAN); c.setLineWidth(1.5); c.line(6, H - 60, W, H - 60)
    fill(BLANCO); c.setFont("Helvetica-Bold", 13)
    c.drawString(24, H - 35, "RESULTADOS TÉCNICOS")
    fill(GRIS_LABEL); c.setFont("Helvetica", 9)
    c.drawString(24, H - 50, f"{datos['nombre'].upper()}  ·  {datos['deporte']}  ·  {datos['fecha']}")
    # Número de página
    fill(GRIS_LABEL); c.setFont("Helvetica", 8)
    c.drawRightString(W - 20, H - 38, "02")

    # ── Tabla de pruebas ────────────────────────────────────────────────────
    y_t = H - 80

    metricas_tabla = [
        ("Squat Jump (SJ)",   datos["sj"],      "cm",   BAREMOS["SJ"]["max"]),
        ("CMJ",               datos["cmj"],     "cm",   BAREMOS["CMJ"]["max"]),
        ("Abalakov",          datos["abalakov"],"cm",   BAREMOS["Abalakov"]["max"]),
        ("IMTP",              datos["imtp"],    "N",    None),
        ("Fuerza Relativa",   datos["f_rel"],   "N/kg", BAREMOS["F_Rel"]["max"]),
        ("RSI Modificado",    datos["rsi"],     "",     BAREMOS["RSI"]["max"]),
        ("Ratio Aduc/Abduc",  datos["ratio"],   "",     None),
    ]

    col_x = [24, 180, 285, 355, 470]  # Prueba | Resultado | Barra+Puntaje | Nivel
    fila_h = 24

    # Encabezado tabla
    rect_f(6, y_t - fila_h, W - 6, fila_h, AZUL_HEADER)
    headers = ["PRUEBA", "RESULTADO", "RENDIMIENTO", "PUNT.", "NIVEL"]
    for hx, htxt in zip(col_x, headers):
        fill(CIAN); c.setFont("Helvetica-Bold", 8)
        c.drawString(hx + 6, y_t - fila_h + 8, htxt)
    y_t -= fila_h

    for i, (prueba, val_raw, unidad, max_v) in enumerate(metricas_tabla):
        bg = AZUL_FILA_A if i % 2 == 0 else AZUL_FILA_B
        rect_f(6, y_t - fila_h, W - 6, fila_h, bg)

        # Nombre prueba
        fill(GRIS_TEXTO); c.setFont("Helvetica", 9)
        c.drawString(col_x[0] + 6, y_t - fila_h + 8, prueba)

        # Resultado
        val_fmt = f"{val_raw:.2f}".rstrip("0").rstrip(".") if isinstance(val_raw, float) else str(val_raw)
        fill(BLANCO); c.setFont("Helvetica-Bold", 9)
        c.drawString(col_x[1] + 6, y_t - fila_h + 8, f"{val_fmt} {unidad}".strip())

        if max_v and float(val_raw) > 0:
            puntaje = min((float(val_raw) / max_v) * 10, 10)
            color_b = VERDE if puntaje >= 6.5 else NARANJA if puntaje >= 5 else ROJO

            # Barra de progreso
            bx = col_x[2] + 6
            bw = 90
            by_bar = y_t - fila_h + 8
            rect_f(bx, by_bar, bw, 8, (0.08, 0.14, 0.26))
            rect_f(bx, by_bar, bw * (puntaje / 10), 8, color_b)

            # Puntaje numérico
            fill(BLANCO); c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(col_x[3] + 20, y_t - fila_h + 8, f"{puntaje:.1f}/10")

            # Nivel badge
            rect_f(col_x[4] + 2, y_t - fila_h + 5, 90, 14, color_b)
            nivel_lbl, _ = clasificar(puntaje)
            fill(AZUL_OSCURO); c.setFont("Helvetica-Bold", 7)
            c.drawCentredString(col_x[4] + 47, y_t - fila_h + 10, nivel_lbl)
        else:
            fill(GRIS_LABEL); c.setFont("Helvetica", 8)
            c.drawString(col_x[2] + 6, y_t - fila_h + 8, "—")

        y_t -= fila_h

    # ── Sección inferior: Radar izquierda + Detalle comparativo derecha ────
    y_seccion = y_t - 20
    seccion_h = 220

    # Título sección
    fill(CIAN); c.setFont("Helvetica-Bold", 8)
    c.drawString(24, y_seccion, "PERFIL RADAR DE CAPACIDADES")

    # Dibujar radar directamente en PDF (sin imagen externa)
    radar_cx = 130
    radar_cy = y_seccion - 110
    radar_r  = 85
    n_pts    = len(puntos_act)
    cats     = list(puntos_act.keys())

    def radar_punto(idx, radio):
        ang = idx * (2 * _math.pi / n_pts) - _math.pi / 2
        return radar_cx + radio * _math.cos(ang), radar_cy + radio * _math.sin(ang)

    # Anillos de fondo
    for nivel_r in [1, 2, 3]:
        r_ring = radar_r * nivel_r / 3
        pts_ring = [radar_punto(j, r_ring) for j in range(n_pts)]
        p = c.beginPath()
        p.moveTo(*pts_ring[0])
        for px2, py2 in pts_ring[1:]: p.lineTo(px2, py2)
        p.close()
        ring_colors = [(0.18,0.07,0.07), (0.18,0.14,0.04), (0.04,0.18,0.12)]
        fill(ring_colors[nivel_r - 1]); c.drawPath(p, fill=1, stroke=0)
        stroke((0.12, 0.22, 0.38)); c.setLineWidth(0.4); c.drawPath(p, fill=0, stroke=1)

    # Ejes
    stroke((0.15, 0.28, 0.48)); c.setLineWidth(0.6)
    for j in range(n_pts):
        ex, ey = radar_punto(j, radar_r)
        c.line(radar_cx, radar_cy, ex, ey)

    # Polígono anterior
    if puntos_prev:
        pts_prev_poly = [radar_punto(j, (min(puntos_prev.get(k, 0), 10) / 10) * radar_r)
                         for j, k in enumerate(cats)]
        p = c.beginPath()
        p.moveTo(*pts_prev_poly[0])
        for px2, py2 in pts_prev_poly[1:]: p.lineTo(px2, py2)
        p.close()
        fill((0.25, 0.30, 0.40)); c.drawPath(p, fill=1, stroke=0)
        stroke((0.45, 0.55, 0.70)); c.setLineWidth(1.2); c.drawPath(p, fill=0, stroke=1)

    # Polígono actual
    pts_act_poly = [radar_punto(j, (min(v, 10) / 10) * radar_r) for j, (k, v) in enumerate(puntos_act.items())]
    p = c.beginPath()
    p.moveTo(*pts_act_poly[0])
    for px2, py2 in pts_act_poly[1:]: p.lineTo(px2, py2)
    p.close()
    fill((0.0, 0.42, 0.70)); c.drawPath(p, fill=1, stroke=0)
    stroke(CIAN); c.setLineWidth(2); c.drawPath(p, fill=0, stroke=1)

    # Puntos y etiquetas
    for j, (k, v) in enumerate(puntos_act.items()):
        px2, py2 = radar_punto(j, (min(v, 10) / 10) * radar_r)
        fill(CIAN); c.circle(px2, py2, 3.5, fill=1, stroke=0)
        # Etiqueta exterior
        lx, ly = radar_punto(j, radar_r + 14)
        fill(GRIS_TEXTO); c.setFont("Helvetica", 7)
        c.drawCentredString(lx, ly - 3, k)

    # ── Detalle comparativo (derecha) ──────────────────────────────────────
    dx = 260
    dy = y_seccion - 10

    fill(CIAN); c.setFont("Helvetica-Bold", 8)
    c.drawString(dx, dy, "DETALLE COMPARATIVO")
    dy -= 16

    for cat, val in puntos_act.items():
        # Fondo fila
        rect_f(dx, dy - 4, W - dx - 20, 20, AZUL_FILA_A)

        fill(GRIS_TEXTO); c.setFont("Helvetica", 8)
        c.drawString(dx + 5, dy + 2, cat)

        # Valor actual
        color_v = VERDE if val >= 6.5 else NARANJA if val >= 5 else ROJO
        fill(color_v); c.setFont("Helvetica-Bold", 9)
        c.drawRightString(dx + 120, dy + 2, f"{val:.1f}")

        # Flecha comparativa si hay datos previos
        if puntos_prev and cat in puntos_prev:
            vp = puntos_prev[cat]
            diff = val - vp
            if diff > 0.2:
                fill(VERDE); arrow = f"▲ +{diff:.1f}"
            elif diff < -0.2:
                fill(ROJO); arrow = f"▼ {diff:.1f}"
            else:
                fill(GRIS_LABEL); arrow = "= ="
            c.setFont("Helvetica-Bold", 8)
            c.drawString(dx + 130, dy + 2, arrow)

            fill(GRIS_LABEL); c.setFont("Helvetica", 7)
            c.drawRightString(W - 26, dy + 2, f"ant: {vp:.1f}")

        dy -= 22

    if puntos_prev:
        dy -= 4
        fill(GRIS_LABEL); c.setFont("Helvetica", 7)
        c.drawString(dx, dy, "▲▼ variación respecto evaluación anterior")

    # Badge nota global (debajo del detalle)
    badge2_cx = dx + 100
    badge2_cy = dy - 55
    hexagono(badge2_cx, badge2_cy, 42, AZUL_PANEL, CIAN, 2)
    fill(BLANCO); c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(badge2_cx, badge2_cy + 4, f"{nota:.1f}")
    fill(GRIS_LABEL); c.setFont("Helvetica", 7)
    c.drawCentredString(badge2_cx, badge2_cy - 10, "NOTA GLOBAL / 10")
    _, color_nivel = clasificar(nota)
    r_hex2 = tuple(int(color_nivel.lstrip("#")[i:i+2], 16)/255 for i in (0,2,4))
    rect_f(badge2_cx - 38, badge2_cy - 30, 76, 14, r_hex2)
    fill(AZUL_OSCURO); c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(badge2_cx, badge2_cy - 24, nivel_str)

    # ── Pie de página p2 ───────────────────────────────────────────────────
    rect_f(0, 0, W, 28, (0.03, 0.05, 0.10))
    stroke((0.08, 0.20, 0.38)); c.setLineWidth(0.5); c.line(6, 28, W, 28)
    fill(GRIS_LABEL); c.setFont("Helvetica", 7)
    c.drawString(20, 10, "Bio Sport Pro  ·  Evaluación Deportiva de Alto Rendimiento")
    c.drawRightString(W - 20, 10, f"Página 2 de 2  ·  {datos['fecha']}")

    c.save()
    buffer.seek(0)
    return buffer


def generar_pdf_grupal(df: pd.DataFrame) -> BytesIO:
    """PDF resumen para un grupo de atletas."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    ancho, alto = A4

    c.setFillColorRGB(0.04, 0.07, 0.13)
    c.rect(0, 0, ancho, alto, fill=1, stroke=0)
    c.setFillColorRGB(0.05, 0.13, 0.25)
    c.rect(0, alto - 100, ancho, 100, fill=1, stroke=0)
    c.setStrokeColorRGB(0, 0.83, 1)
    c.setLineWidth(3)
    c.line(0, alto - 100, ancho, alto - 100)

    c.setFillColorRGB(0, 0.83, 1)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, alto - 50, "⚡ BIO SPORT PRO — INFORME GRUPAL")
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.5, 0.7, 0.9)
    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
    c.drawString(40, alto - 70, f"Generado el {fecha_hoy}  ·  {len(df)} atletas evaluados")

    # Tabla — solo columnas que existan en el df
    _cols_candidatos = [
        ("Nombre","Nombre"), ("Deporte","Deporte"), ("SJ_cm","SJ"),
        ("CMJ_cm","CMJ"), ("Abalakov_cm","Abalakov"), ("F_Rel_NKg","F.Rel"), ("RSI_Mod","RSI"),
    ]
    cols_mostrar = [c for c, _ in _cols_candidatos if c in df.columns]
    cols_labels  = [lbl for c, lbl in _cols_candidatos if c in df.columns]
    df_show = df[cols_mostrar].tail(50).copy()

    tabla_data = [cols_labels]
    for _, row in df_show.iterrows():
        tabla_data.append([str(row[c])[:18] for c in cols_mostrar])

    _all_widths = [110, 80, 50, 50, 55, 50, 50]
    t = Table(tabla_data, colWidths=_all_widths[:len(cols_mostrar)])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), colors.HexColor("#0f3460")),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.HexColor("#00d4ff")),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 8),
        ("BACKGROUND",   (0, 1), (-1, -1), colors.HexColor("#0d1627")),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.HexColor("#111827"), colors.HexColor("#0d1627")]),
        ("TEXTCOLOR",    (0, 1), (-1, -1), colors.HexColor("#c8d8f0")),
        ("FONTSIZE",     (0, 1), (-1, -1), 8),
        ("ALIGN",        (2, 0), (-1, -1), "CENTER"),
        ("GRID",         (0, 0), (-1, -1), 0.3, colors.HexColor("#1f2d45")),
        ("ROWHEIGHT",    (0, 0), (-1, -1), 16),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
    ]))
    t.wrapOn(c, ancho - 80, alto)
    t.drawOn(c, 40, alto - 150 - len(tabla_data) * 17)

    c.setFillColorRGB(0.04, 0.07, 0.13)
    c.rect(0, 0, ancho, 30, fill=1, stroke=0)
    c.setFont("Helvetica", 7)
    c.setFillColorRGB(0.35, 0.50, 0.70)
    c.drawString(40, 10, "Generado por Bio Sport Pro  ·  Informe Grupal")
    c.drawRightString(ancho - 40, 10, fecha_hoy)

    c.save()
    buffer.seek(0)
    return buffer


# ─────────────────────────────────────────────
#  CARGA INICIAL
# ─────────────────────────────────────────────
cliente_sheets = conectar_sheets()
data_historica  = cargar_historial(cliente_sheets)

lista_atletas = ["➕ Nuevo Atleta"]
if not data_historica.empty and "Nombre" in data_historica.columns:
    nombres_unicos = sorted(data_historica["Nombre"].dropna().unique().tolist())
    lista_atletas += [n for n in nombres_unicos if n]


# ─────────────────────────────────────────────
#  ENCABEZADO HERO
# ─────────────────────────────────────────────
col_logo, col_titulo = st.columns([1, 6])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=80)
    else:
        st.markdown("<div style='font-size:3rem;'>⚡</div>", unsafe_allow_html=True)
with col_titulo:
    st.markdown("""
    <div style="padding:12px 0">
      <p class="hero-title">Bio Sport <span class="accent">Pro</span></p>
      <p class="hero-subtitle">Plataforma de Evaluación Deportiva de Alto Rendimiento</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ─────────────────────────────────────────────
#  TABS PRINCIPALES
# ─────────────────────────────────────────────
tab_eval, tab_historial, tab_grupo = st.tabs([
    "📋 Nueva Evaluación",
    "📈 Historial Individual",
    "👥 Informe Grupal",
])


# ════════════════════════════════════════════════
#  TAB 1 — NUEVA EVALUACIÓN
# ════════════════════════════════════════════════
with tab_eval:
    # ── Seleccionar atleta ────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">Identificación del Atleta</p>', unsafe_allow_html=True)

    c_sel, c_new = st.columns([2, 3])
    with c_sel:
        atleta_sel = st.selectbox("Buscar en historial", lista_atletas, label_visibility="visible")
    with c_new:
        valor_nombre = "" if atleta_sel == "➕ Nuevo Atleta" else atleta_sel
        nombre = st.text_input("Nombre completo", value=valor_nombre, placeholder="Ej: Carlos Pérez")

    c1, c2, c3, c4 = st.columns(4)
    with c1: edad     = st.number_input("Edad", min_value=10, max_value=60, step=1, value=22)
    with c2: peso     = st.number_input("Peso (kg)", min_value=30.0, max_value=180.0, step=0.1, value=75.0)
    with c3: estatura = st.number_input("Estatura (m)", min_value=1.40, max_value=2.20, step=0.01, value=1.75)
    with c4: deporte  = st.text_input("Deporte / Posición", value="Fútbol", placeholder="Ej: Basquetbol")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Pruebas de salto ──────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">Pruebas de Potencia y Salto</p>', unsafe_allow_html=True)

    p1, p2, p3, p4 = st.columns(4)
    with p1: sj       = st.number_input("SJ (cm)",       min_value=0.0, max_value=100.0, step=0.1, value=0.0, help="Squat Jump")
    with p2: cmj      = st.number_input("CMJ (cm)",      min_value=0.0, max_value=100.0, step=0.1, value=0.0, help="Counter Movement Jump")
    with p3: abalakov = st.number_input("Abalakov (cm)", min_value=0.0, max_value=100.0, step=0.1, value=0.0)
    with p4: rsi      = st.number_input("RSI Modificado",min_value=0.0, max_value=5.0,   step=0.01, value=0.0, help="Reactive Strength Index")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Fuerza ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">Fuerza Isométrica y Dinamometría</p>', unsafe_allow_html=True)

    f1, f2, f3 = st.columns(3)
    with f1: imtp  = st.number_input("IMTP (N)",        min_value=0.0, step=10.0, value=0.0, help="Isometric Mid-Thigh Pull")
    with f2: aduc  = st.number_input("Aductores (N)",   min_value=0.0, step=1.0,  value=0.0)
    with f3: abduc = st.number_input("Abductores (N)",  min_value=0.0, step=1.0,  value=0.0)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Preview en vivo ───────────────────────────────────────────────────
    if any([sj > 0, cmj > 0, abalakov > 0, imtp > 0]):
        f_rel_live = round(imtp / peso, 1) if peso > 0 else 0
        ratio_live = round(aduc / abduc, 2) if abduc > 0 else 1.0
        pts_live   = calcular_puntos(sj, cmj, abalakov, f_rel_live, ratio_live)
        nota_live  = nota_global(pts_live)
        nivel_live, color_live = clasificar(nota_live)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Vista Previa en Tiempo Real</p>', unsafe_allow_html=True)

        # Chips de puntuaciones
        chips_html = '<div class="metric-row">'
        for cat, val in pts_live.items():
            chips_html += f"""
            <div class="metric-chip">
                <div class="val">{val:.1f}</div>
                <div class="lbl">{cat}</div>
            </div>"""
        chips_html += f"""
        <div class="metric-chip" style="border-color:#00d4ff;">
            <div class="val" style="color:#fff">{nota_live}</div>
            <div class="lbl" style="color:{color_live}">{nivel_live}</div>
        </div>"""
        chips_html += '</div>'
        st.markdown(chips_html, unsafe_allow_html=True)

        # Velocímetros
        vm1, vm2, vm3 = st.columns(3)
        with vm1: st.plotly_chart(chart_velocimetro("Squat Jump", sj, BAREMOS["SJ"]["max"],
            [0, BAREMOS["SJ"]["max"]*0.5], [BAREMOS["SJ"]["max"]*0.5, BAREMOS["SJ"]["max"]*0.7],
            [BAREMOS["SJ"]["max"]*0.7, BAREMOS["SJ"]["max"]]), use_container_width=True)
        with vm2: st.plotly_chart(chart_velocimetro("CMJ", cmj, BAREMOS["CMJ"]["max"],
            [0, BAREMOS["CMJ"]["max"]*0.5], [BAREMOS["CMJ"]["max"]*0.5, BAREMOS["CMJ"]["max"]*0.7],
            [BAREMOS["CMJ"]["max"]*0.7, BAREMOS["CMJ"]["max"]]), use_container_width=True)
        with vm3: st.plotly_chart(chart_velocimetro("RSI Mod.", rsi, BAREMOS["RSI"]["max"],
            [0, BAREMOS["RSI"]["max"]*0.33], [BAREMOS["RSI"]["max"]*0.33, BAREMOS["RSI"]["max"]*0.55],
            [BAREMOS["RSI"]["max"]*0.55, BAREMOS["RSI"]["max"]]), use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # ── Guardar ───────────────────────────────────────────────────────────
    st.markdown("")
    confirmar = st.toggle("✅ Confirmo que los datos son correctos y están listos para guardar")
    col_btn1, col_btn2 = st.columns([3, 1])
    with col_btn1:
        btn_guardar = st.button(
            "💾 GUARDAR Y GENERAR INFORME PDF",
            type="primary",
            use_container_width=True,
            disabled=not confirmar,
        )

    # ── Procesamiento ─────────────────────────────────────────────────────
    if btn_guardar:
        errores = []
        if not nombre.strip():    errores.append("El nombre del atleta es obligatorio.")
        if peso <= 0:             errores.append("El peso debe ser mayor a 0.")
        if all(v == 0 for v in [sj, cmj, abalakov, imtp]):
            errores.append("Registra al menos una prueba de rendimiento.")

        if errores:
            for e in errores:
                st.error(f"⚠️ {e}")
        else:
            f_rel = round(imtp / peso, 1) if peso > 0 else 0
            ratio = round(aduc / abduc, 2) if abduc > 0 else 1.0
            fecha = datetime.now().strftime("%d/%m/%Y")

            datos_eval = {
                "nombre": nombre.strip(), "edad": int(edad), "peso": round(peso, 1),
                "estatura": round(estatura, 2), "deporte": deporte, "fecha": fecha,
                "cmj": cmj, "sj": sj, "abalakov": abalakov,
                "imtp": imtp, "f_rel": f_rel, "rsi": rsi,
                "aduc": aduc, "abduc": abduc, "ratio": ratio,
            }

            # Búsqueda eval previa
            eval_previa = None
            if not data_historica.empty and "Nombre" in data_historica.columns:
                mask = data_historica["Nombre"] == nombre.strip()
                if mask.any():
                    eval_previa = data_historica[mask].iloc[-1].to_dict()

            # Guardar en Sheets
            if cliente_sheets:
                fila = [fecha, datos_eval["nombre"], edad, peso, estatura, deporte,
                        imtp, f_rel, sj, cmj, abalakov, rsi, aduc, abduc, ratio]
                guardado = guardar_fila(cliente_sheets, fila)
                if guardado:
                    st.success("✅ Evaluación guardada en Google Sheets.")
                    # Limpiar cache para que el historial se actualice
                    cargar_historial.clear()
            else:
                st.info("ℹ️ Sin conexión a Google Sheets — el PDF se genera igual.")

            # Puntos actuales
            puntos_act = calcular_puntos(sj, cmj, abalakov, f_rel, ratio)

            # Puntos previos
            puntos_prev = None
            if eval_previa:
                try:
                    puntos_prev = calcular_puntos(
                        float(eval_previa.get("SJ_cm", 0)),
                        float(eval_previa.get("CMJ_cm", 0)),
                        float(eval_previa.get("Abalakov_cm", 0)),
                        float(eval_previa.get("F_Rel_NKg", 0)),
                        float(eval_previa.get("Ratio_AdAb", 1)),
                    )
                except Exception:
                    pass

            with st.spinner("Generando informe PDF…"):
                pdf_buffer = generar_pdf_informe(datos_eval, puntos_act, puntos_prev)

            st.session_state.informe_actual = {
                "datos": datos_eval,
                "pdf": pdf_buffer,
                "radar_act": puntos_act,
                "radar_prev": puntos_prev,
                "eval_previa": eval_previa,
            }

    # ── Resultado / Descarga ───────────────────────────────────────────────
    if st.session_state.informe_actual:
        inf = st.session_state.informe_actual
        d   = inf["datos"]
        ra  = inf["radar_act"]
        rp  = inf["radar_prev"]
        nota = nota_global(ra)
        nivel, color_nivel = clasificar(nota)

        st.divider()
        st.markdown(f"### 📊 Resultados — {d['nombre']}")

        # Badge nota global + radar
        col_badge, col_radar = st.columns([1, 2])
        with col_badge:
            st.markdown(f"""
            <div style="text-align:center;margin-top:20px">
                <div class="score-badge">
                    <span class="num">{nota}</span>
                    <span class="denom">/ 10</span>
                </div>
                <p style="font-size:1rem;font-weight:700;color:{color_nivel};letter-spacing:1px;margin-top:8px">{nivel}</p>
                <p style="font-size:0.8rem;color:#7ea8d8">{d['fecha']}</p>
            </div>
            """, unsafe_allow_html=True)

        with col_radar:
            st.plotly_chart(chart_radar(ra, rp), use_container_width=True)

        if rp:
            st.info("💡 La sombra semitransparente del radar representa la evaluación anterior del atleta.")

        # Velocímetros principales post-guardado
        v1, v2 = st.columns(2)
        with v1: st.plotly_chart(chart_velocimetro(
            "CMJ", d["cmj"], BAREMOS["CMJ"]["max"],
            [0,30],[30,42],[42,BAREMOS["CMJ"]["max"]]), use_container_width=True)
        with v2: st.plotly_chart(chart_velocimetro(
            "RSI Modificado", d["rsi"], BAREMOS["RSI"]["max"],
            [0,1],[1,1.5],[1.5,BAREMOS["RSI"]["max"]]), use_container_width=True)

        # Descarga
        st.download_button(
            label="📥 DESCARGAR INFORME OFICIAL (PDF)",
            data=inf["pdf"],
            file_name=f"BioSport_{d['nombre'].replace(' ','_')}_{d['fecha'].replace('/','')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


# ════════════════════════════════════════════════
#  TAB 2 — HISTORIAL INDIVIDUAL
# ════════════════════════════════════════════════
with tab_historial:
    _col_nombre_ok = not data_historica.empty and "Nombre" in data_historica.columns
    if not _col_nombre_ok:
        st.info("Aún no hay evaluaciones guardadas. Completa una evaluación para empezar.")
    else:
        nombres_hist = sorted([n for n in data_historica["Nombre"].dropna().unique().tolist() if str(n).strip()])
        if not nombres_hist:
            st.info("No se encontraron atletas en el historial.")
        else:
            atleta_hist = st.selectbox("Seleccionar atleta", nombres_hist, key="hist_sel")
            df_at = data_historica[data_historica["Nombre"] == atleta_hist].copy()

            if df_at.empty:
                st.warning("No hay registros para este atleta.")
            else:
                st.markdown(f"**{len(df_at)} evaluación(es) encontrada(s)**")

                # Última evaluación
                ultima = df_at.iloc[-1]
                col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
                metrics = [
                    ("SJ", "SJ_cm", "cm"), ("CMJ", "CMJ_cm", "cm"),
                    ("Abalakov", "Abalakov_cm", "cm"), ("F. Relativa", "F_Rel_NKg", "N/kg"), ("RSI", "RSI_Mod", ""),
                ]
                for col, (lab, col_key, uni) in zip([col_m1,col_m2,col_m3,col_m4,col_m5], metrics):
                    val = float(ultima.get(col_key, 0) or 0)
                    col.metric(label=lab, value=f"{val:.1f} {uni}".strip())

                # Gráficos de evolución
                st.markdown("#### Evolución Histórica")
                evo_cols = [
                    ("SJ_cm", "Squat Jump (cm)"),
                    ("CMJ_cm", "CMJ (cm)"),
                    ("Abalakov_cm", "Abalakov (cm)"),
                    ("F_Rel_NKg", "Fuerza Relativa (N/kg)"),
                ]
                for col_a, col_b in zip(evo_cols[::2], evo_cols[1::2]):
                    c1e, c2e = st.columns(2)
                    with c1e:
                        fig = chart_evolucion(df_at, col_a[0], col_a[1])
                        if fig: st.plotly_chart(fig, use_container_width=True)
                    with c2e:
                        fig = chart_evolucion(df_at, col_b[0], col_b[1])
                        if fig: st.plotly_chart(fig, use_container_width=True)

                # Tabla completa
                with st.expander("Ver tabla completa de evaluaciones"):
                    st.dataframe(df_at, use_container_width=True)


# ════════════════════════════════════════════════
#  TAB 3 — INFORME GRUPAL
# ════════════════════════════════════════════════
with tab_grupo:
    if data_historica.empty or "Nombre" not in data_historica.columns:
        st.info("Aún no hay evaluaciones en el sistema.")
    else:
        st.markdown("#### Comparativa del Grupo")

        # Filtro por deporte
        if "Deporte" in data_historica.columns:
            deportes_lista = sorted(data_historica["Deporte"].dropna().unique().tolist())
        else:
            deportes_lista = []
        deportes_disponibles = ["Todos"] + deportes_lista
        deporte_filtro = st.selectbox("Filtrar por deporte / posición", deportes_disponibles)

        df_grupo = data_historica.copy()
        if deporte_filtro != "Todos" and "Deporte" in df_grupo.columns:
            df_grupo = df_grupo[df_grupo["Deporte"] == deporte_filtro]

        # Tomar la evaluación más reciente por atleta
        if "Fecha" in df_grupo.columns and "Nombre" in df_grupo.columns:
            try:
                df_grupo = df_grupo.sort_values("Fecha").groupby("Nombre").last().reset_index()
            except Exception:
                pass

        st.markdown(f"**{len(df_grupo)} atleta(s) en el grupo**")

        # Gráficos de barras por métrica
        metricas_grupo = [
            ("CMJ_cm", "CMJ (cm)"),
            ("SJ_cm", "Squat Jump (cm)"),
            ("F_Rel_NKg", "Fuerza Relativa (N/kg)"),
            ("RSI_Mod", "RSI Modificado"),
        ]
        for col_a, col_b in zip(metricas_grupo[::2], metricas_grupo[1::2]):
            c1g, c2g = st.columns(2)
            with c1g:
                fig = chart_barras_grupo(df_grupo, col_a[0], col_a[1])
                if fig: st.plotly_chart(fig, use_container_width=True)
            with c2g:
                fig = chart_barras_grupo(df_grupo, col_b[0], col_b[1])
                if fig: st.plotly_chart(fig, use_container_width=True)

        # Tabla resumen
        st.markdown("#### Tabla Resumen")
        cols_display = [c for c in ["Nombre","Deporte","Fecha","SJ_cm","CMJ_cm","Abalakov_cm","F_Rel_NKg","RSI_Mod"] if c in df_grupo.columns]
        if cols_display:
            st.dataframe(df_grupo[cols_display], use_container_width=True)
        else:
            st.dataframe(df_grupo, use_container_width=True)

        # Descarga PDF grupal
        with st.spinner("Preparando PDF grupal…"):
            pdf_grupo = generar_pdf_grupal(df_grupo)

        nombre_archivo = f"BioSport_Grupal_{deporte_filtro.replace(' ','_')}_{datetime.now().strftime('%d%m%Y')}.pdf"
        st.download_button(
            label="📥 DESCARGAR INFORME GRUPAL (PDF)",
            data=pdf_grupo,
            file_name=nombre_archivo,
            mime="application/pdf",
            use_container_width=True,
        )
