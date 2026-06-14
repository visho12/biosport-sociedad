"""
Bio Sport Pro — Versión 4.0
Fusión completa: baremos por deporte, módulos COD/VO2/F-V,
arquitectura reactiva blindada, PDF mejorado, hoja de cálculo ordenada.
"""

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
from reportlab.platypus import Table, TableStyle
import math
import os

# ─────────────────────────────────────────────
#  BAREMOS POR DEPORTE (referencia élite)
# ─────────────────────────────────────────────
BAREMOS_DEPORTIVOS = {
    "Fútbol":                 {"SJ":46.0,"CMJ":56.0,"Abalakov":66.0,"F_Rel":35.0,"RSI":2.6},
    "Básquetbol":             {"SJ":55.0,"CMJ":68.0,"Abalakov":78.0,"F_Rel":35.0,"RSI":3.0},
    "Voleibol":               {"SJ":60.0,"CMJ":75.0,"Abalakov":88.0,"F_Rel":32.0,"RSI":3.2},
    "Rugby":                  {"SJ":48.0,"CMJ":58.0,"Abalakov":68.0,"F_Rel":40.0,"RSI":2.4},
    "Atletismo (Velocidad)":  {"SJ":55.0,"CMJ":65.0,"Abalakov":75.0,"F_Rel":45.0,"RSI":3.0},
    "General / Recreacional": {"SJ":40.0,"CMJ":48.0,"Abalakov":58.0,"F_Rel":28.0,"RSI":2.2},
}

COLUMNAS_SHEETS = [
    "Fecha","Nombre","Edad","Peso_kg","Estatura_m","Deporte",
    "IMTP_N","F_Rel_NKg","SJ_cm","CMJ_cm","Abalakov_cm",
    "RSI_Mod","Aduc_N","Abduc_N","Ratio_AdAb",
    "Sprint_10m_s","Agilidad_505_s","COD_Deficit_s",
    "YoYo_Dist_m","VO2Max","VAM_kmh",
    "SJ_20kg_cm","SJ_40kg_cm"
]

ALIAS_COLUMNAS = {
    "nombre":"Nombre","fecha":"Fecha","deporte":"Deporte","edad":"Edad",
    "peso":"Peso_kg","Peso":"Peso_kg","estatura":"Estatura_m","Estatura":"Estatura_m",
    "SJ":"SJ_cm","sj":"SJ_cm","CMJ":"CMJ_cm","cmj":"CMJ_cm",
    "Abalakov":"Abalakov_cm","abalakov":"Abalakov_cm",
    "IMTP":"IMTP_N","imtp":"IMTP_N","F_Rel":"F_Rel_NKg","f_rel":"F_Rel_NKg",
    "RSI":"RSI_Mod","rsi":"RSI_Mod","Aduc":"Aduc_N","aduc":"Aduc_N",
    "Abduc":"Abduc_N","abduc":"Abduc_N","Ratio":"Ratio_AdAb","ratio":"Ratio_AdAb",
}

NUM_COLS = [
    "Edad","Peso_kg","Estatura_m","IMTP_N","F_Rel_NKg",
    "SJ_cm","CMJ_cm","Abalakov_cm","RSI_Mod","Aduc_N","Abduc_N","Ratio_AdAb",
    "Sprint_10m_s","Agilidad_505_s","COD_Deficit_s",
    "YoYo_Dist_m","VO2Max","VAM_kmh","SJ_20kg_cm","SJ_40kg_cm"
]

# ─────────────────────────────────────────────
#  PAGE CONFIG & CSS
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Bio Sport Pro", page_icon="⚡",
    layout="wide", initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.stApp{background:#0a0e1a;color:#e8eaf0;}
.hero-title{font-size:2.2rem;font-weight:900;letter-spacing:-.5px;color:#fff;margin:0;}
.hero-subtitle{font-size:.95rem;color:#7ea8d8;margin:4px 0 0;font-weight:400;}
.accent{color:#00d4ff;}
.section-card{background:#111827;border:1px solid #1f2d45;border-radius:12px;padding:24px 28px;margin-bottom:20px;}
.section-title{font-size:.75rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#00d4ff;margin-bottom:16px;}
.metric-row{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px;}
.metric-chip{background:#1a2744;border:1px solid #2a3f6f;border-radius:10px;padding:14px 20px;min-width:130px;flex:1;text-align:center;}
.metric-chip .val{font-size:1.7rem;font-weight:700;color:#00d4ff;line-height:1;}
.metric-chip .lbl{font-size:.72rem;color:#8899bb;margin-top:4px;font-weight:600;letter-spacing:1px;text-transform:uppercase;}
.score-badge{background:linear-gradient(135deg,#0f3460,#1a4f8a);border:2px solid #00d4ff;border-radius:50%;width:110px;height:110px;display:flex;flex-direction:column;align-items:center;justify-content:center;margin:0 auto 20px;}
.score-badge .num{font-size:2.4rem;font-weight:900;color:#fff;line-height:1;}
.score-badge .denom{font-size:.8rem;color:#7ea8d8;}
.alert-box{background:#1a0d0d;border:1px solid #ff4b4b;border-radius:8px;padding:10px 16px;margin:8px 0;font-size:.85rem;color:#ffaaaa;}
.ok-box{background:#0d1a0d;border:1px solid #00cc88;border-radius:8px;padding:10px 16px;margin:8px 0;font-size:.85rem;color:#aaffcc;}
div.stButton>button[kind="primary"]{background:linear-gradient(90deg,#0066cc,#00aaff);color:white;border:none;border-radius:10px;font-weight:700;letter-spacing:.5px;font-size:.95rem;padding:.65rem 2rem;transition:opacity .2s;}
div.stButton>button[kind="primary"]:hover{opacity:.88;}
.stTabs [data-baseweb="tab-list"]{background:#111827;border-radius:10px;padding:4px;gap:4px;border:1px solid #1f2d45;}
.stTabs [data-baseweb="tab"]{background:transparent;color:#8899bb;border-radius:8px;font-weight:600;font-size:.85rem;}
.stTabs [aria-selected="true"]{background:#1a2744 !important;color:#00d4ff !important;}
hr{border-color:#1f2d45 !important;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────
_defaults = {
    "informe_actual": None,
    "_df": None,
    "_local_rows": [],
    "_cache_ver": 0,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
#  GOOGLE SHEETS
# ─────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def conectar_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    try:
        creds_info = json.loads(st.secrets["google_credentials"], strict=False)
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception:
        return None

@st.cache_data(ttl=60, show_spinner=False)
def _fetch_sheets(_ver, _cliente):
    """Lee Google Sheets y normaliza columnas. TTL 60s, invalida con _ver."""
    if _cliente is None:
        return pd.DataFrame()
    try:
        hoja = _cliente.open("BioSport_BD").sheet1
        vals = hoja.get_all_values()
        if len(vals) < 2:
            return pd.DataFrame()
        df = pd.DataFrame(vals[1:], columns=vals[0])
        df.columns = [str(c).strip() for c in df.columns]
        df.rename(columns=ALIAS_COLUMNAS, inplace=True)
        for col in ["Nombre","Fecha","Deporte"]:
            if col not in df.columns:
                df[col] = ""
        for col in NUM_COLS:
            if col not in df.columns:
                df[col] = 0.0
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        return df
    except Exception as ex:
        st.warning(f"Error al cargar historial: {ex}")
        return pd.DataFrame()

def get_df() -> pd.DataFrame:
    """Devuelve historial fusionando Sheets + filas locales pendientes."""
    if st.session_state["_df"] is None:
        st.session_state["_df"] = _fetch_sheets(
            st.session_state["_cache_ver"], cliente_sheets
        )
    df_sheets = st.session_state["_df"]
    local = st.session_state.get("_local_rows", [])
    if not local:
        return df_sheets if df_sheets is not None else pd.DataFrame()

    df_local = pd.DataFrame(local, columns=COLUMNAS_SHEETS)
    for col in NUM_COLS:
        if col in df_local.columns:
            df_local[col] = pd.to_numeric(df_local[col], errors="coerce").fillna(0.0)
    if df_sheets is None or df_sheets.empty:
        return df_local
    combined = pd.concat([df_sheets, df_local], ignore_index=True)
    combined = combined.drop_duplicates(subset=["Fecha","Nombre","CMJ_cm"], keep="last")
    return combined

def _invalidar_cache():
    st.session_state["_cache_ver"] += 1
    st.session_state["_df"] = None

def _formatear_hoja(hoja):
    """Aplica formato visual profesional a Google Sheets."""
    try:
        hoja.freeze(rows=1)
        hoja.format("A1:W1", {
            "backgroundColor": {"red":0.04,"green":0.13,"blue":0.25},
            "textFormat": {
                "bold": True,
                "foregroundColor": {"red":0.0,"green":0.83,"blue":1.0},
                "fontSize": 10
            },
            "horizontalAlignment": "CENTER"
        })
        hoja.format("C1:W1000", {"horizontalAlignment": "CENTER"})
        hoja.format("B2:B1000", {"textFormat": {"bold": True}})
        # Ancho de columnas clave
        body = {"requests": [
            {"updateDimensionProperties": {
                "range": {"sheetId":0,"dimension":"COLUMNS","startIndex":0,"endIndex":1},
                "properties": {"pixelSize": 90}, "fields": "pixelSize"}},
            {"updateDimensionProperties": {
                "range": {"sheetId":0,"dimension":"COLUMNS","startIndex":1,"endIndex":2},
                "properties": {"pixelSize": 160}, "fields": "pixelSize"}},
        ]}
        hoja.spreadsheet.batch_update(body)
    except Exception:
        pass

def guardar_fila(cliente, fila: list) -> bool:
    """Guarda en Sheets y en buffer local para reactividad inmediata."""
    # Asegurar longitud correcta (rellenar con 0 si faltan columnas nuevas)
    while len(fila) < len(COLUMNAS_SHEETS):
        fila.append(0)
    st.session_state["_local_rows"].append(fila)
    st.session_state["_df"] = None  # Forzar re-merge local

    if cliente is None:
        return False
    try:
        hoja = cliente.open("BioSport_BD").sheet1
        vals_existentes = hoja.get_all_values()
        if len(vals_existentes) == 0:
            hoja.append_row(COLUMNAS_SHEETS)
            _formatear_hoja(hoja)
        elif vals_existentes[0] != COLUMNAS_SHEETS:
            hoja.update("A1", [COLUMNAS_SHEETS])
            _formatear_hoja(hoja)
        hoja.append_row(fila, value_input_option="USER_ENTERED")
        _invalidar_cache()
        return True
    except Exception as e:
        st.warning(f"Sin conexión a Sheets — guardado en sesión local: {e}")
        return False

# ─────────────────────────────────────────────
#  CÁLCULOS
# ─────────────────────────────────────────────
def calcular_puntos(sj, cmj, abalakov, f_rel, ratio_adab, deporte) -> dict:
    perfil = BAREMOS_DEPORTIVOS.get(deporte, BAREMOS_DEPORTIVOS["General / Recreacional"])
    def puntuar(val, max_val):
        return round(min((float(val)/max_val)*10, 10), 2) if max_val and float(val) > 0 else 0.0
    equil = round(max(0.0, 10.0 - abs(1.0 - float(ratio_adab))*20.0), 1) if float(ratio_adab) > 0 else 5.0
    return {
        "Squat Jump":  puntuar(sj,       perfil["SJ"]),
        "CMJ":         puntuar(cmj,      perfil["CMJ"]),
        "Abalakov":    puntuar(abalakov, perfil["Abalakov"]),
        "F. Relativa": puntuar(f_rel,    perfil["F_Rel"]),
        "Equilibrio":  equil,
    }

def nota_global(puntos: dict) -> float:
    vals = [v for v in puntos.values() if v > 0]
    return round(sum(vals)/len(vals), 1) if vals else 0.0

def clasificar(nota: float) -> tuple:
    if nota >= 8:   return "ÉLITE",        "#00d4ff"
    if nota >= 6.5: return "AVANZADO",     "#00cc88"
    if nota >= 5:   return "INTERMEDIO",   "#ffa500"
    return               "EN DESARROLLO",  "#ff4b4b"

def interpretar_cod(deficit):
    if deficit <= 0: return None, None
    if deficit > 0.70:
        return ("⚠️ Déficit muy alto — priorizar frenado excéntrico y fuerza de cadera", "alert")
    if deficit > 0.50:
        return ("🔶 Déficit moderado — trabajar aceleración post-cambio de dirección", "warning")
    return ("✅ Transferencia óptima de desaceleración y empuje", "ok")

def interpretar_vo2(vo2):
    if vo2 <= 0: return None, None
    if vo2 >= 60: return ("✅ Capacidad aeróbica de élite", "ok")
    if vo2 >= 50: return ("🔶 Capacidad aeróbica avanzada", "warning")
    return ("⚠️ Capacidad aeróbica por desarrollar", "alert")

def interpretar_ratio(ratio):
    if ratio <= 0: return None, None
    if 0.90 <= ratio <= 1.10:
        return ("✅ Ratio equilibrado — bajo riesgo de lesión", "ok")
    if 0.75 <= ratio < 0.90 or 1.10 < ratio <= 1.25:
        return ("🔶 Desequilibrio leve — monitorear", "warning")
    return ("⚠️ Desequilibrio significativo — riesgo de pubalgia / lesión", "alert")

# ─────────────────────────────────────────────
#  GRÁFICOS
# ─────────────────────────────────────────────
def chart_velocimetro(titulo, valor, max_val, zona_r, zona_a, zona_v):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=valor,
        title={"text": titulo, "font": {"size":13,"color":"#c8d8f0","family":"Inter"}},
        number={"font": {"size":26,"color":"#ffffff"}},
        gauge={
            "axis": {"range":[0,max_val],"tickcolor":"#4a6080","tickfont":{"color":"#4a6080","size":9}},
            "bar": {"color":"#00aaff","thickness":0.25},
            "bgcolor":"#1a2744","borderwidth":0,
            "steps": [{"range":zona_r,"color":"#3d1515"},
                      {"range":zona_a,"color":"#3d2c0a"},
                      {"range":zona_v,"color":"#0d3320"}],
            "threshold": {"line":{"color":"#00d4ff","width":3},"value":valor},
        },
    ))
    fig.update_layout(height=180, margin=dict(l=10,r=10,t=30,b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

def chart_radar(puntos_actual, puntos_previo=None):
    cats = list(puntos_actual.keys())
    fig = go.Figure()
    if puntos_previo:
        v = list(puntos_previo.values()) + [list(puntos_previo.values())[0]]
        fig.add_trace(go.Scatterpolar(
            r=v, theta=cats+[cats[0]], fill="toself", name="Evaluación anterior",
            line=dict(color="rgba(120,140,180,0.6)",width=1.5),
            fillcolor="rgba(120,140,180,0.08)"))
    v = list(puntos_actual.values()) + [list(puntos_actual.values())[0]]
    fig.add_trace(go.Scatterpolar(
        r=v, theta=cats+[cats[0]], fill="toself", name="Evaluación actual",
        line=dict(color="#00aaff",width=2.5), fillcolor="rgba(0,170,255,0.12)"))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True,range=[0,10],
                tickfont=dict(color="#4a6080",size=9),gridcolor="#1f2d45"),
            angularaxis=dict(tickfont=dict(color="#c8d8f0",size=11)),
            bgcolor="rgba(0,0,0,0)"),
        showlegend=True,
        legend=dict(font=dict(color="#c8d8f0",size=11),bgcolor="rgba(0,0,0,0)"),
        height=380, paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40,r=40,t=20,b=20))
    return fig

def chart_evolucion(df_at, metrica, label, key_suffix=""):
    if df_at.empty or metrica not in df_at.columns:
        return None
    df = df_at.copy()
    df[metrica] = pd.to_numeric(df[metrica], errors="coerce")
    df = df.dropna(subset=[metrica])
    df = df[df[metrica] > 0]
    if df.empty:
        return None
    try:
        df["_dt"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
        df = df.sort_values("_dt").tail(8)
    except Exception:
        df = df.tail(8)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Fecha"], y=df[metrica],
        mode="lines+markers+text",
        text=[f"{v:.1f}" for v in df[metrica]],
        textposition="top center",
        line=dict(color="#00aaff",width=2.5),
        marker=dict(size=9,color="#00d4ff"),
        textfont=dict(color="#c8d8f0",size=10)))
    fig.update_layout(
        title=dict(text=f"Evolución — {label}",font=dict(color="#c8d8f0",size=13)),
        xaxis=dict(tickfont=dict(color="#4a6080"),gridcolor="#1f2d45"),
        yaxis=dict(tickfont=dict(color="#4a6080"),gridcolor="#1f2d45"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(16,26,48,0.6)",
        height=220, margin=dict(l=10,r=10,t=40,b=10))
    return fig

def chart_barras_grupo(df, metrica, label):
    if df.empty or metrica not in df.columns:
        return None
    df2 = df[["Nombre",metrica]].copy()
    df2[metrica] = pd.to_numeric(df2[metrica], errors="coerce").fillna(0)
    df2 = df2[df2[metrica]>0].sort_values(metrica, ascending=True)
    if df2.empty:
        return None
    med = df2[metrica].median()
    colores = ["#ff4b4b" if v<med*0.85 else "#ffa500" if v<med*1.1 else "#00cc88"
               for v in df2[metrica]]
    fig = go.Figure(go.Bar(
        x=df2[metrica], y=df2["Nombre"], orientation="h",
        marker_color=colores,
        text=[f"{v:.1f}" for v in df2[metrica]],
        textposition="outside",
        textfont=dict(color="#c8d8f0",size=10)))
    fig.update_layout(
        title=dict(text=label,font=dict(color="#c8d8f0",size=13)),
        xaxis=dict(tickfont=dict(color="#4a6080"),gridcolor="#1f2d45"),
        yaxis=dict(tickfont=dict(color="#c8d8f0",size=11)),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(16,26,48,0.6)",
        height=max(250,35*len(df2)), margin=dict(l=10,r=50,t=40,b=10))
    return fig

def chart_perfil_fv(sj_0, sj_20, sj_40):
    puntos = [(c, v) for c,v in [(0,sj_0),(20,sj_20),(40,sj_40)] if v > 0]
    if len(puntos) < 2:
        return None
    xs, ys = zip(*puntos)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="lines+markers+text",
        text=[f"{y:.1f} cm" for y in ys],
        textposition="top center",
        line=dict(color="#00ffcc",width=3),
        marker=dict(size=10,color="#00d4ff")))
    fig.update_layout(
        title=dict(text="Perfil Fuerza-Velocidad",font=dict(color="#c8d8f0",size=13)),
        xaxis=dict(title="Carga Externa (kg)",tickfont=dict(color="#4a6080"),
                   gridcolor="#1f2d45",titlefont=dict(color="#7ea8d8",size=10)),
        yaxis=dict(title="Altura Salto (cm)",tickfont=dict(color="#4a6080"),
                   gridcolor="#1f2d45",titlefont=dict(color="#7ea8d8",size=10)),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(16,26,48,0.6)",
        height=240, margin=dict(l=40,r=40,t=40,b=40))
    return fig

# ─────────────────────────────────────────────
#  PDF — Página 1: Portada
# ─────────────────────────────────────────────
def _hexagono(c, cx, cy, r, cf, cs, lw=2):
    pts = [(cx+r*math.cos(math.radians(60*i-30)),
            cy+r*math.sin(math.radians(60*i-30))) for i in range(6)]
    p = c.beginPath()
    p.moveTo(*pts[0])
    for px,py in pts[1:]: p.lineTo(px,py)
    p.close()
    c.setFillColorRGB(*cf); c.drawPath(p,fill=1,stroke=0)
    c.setStrokeColorRGB(*cs); c.setLineWidth(lw); c.drawPath(p,fill=0,stroke=1)

def generar_pdf_informe(datos: dict, puntos_act: dict, puntos_prev: dict | None = None,
                        extras: dict | None = None) -> BytesIO:
    buffer = BytesIO()
    cv = canvas.Canvas(buffer, pagesize=A4)
    W, H = A4

    # Paleta
    AO=(0.04,0.07,0.13); AM=(0.05,0.13,0.25); AP=(0.07,0.14,0.26)
    AFA=(0.07,0.12,0.22); AFB=(0.05,0.09,0.17); AH=(0.04,0.20,0.38)
    CI=(0.00,0.83,1.00); BL=(1.00,1.00,1.00)
    GT=(0.78,0.86,0.95); GL=(0.49,0.66,0.86)
    VE=(0.00,0.80,0.53); NA=(1.00,0.65,0.00); RO=(1.00,0.29,0.29)

    nota = nota_global(puntos_act)
    nivel_str, color_nivel = clasificar(nota)
    cn_rgb = tuple(int(color_nivel.lstrip("#")[i:i+2],16)/255 for i in (0,2,4))
    perfil = BAREMOS_DEPORTIVOS.get(datos["deporte"], BAREMOS_DEPORTIVOS["General / Recreacional"])

    def rf(x,y,w,h,rgb): cv.setFillColorRGB(*rgb); cv.rect(x,y,w,h,fill=1,stroke=0)
    def rs(x,y,w,h,rgb,lw=1): cv.setStrokeColorRGB(*rgb); cv.setLineWidth(lw); cv.rect(x,y,w,h,fill=0,stroke=1)

    # ── PORTADA ───────────────────────────────────────────────────────────
    rf(0,0,W,H,AO); rf(0,H-220,W,220,AM); rf(0,0,6,H,CI)
    cv.setStrokeColorRGB(*CI); cv.setLineWidth(2); cv.line(6,H-220,W,H-220)
    cv.setStrokeColorRGB(0.08,0.25,0.45); cv.setLineWidth(0.5)
    for off in range(0,120,18): cv.line(W-160+off*0.3,H-10,W-10,H-160+off*0.3)

    _hexagono(cv,55,H-68,28,AP,CI,2); _hexagono(cv,55,H-68,18,AO,CI,1)
    cv.setFillColorRGB(*CI); cv.setFont("Helvetica-Bold",20); cv.drawCentredString(55,H-74,"B")
    cv.setFillColorRGB(*BL); cv.setFont("Helvetica-Bold",26); cv.drawString(92,H-58,"BIO SPORT")
    cv.setFillColorRGB(*CI); cv.setFont("Helvetica-Bold",26); cv.drawString(222,H-58," PRO")
    cv.setFillColorRGB(*GL); cv.setFont("Helvetica",9)
    cv.drawString(93,H-74,"EVALUACIÓN DEPORTIVA DE ALTO RENDIMIENTO")
    cv.drawRightString(W-30,H-58,datos["fecha"])

    # Bloque nombre
    yc=H-320
    rf(30,yc-40,W-60,80,AP); rs(30,yc-40,W-60,80,CI,1)
    cv.setFillColorRGB(*CI); cv.setFont("Helvetica",8); cv.drawString(48,yc+30,"INFORME DE EVALUACIÓN  ·  ATLETA")
    cv.setFillColorRGB(*BL); cv.setFont("Helvetica-Bold",22); cv.drawString(48,yc+8,datos["nombre"].upper())
    cv.setFillColorRGB(*GL); cv.setFont("Helvetica",10)
    cv.drawString(48,yc-22,f"{datos['deporte'].upper()}   ·   {datos['edad']} años   ·   {datos['peso']} kg   ·   {datos['estatura']} m")

    # Fichas datos
    fichas=[("DEPORTE",datos["deporte"]),("EDAD",f"{datos['edad']} años"),
            ("PESO",f"{datos['peso']} kg"),("ESTATURA",f"{datos['estatura']} m")]
    fw=(W-60)/4
    for i,(lbl,val) in enumerate(fichas):
        fx=30+i*fw; fy=yc-130
        rf(fx+2,fy,fw-4,70,AP); rs(fx+2,fy,fw-4,70,(0.10,0.24,0.44),0.6)
        cv.setFillColorRGB(*GL); cv.setFont("Helvetica",7); cv.drawCentredString(fx+fw/2,fy+54,lbl)
        cv.setFillColorRGB(*BL); cv.setFont("Helvetica-Bold",13); cv.drawCentredString(fx+fw/2,fy+32,str(val))
        rf(fx+2,fy,fw-4,3,CI)

    # Badge nota global
    bcx=W/2; bcy=yc-270
    for r_ring,alpha in [(80,0.08),(68,0.15),(56,1.0)]:
        if r_ring==56: _hexagono(cv,bcx,bcy,r_ring,AP,CI,2.5)
        else:
            cv.setStrokeColorRGB(*CI); cv.setLineWidth(0.5)
            cv.setStrokeAlpha(alpha); cv.circle(bcx,bcy,r_ring,fill=0,stroke=1)
    cv.setStrokeAlpha(1.0)
    cv.setFillColorRGB(*BL); cv.setFont("Helvetica-Bold",36); cv.drawCentredString(bcx,bcy+2,f"{nota:.1f}")
    cv.setFillColorRGB(*GL); cv.setFont("Helvetica",10); cv.drawCentredString(bcx,bcy-18,"/ 10  NOTA GLOBAL")
    rf(bcx-55,bcy-50,110,20,cn_rgb)
    cv.setFillColorRGB(*AO); cv.setFont("Helvetica-Bold",9); cv.drawCentredString(bcx,bcy-44,nivel_str)

    # Barras de capacidades
    by_b=bcy-110; bw_b=320; bx0=(W-bw_b)/2
    cv.setFillColorRGB(*GL); cv.setFont("Helvetica-Bold",7); cv.drawCentredString(W/2,by_b+20,"PERFIL DE CAPACIDADES")
    for i,(cat,val) in enumerate(puntos_act.items()):
        ry=by_b-i*22
        cv.setFillColorRGB(*GL); cv.setFont("Helvetica",8); cv.drawString(bx0,ry,cat)
        rf(bx0+110,ry,bw_b-110,10,(0.08,0.14,0.26))
        if puntos_prev and cat in puntos_prev:
            vp=min(puntos_prev[cat],10)/10
            cv.setFillColorRGB(0.35,0.42,0.55); cv.rect(bx0+110,ry,(bw_b-110)*vp,10,fill=1,stroke=0)
        va=min(val,10)/10; cb=VE if val>=6.5 else NA if val>=5 else RO
        rf(bx0+110,ry,(bw_b-110)*va,10,cb)
        cv.setFillColorRGB(*BL); cv.setFont("Helvetica-Bold",8); cv.drawRightString(bx0+bw_b+28,ry+2,f"{val:.1f}")
    if puntos_prev:
        byl=by_b-len(puntos_act)*22-10
        rf(bx0+110,byl,10,8,(0.35,0.42,0.55))
        cv.setFillColorRGB(*GL); cv.setFont("Helvetica",7); cv.drawString(bx0+124,byl,"Evaluación anterior")

    # Pie p1
    rf(0,0,W,28,(0.03,0.05,0.10))
    cv.setStrokeColorRGB(0.08,0.20,0.38); cv.setLineWidth(0.5); cv.line(6,28,W,28)
    cv.setFillColorRGB(*GL); cv.setFont("Helvetica",7)
    cv.drawString(20,10,"Bio Sport Pro  ·  Evaluación Deportiva de Alto Rendimiento")
    cv.drawRightString(W-20,10,f"Página 1 de 2  ·  {datos['fecha']}")

    # ── PÁGINA 2: RESULTADOS TÉCNICOS ─────────────────────────────────────
    cv.showPage()
    rf(0,0,W,H,AO); rf(0,0,6,H,CI); rf(0,H-60,W,60,AM)
    cv.setStrokeColorRGB(*CI); cv.setLineWidth(1.5); cv.line(6,H-60,W,H-60)
    cv.setFillColorRGB(*BL); cv.setFont("Helvetica-Bold",13); cv.drawString(24,H-35,"RESULTADOS TÉCNICOS")
    cv.setFillColorRGB(*GL); cv.setFont("Helvetica",9)
    cv.drawString(24,H-50,f"{datos['nombre'].upper()}  ·  {datos['deporte']}  ·  {datos['fecha']}")
    cv.setFillColorRGB(*GL); cv.setFont("Helvetica",8); cv.drawRightString(W-20,H-38,"02")

    # Tabla de pruebas
    yt=H-80
    metricas_pdf=[
        ("Squat Jump (SJ)",  datos["sj"],      "cm",   perfil["SJ"]),
        ("CMJ",              datos["cmj"],     "cm",   perfil["CMJ"]),
        ("Abalakov",         datos["abalakov"],"cm",   perfil["Abalakov"]),
        ("IMTP",             datos["imtp"],    "N",    None),
        ("Fuerza Relativa",  datos["f_rel"],   "N/kg", perfil["F_Rel"]),
        ("RSI Modificado",   datos["rsi"],     "",     perfil["RSI"]),
        ("Ratio Aduc/Abduc", datos["ratio"],   "",     None),
    ]
    # Agregar métricas extras si existen
    if extras:
        if extras.get("sprint_10m",0)>0:
            metricas_pdf.append(("Sprint 10m",extras["sprint_10m"],"s",None))
        if extras.get("agilidad_505",0)>0:
            metricas_pdf.append(("Test 5-0-5",extras["agilidad_505"],"s",None))
        if extras.get("vo2max",0)>0:
            metricas_pdf.append(("VO2 Máx",extras["vo2max"],"ml/kg/min",None))
            metricas_pdf.append(("VAM",extras["vam"],"km/h",None))

    col_x=[24,180,285,355,470]; fh2=22
    rf(6,yt-fh2,W-6,fh2,AH)
    for hx,ht in zip(col_x,["PRUEBA","RESULTADO","RENDIMIENTO","PUNT.","NIVEL"]):
        cv.setFillColorRGB(*CI); cv.setFont("Helvetica-Bold",8); cv.drawString(hx+6,yt-fh2+7,ht)
    yt -= fh2

    for i,(prueba,val_raw,unidad,max_v) in enumerate(metricas_pdf):
        bg=AFA if i%2==0 else AFB; rf(6,yt-fh2,W-6,fh2,bg)
        cv.setFillColorRGB(*GT); cv.setFont("Helvetica",9); cv.drawString(col_x[0]+6,yt-fh2+6,prueba)
        vf=f"{float(val_raw or 0):.2f}".rstrip("0").rstrip(".")
        cv.setFillColorRGB(*BL); cv.setFont("Helvetica-Bold",9)
        cv.drawString(col_x[1]+6,yt-fh2+6,f"{vf} {unidad}".strip())
        if max_v and float(val_raw or 0)>0:
            pts=(float(val_raw)/max_v)*10; pts=min(pts,10)
            cb=VE if pts>=6.5 else NA if pts>=5 else RO
            bx2=col_x[2]+6; bw2=90; by2=yt-fh2+7
            rf(bx2,by2,bw2,8,(0.08,0.14,0.26)); rf(bx2,by2,bw2*(pts/10),8,cb)
            cv.setFillColorRGB(*BL); cv.setFont("Helvetica-Bold",9)
            cv.drawCentredString(col_x[3]+20,yt-fh2+6,f"{pts:.1f}/10")
            rf(col_x[4]+2,yt-fh2+4,90,14,cb)
            nl,_=clasificar(pts)
            cv.setFillColorRGB(*AO); cv.setFont("Helvetica-Bold",7)
            cv.drawCentredString(col_x[4]+47,yt-fh2+9,nl)
        else:
            cv.setFillColorRGB(*GL); cv.setFont("Helvetica",8)
            cv.drawString(col_x[2]+6,yt-fh2+6,"—")
        yt -= fh2

    # Radar vectorial
    ys=yt-16
    cv.setFillColorRGB(*CI); cv.setFont("Helvetica-Bold",8); cv.drawString(24,ys,"PERFIL RADAR DE CAPACIDADES")
    rcx=130; rcy=ys-105; rr=82; n=len(puntos_act); cats=list(puntos_act.keys())
    def rpt(idx,radio):
        ang=idx*(2*math.pi/n)-math.pi/2
        return rcx+radio*math.cos(ang), rcy+radio*math.sin(ang)
    for nr in [1,2,3]:
        ring=[rpt(j,rr*nr/3) for j in range(n)]
        p=cv.beginPath(); p.moveTo(*ring[0])
        for px2,py2 in ring[1:]: p.lineTo(px2,py2)
        p.close()
        cv.setFillColorRGB(*[(0.18,0.07,0.07),(0.18,0.14,0.04),(0.04,0.18,0.12)][nr-1])
        cv.drawPath(p,fill=1,stroke=0)
        cv.setStrokeColorRGB(0.12,0.22,0.38); cv.setLineWidth(0.4); cv.drawPath(p,fill=0,stroke=1)
    cv.setStrokeColorRGB(0.15,0.28,0.48); cv.setLineWidth(0.6)
    for j in range(n): ex,ey=rpt(j,rr); cv.line(rcx,rcy,ex,ey)
    if puntos_prev:
        pp=[rpt(j,(min(puntos_prev.get(k,0),10)/10)*rr) for j,k in enumerate(cats)]
        p=cv.beginPath(); p.moveTo(*pp[0])
        for px2,py2 in pp[1:]: p.lineTo(px2,py2)
        p.close(); cv.setFillColorRGB(0.25,0.30,0.40); cv.drawPath(p,fill=1,stroke=0)
        cv.setStrokeColorRGB(0.45,0.55,0.70); cv.setLineWidth(1.2); cv.drawPath(p,fill=0,stroke=1)
    pa=[rpt(j,(min(v,10)/10)*rr) for j,(_,v) in enumerate(puntos_act.items())]
    p=cv.beginPath(); p.moveTo(*pa[0])
    for px2,py2 in pa[1:]: p.lineTo(px2,py2)
    p.close(); cv.setFillColorRGB(0.0,0.42,0.70); cv.drawPath(p,fill=1,stroke=0)
    cv.setStrokeColorRGB(*CI); cv.setLineWidth(2); cv.drawPath(p,fill=0,stroke=1)
    for j,(k,v) in enumerate(puntos_act.items()):
        px2,py2=rpt(j,(min(v,10)/10)*rr)
        cv.setFillColorRGB(*CI); cv.circle(px2,py2,3.5,fill=1,stroke=0)
        lx,ly=rpt(j,rr+14)
        cv.setFillColorRGB(*GT); cv.setFont("Helvetica",7); cv.drawCentredString(lx,ly-3,k)

    # Detalle comparativo
    dx=260; dy=ys-10
    cv.setFillColorRGB(*CI); cv.setFont("Helvetica-Bold",8); cv.drawString(dx,dy,"DETALLE COMPARATIVO"); dy-=16
    for cat,val in puntos_act.items():
        rf(dx,dy-4,W-dx-20,20,AFA)
        cv.setFillColorRGB(*GT); cv.setFont("Helvetica",8); cv.drawString(dx+5,dy+2,cat)
        cb=VE if val>=6.5 else NA if val>=5 else RO
        cv.setFillColorRGB(*cb); cv.setFont("Helvetica-Bold",9); cv.drawRightString(dx+120,dy+2,f"{val:.1f}")
        if puntos_prev and cat in puntos_prev:
            diff=val-puntos_prev[cat]
            cv.setFillColorRGB(*(VE if diff>0.2 else RO if diff<-0.2 else GL))
            arr=f"▲ +{diff:.1f}" if diff>0.2 else (f"▼ {diff:.1f}" if diff<-0.2 else "= =")
            cv.setFont("Helvetica-Bold",8); cv.drawString(dx+130,dy+2,arr)
            cv.setFillColorRGB(*GL); cv.setFont("Helvetica",7); cv.drawRightString(W-26,dy+2,f"ant:{puntos_prev[cat]:.1f}")
        dy-=21
    if puntos_prev:
        dy-=4; cv.setFillColorRGB(*GL); cv.setFont("Helvetica",7)
        cv.drawString(dx,dy,"▲▼ variación respecto evaluación anterior")

    # Badge nota página 2
    b2cx=dx+100; b2cy=dy-55
    _hexagono(cv,b2cx,b2cy,42,AP,CI,2)
    cv.setFillColorRGB(*BL); cv.setFont("Helvetica-Bold",22); cv.drawCentredString(b2cx,b2cy+4,f"{nota:.1f}")
    cv.setFillColorRGB(*GL); cv.setFont("Helvetica",7); cv.drawCentredString(b2cx,b2cy-10,"NOTA GLOBAL / 10")
    rf(b2cx-38,b2cy-30,76,14,cn_rgb)
    cv.setFillColorRGB(*AO); cv.setFont("Helvetica-Bold",7); cv.drawCentredString(b2cx,b2cy-24,nivel_str)

    # Pie p2
    rf(0,0,W,28,(0.03,0.05,0.10))
    cv.setStrokeColorRGB(0.08,0.20,0.38); cv.setLineWidth(0.5); cv.line(6,28,W,28)
    cv.setFillColorRGB(*GL); cv.setFont("Helvetica",7)
    cv.drawString(20,10,"Bio Sport Pro  ·  Evaluación Deportiva de Alto Rendimiento")
    cv.drawRightString(W-20,10,f"Página 2 de 2  ·  {datos['fecha']}")

    cv.save(); buffer.seek(0)
    return buffer

def generar_pdf_grupal(df: pd.DataFrame) -> BytesIO:
    buffer = BytesIO()
    cv = canvas.Canvas(buffer, pagesize=A4)
    W,H=A4
    cv.setFillColorRGB(0.04,0.07,0.13); cv.rect(0,0,W,H,fill=1,stroke=0)
    cv.setFillColorRGB(0.05,0.13,0.25); cv.rect(0,H-100,W,100,fill=1,stroke=0)
    cv.setStrokeColorRGB(0,0.83,1); cv.setLineWidth(3); cv.line(0,H-100,W,H-100)
    cv.setFillColorRGB(0,0.83,1); cv.setFont("Helvetica-Bold",18)
    cv.drawString(40,H-50,"BIO SPORT PRO — INFORME GRUPAL")
    cv.setFont("Helvetica",10); cv.setFillColorRGB(0.5,0.7,0.9)
    fh=datetime.now().strftime("%d/%m/%Y")
    cv.drawString(40,H-70,f"Generado el {fh}  ·  {len(df)} atletas evaluados")
    _cc=[("Nombre","Nombre"),("Deporte","Deporte"),("Fecha","Fecha"),
         ("SJ_cm","SJ cm"),("CMJ_cm","CMJ cm"),("Abalakov_cm","Abalakov cm"),
         ("F_Rel_NKg","F.Rel N/kg"),("RSI_Mod","RSI"),("Ratio_AdAb","Ratio A/Ab")]
    cols_m=[col for col,_ in _cc if col in df.columns]
    cols_l=[lbl for col,lbl in _cc if col in df.columns]
    df_show=df[cols_m].tail(50).copy()
    td=[cols_l]+[[str(row[col])[:16] for col in cols_m] for _,row in df_show.iterrows()]
    _w=[110,80,75,45,45,55,58,42,52]
    t=Table(td,colWidths=_w[:len(cols_m)])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0f3460")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.HexColor("#00d4ff")),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#111827"),colors.HexColor("#0d1627")]),
        ("TEXTCOLOR",(0,1),(-1,-1),colors.HexColor("#c8d8f0")),("FONTSIZE",(0,1),(-1,-1),8),
        ("ALIGN",(2,0),(-1,-1),"CENTER"),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#1f2d45")),
        ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
    ]))
    t.wrapOn(cv,W-80,H); t.drawOn(cv,40,H-150-len(td)*17)
    cv.setFillColorRGB(0.04,0.07,0.13); cv.rect(0,0,W,30,fill=1,stroke=0)
    cv.setFont("Helvetica",7); cv.setFillColorRGB(0.35,0.50,0.70)
    cv.drawString(40,10,"Generado por Bio Sport Pro  ·  Informe Grupal")
    cv.drawRightString(W-40,10,fh)
    cv.save(); buffer.seek(0)
    return buffer

# ═══════════════════════════════════════════════
#  INICIO
# ═══════════════════════════════════════════════
cliente_sheets = conectar_sheets()
data_historica = get_df()

lista_atletas = ["➕ Nuevo Atleta"]
if not data_historica.empty and "Nombre" in data_historica.columns:
    lista_atletas += sorted([n for n in data_historica["Nombre"].dropna().unique() if str(n).strip()])

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

tab_eval, tab_hist, tab_grupo = st.tabs([
    "📋 Nueva Evaluación", "📈 Historial Individual", "👥 Informe Grupal"
])

# ════════════════════════════════════════════════
#  TAB 1 — NUEVA EVALUACIÓN
# ════════════════════════════════════════════════
with tab_eval:

    # ── Identificación ────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">Identificación del Atleta</p>', unsafe_allow_html=True)

    c_sel, c_nom = st.columns([2,3])
    with c_sel:
        atleta_sel = st.selectbox("Buscar en historial", lista_atletas, key="sel_atleta")

    # Auto-relleno desde historial
    datos_prev_raw = {}
    if atleta_sel != "➕ Nuevo Atleta" and not data_historica.empty:
        mask = data_historica["Nombre"] == atleta_sel
        if mask.any():
            datos_prev_raw = data_historica[mask].iloc[-1].to_dict()

    def vd(col, default):
        val = datos_prev_raw.get(col, default)
        try: return type(default)(val) if val not in ("", None, 0) else default
        except Exception: return default

    with c_nom:
        nombre = st.text_input("Nombre completo",
            value=atleta_sel if atleta_sel != "➕ Nuevo Atleta" else "",
            placeholder="Ej: Carlos Pérez")

    c1,c2,c3,c4 = st.columns(4)
    with c1: edad     = st.number_input("Edad", min_value=10, max_value=60, step=1, value=vd("Edad",22))
    with c2: peso     = st.number_input("Peso (kg)", min_value=30.0, max_value=180.0, step=0.1, value=vd("Peso_kg",75.0), format="%.1f")
    with c3: estatura = st.number_input("Estatura (m)", min_value=1.40, max_value=2.20, step=0.01, value=vd("Estatura_m",1.75), format="%.2f")
    with c4:
        dep_options = list(BAREMOS_DEPORTIVOS.keys())
        dep_prev = str(datos_prev_raw.get("Deporte","Fútbol"))
        dep_idx = dep_options.index(dep_prev) if dep_prev in dep_options else 0
        deporte = st.selectbox("Deporte / Disciplina", dep_options, index=dep_idx)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Pliometría ────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">Pruebas de Potencia y Salto</p>', unsafe_allow_html=True)
    p1,p2,p3,p4 = st.columns(4)
    with p1: sj       = st.number_input("SJ (cm)", min_value=0.0, max_value=100.0, step=0.1, value=0.0,
        help="Squat Jump: salto concéntrico puro desde 90° de flexión. Evalúa fuerza explosiva bruta.")
    with p2: cmj      = st.number_input("CMJ (cm)", min_value=0.0, max_value=100.0, step=0.1, value=0.0,
        help="Counter Movement Jump: salto con contramovimiento. Evalúa el ciclo estiramiento-acortamiento (CEA).")
    with p3: abalakov = st.number_input("Abalakov (cm)", min_value=0.0, max_value=100.0, step=0.1, value=0.0,
        help="CMJ con brazos libres. Evalúa coordinación global y aporte del tren superior.")
    with p4: rsi      = st.number_input("RSI Modificado", min_value=0.0, max_value=5.0, step=0.01, value=0.0,
        help="Reactive Strength Index: evalúa rigidez tendinosa (stiffness) y reactividad del tobillo.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Fuerza isométrica y dinamometría ──────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">Fuerza Isométrica y Dinamometría de Cadera</p>', unsafe_allow_html=True)
    f1,f2,f3 = st.columns(3)
    with f1: imtp  = st.number_input("IMTP (N)", min_value=0.0, step=10.0, value=0.0,
        help="Fuerza máxima isométrica (Isometric Mid-Thigh Pull). Se calcula F.Rel automáticamente.")
    with f2: aduc  = st.number_input("Aductores (N)", min_value=0.0, step=1.0, value=0.0,
        help="Fuerza de cierre. Se cruza con Abductores para calcular ratio de equilibrio muscular.")
    with f3: abduc = st.number_input("Abductores (N)", min_value=0.0, step=1.0, value=0.0)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Velocidad y COD ───────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">Velocidad y Cambio de Dirección (COD)</p>', unsafe_allow_html=True)
    vc1,vc2 = st.columns(2)
    with vc1: sprint_10m   = st.number_input("Sprint Lineal 10m (s)", min_value=0.0, max_value=10.0, step=0.01, value=0.0,
        help="Tiempo en segundos. Referencia élite: <1.70s")
    with vc2: agilidad_505 = st.number_input("Test Agilidad 5-0-5 (s)", min_value=0.0, max_value=10.0, step=0.01, value=0.0,
        help="Tiempo en segundos. Se calcula el déficit COD automáticamente.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Capacidad aeróbica ────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">Capacidad Aeróbica — Yo-Yo IR1</p>', unsafe_allow_html=True)
    yoyo_m = st.number_input("Distancia Total Yo-Yo IR1 (metros)", min_value=0.0, max_value=4000.0, step=40.0, value=0.0,
        help="Metros acumulados. El sistema calcula VO2Máx y VAM automáticamente.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Perfil F-V ────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">Perfil Fuerza-Velocidad (SJ con Sobrecarga)</p>', unsafe_allow_html=True)
    fv1,fv2 = st.columns(2)
    with fv1: sj_20kg = st.number_input("SJ con 20 kg (cm)", min_value=0.0, max_value=100.0, step=0.1, value=0.0)
    with fv2: sj_40kg = st.number_input("SJ con 40 kg (cm)", min_value=0.0, max_value=100.0, step=0.1, value=0.0)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Cálculos derivados ────────────────────────────────────────────────
    f_rel_live = round(imtp/peso, 2) if peso > 0 and imtp > 0 else 0.0
    ratio_live = round(aduc/abduc, 2) if abduc > 0 else 1.0
    cod_deficit = round(agilidad_505 - sprint_10m, 2) if agilidad_505 > 0 and sprint_10m > 0 else 0.0
    vo2max  = round((yoyo_m*0.0084)+36.4, 1) if yoyo_m > 0 else 0.0
    vam     = round(vo2max/3.5, 1) if vo2max > 0 else 0.0

    # ── Vista previa en tiempo real ───────────────────────────────────────
    if any(v2 > 0 for v2 in [sj,cmj,abalakov,imtp,rsi]):
        pts_live  = calcular_puntos(sj,cmj,abalakov,f_rel_live,ratio_live,deporte)
        nota_live = nota_global(pts_live)
        nivel_live, color_live = clasificar(nota_live)
        mx = BAREMOS_DEPORTIVOS[deporte]

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Vista Previa en Tiempo Real</p>', unsafe_allow_html=True)

        chips = '<div class="metric-row">'
        for cat,val in pts_live.items():
            chips += f'<div class="metric-chip"><div class="val">{val:.1f}</div><div class="lbl">{cat}</div></div>'
        chips += f'<div class="metric-chip" style="border-color:#00d4ff;"><div class="val" style="color:#fff">{nota_live}</div><div class="lbl" style="color:{color_live}">{nivel_live}</div></div></div>'
        st.markdown(chips, unsafe_allow_html=True)

        vm1,vm2,vm3 = st.columns(3)
        with vm1: st.plotly_chart(chart_velocimetro("SJ",sj,mx["SJ"],[0,mx["SJ"]*0.5],[mx["SJ"]*0.5,mx["SJ"]*0.7],[mx["SJ"]*0.7,mx["SJ"]]), use_container_width=True, key="vp_sj")
        with vm2: st.plotly_chart(chart_velocimetro("CMJ",cmj,mx["CMJ"],[0,mx["CMJ"]*0.5],[mx["CMJ"]*0.5,mx["CMJ"]*0.7],[mx["CMJ"]*0.7,mx["CMJ"]]), use_container_width=True, key="vp_cmj")
        with vm3: st.plotly_chart(chart_velocimetro("RSI",rsi,mx["RSI"],[0,mx["RSI"]*0.33],[mx["RSI"]*0.33,mx["RSI"]*0.55],[mx["RSI"]*0.55,mx["RSI"]]), use_container_width=True, key="vp_rsi")

        # Diagnósticos avanzados en tiempo real
        diag_items = []
        if ratio_live > 0 and abduc > 0:
            msg, tipo = interpretar_ratio(ratio_live)
            if msg: diag_items.append((f"Ratio Aduc/Abduc: **{ratio_live:.2f}**  — {msg}", tipo))
        if cod_deficit > 0:
            msg, tipo = interpretar_cod(cod_deficit)
            if msg: diag_items.append((f"Déficit COD: **{cod_deficit:.2f}s**  — {msg}", tipo))
        if vo2max > 0:
            msg, tipo = interpretar_vo2(vo2max)
            if msg: diag_items.append((f"VO2Máx estimado: **{vo2max} ml/kg/min** | VAM: **{vam} km/h**  — {msg}", tipo))

        if diag_items:
            st.markdown("<p class='section-title' style='margin-top:16px'>🔬 Diagnóstico Automático</p>", unsafe_allow_html=True)
            for msg, tipo in diag_items:
                css = "alert-box" if tipo=="alert" else "ok-box" if tipo=="ok" else "section-card"
                st.markdown(f'<div class="{css}">{msg}</div>', unsafe_allow_html=True)

        fig_fv = chart_perfil_fv(sj, sj_20kg, sj_40kg)
        if fig_fv:
            st.plotly_chart(fig_fv, use_container_width=True, key="vp_fv")

        st.markdown('</div>', unsafe_allow_html=True)

    # ── Guardar ───────────────────────────────────────────────────────────
    st.markdown("")
    confirmar = st.toggle("✅ Confirmo que los datos son correctos")
    btn_guardar = st.button("💾 GUARDAR Y GENERAR INFORME PDF",
                            type="primary", use_container_width=True, disabled=not confirmar)

    if btn_guardar:
        errores = []
        if not nombre.strip():                             errores.append("El nombre es obligatorio.")
        if peso <= 0:                                      errores.append("El peso debe ser mayor a 0.")
        if all(v2==0 for v2 in [sj,cmj,abalakov,imtp]):  errores.append("Registra al menos una prueba de rendimiento.")

        if errores:
            for e in errores: st.error(f"⚠️ {e}")
        else:
            f_rel  = round(imtp/peso, 2) if peso > 0 else 0.0
            ratio  = round(aduc/abduc, 2) if abduc > 0 else 1.0
            fecha  = datetime.now().strftime("%d/%m/%Y")

            datos_eval = {
                "nombre": nombre.strip(), "edad": int(edad), "peso": round(float(peso),1),
                "estatura": round(float(estatura),2), "deporte": deporte, "fecha": fecha,
                "sj": sj, "cmj": cmj, "abalakov": abalakov,
                "imtp": imtp, "f_rel": f_rel, "rsi": rsi,
                "aduc": aduc, "abduc": abduc, "ratio": ratio,
            }
            extras = {
                "sprint_10m": sprint_10m, "agilidad_505": agilidad_505,
                "cod_deficit": cod_deficit, "yoyo_m": yoyo_m,
                "vo2max": vo2max, "vam": vam,
                "sj_20kg": sj_20kg, "sj_40kg": sj_40kg,
            }

            fila = [fecha, nombre.strip(), int(edad), round(float(peso),1),
                    round(float(estatura),2), deporte,
                    imtp, f_rel, sj, cmj, abalakov, rsi, aduc, abduc, ratio,
                    sprint_10m, agilidad_505, cod_deficit,
                    yoyo_m, vo2max, vam, sj_20kg, sj_40kg]

            # Puntos previos para comparativo
            puntos_prev = None
            df_actual = get_df()
            if not df_actual.empty and "Nombre" in df_actual.columns:
                mask = df_actual["Nombre"] == nombre.strip()
                if mask.any():
                    prev_row = df_actual[mask].iloc[-1].to_dict()
                    try:
                        dep_p = str(prev_row.get("Deporte", deporte))
                        if dep_p not in BAREMOS_DEPORTIVOS: dep_p = "General / Recreacional"
                        puntos_prev = calcular_puntos(
                            float(prev_row.get("SJ_cm",0)),
                            float(prev_row.get("CMJ_cm",0)),
                            float(prev_row.get("Abalakov_cm",0)),
                            float(prev_row.get("F_Rel_NKg",0)),
                            float(prev_row.get("Ratio_AdAb",1)),
                            dep_p)
                    except Exception:
                        pass

            guardado = guardar_fila(cliente_sheets, fila)
            if guardado:
                st.success(f"✅ Evaluación de **{nombre.strip()}** guardada en Google Sheets.")
            else:
                st.info("💾 Guardado en sesión local (sin conexión a Sheets).")

            puntos_act = calcular_puntos(sj, cmj, abalakov, f_rel, ratio, deporte)

            with st.spinner("Generando informe PDF…"):
                pdf_buffer = generar_pdf_informe(datos_eval, puntos_act, puntos_prev, extras)

            st.session_state.informe_actual = {
                "datos": datos_eval, "pdf": pdf_buffer,
                "radar_act": puntos_act, "radar_prev": puntos_prev,
                "extras": extras,
            }
            st.rerun()

    # ── Resultados post-guardado ───────────────────────────────────────────
    if st.session_state.informe_actual:
        inf  = st.session_state.informe_actual
        d    = inf["datos"]
        ra   = inf["radar_act"]
        rp   = inf["radar_prev"]
        ext  = inf.get("extras", {})
        nota = nota_global(ra)
        nivel, color_nivel = clasificar(nota)

        st.divider()
        st.markdown(f"### 📊 Resultados — {d['nombre']}")

        col_badge, col_radar = st.columns([1,2])
        with col_badge:
            st.markdown(f"""
            <div style="text-align:center;margin-top:20px">
                <div class="score-badge">
                    <span class="num">{nota}</span><span class="denom">/ 10</span>
                </div>
                <p style="font-size:1rem;font-weight:700;color:{color_nivel};letter-spacing:1px;margin-top:8px">{nivel}</p>
                <p style="font-size:.8rem;color:#7ea8d8">{d['fecha']} · {d['deporte']}</p>
            </div>""", unsafe_allow_html=True)
        with col_radar:
            st.plotly_chart(chart_radar(ra, rp), use_container_width=True, key="res_radar")
        if rp:
            st.info("💡 La sombra del radar representa la evaluación anterior del atleta.")

        mx3 = BAREMOS_DEPORTIVOS.get(d["deporte"], BAREMOS_DEPORTIVOS["General / Recreacional"])
        v1,v2 = st.columns(2)
        with v1: st.plotly_chart(chart_velocimetro("CMJ",d["cmj"],mx3["CMJ"],[0,mx3["CMJ"]*0.5],[mx3["CMJ"]*0.5,mx3["CMJ"]*0.7],[mx3["CMJ"]*0.7,mx3["CMJ"]]), use_container_width=True, key="res_cmj")
        with v2: st.plotly_chart(chart_velocimetro("RSI",d["rsi"],mx3["RSI"],[0,mx3["RSI"]*0.33],[mx3["RSI"]*0.33,mx3["RSI"]*0.55],[mx3["RSI"]*0.55,mx3["RSI"]]), use_container_width=True, key="res_rsi")

        # Módulos avanzados post-guardado
        if any(ext.get(k,0)>0 for k in ["cod_deficit","vo2max","sj_20kg"]):
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown('<p class="section-title">🔬 Diagnóstico Avanzado</p>', unsafe_allow_html=True)
            rx1,rx2 = st.columns(2)
            with rx1:
                if ext.get("cod_deficit",0)>0:
                    st.metric("Déficit COD", f"{ext['cod_deficit']} s")
                    msg,tipo = interpretar_cod(ext["cod_deficit"])
                    if msg:
                        css="alert-box" if tipo=="alert" else "ok-box"
                        st.markdown(f'<div class="{css}">{msg}</div>', unsafe_allow_html=True)
                if ext.get("vo2max",0)>0:
                    st.metric("VO2 Máx", f"{ext['vo2max']} ml/kg/min")
                    st.metric("VAM", f"{ext['vam']} km/h")
                    msg,tipo = interpretar_vo2(ext["vo2max"])
                    if msg:
                        css="alert-box" if tipo=="alert" else "ok-box"
                        st.markdown(f'<div class="{css}">{msg}</div>', unsafe_allow_html=True)
            with rx2:
                fig_fv2 = chart_perfil_fv(d["sj"], ext.get("sj_20kg",0), ext.get("sj_40kg",0))
                if fig_fv2: st.plotly_chart(fig_fv2, use_container_width=True, key="res_fv")
            st.markdown('</div>', unsafe_allow_html=True)

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
with tab_hist:
    df_h = get_df()
    if df_h.empty or "Nombre" not in df_h.columns:
        st.info("Aún no hay evaluaciones guardadas.")
        if st.button("🔄 Recargar", key="reload_hist"):
            _invalidar_cache(); st.rerun()
    else:
        nombres_h = sorted([n for n in df_h["Nombre"].dropna().unique() if str(n).strip()])
        if not nombres_h:
            st.info("No se encontraron atletas.")
        else:
            ch1,ch2 = st.columns([4,1])
            with ch1: atleta_h = st.selectbox("Seleccionar atleta", nombres_h, key="hist_sel")
            with ch2:
                st.markdown("<div style='margin-top:28px'>", unsafe_allow_html=True)
                if st.button("🔄 Actualizar", key="reload_hist2"):
                    _invalidar_cache(); st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            df_at = df_h[df_h["Nombre"]==atleta_h].copy()
            if df_at.empty:
                st.warning("No hay registros para este atleta.")
            else:
                st.markdown(f"**{len(df_at)} evaluación(es) registrada(s)**")
                ultima = df_at.iloc[-1]

                col_m1,col_m2,col_m3,col_m4,col_m5 = st.columns(5)
                for col,(lab,ck,uni) in zip(
                    [col_m1,col_m2,col_m3,col_m4,col_m5],
                    [("SJ","SJ_cm","cm"),("CMJ","CMJ_cm","cm"),
                     ("Abalakov","Abalakov_cm","cm"),("F. Rel.","F_Rel_NKg","N/kg"),("RSI","RSI_Mod","")]
                ):
                    col.metric(label=lab, value=f"{float(ultima.get(ck,0) or 0):.1f} {uni}".strip())

                # Radar del atleta
                dep_h = str(ultima.get("Deporte","General / Recreacional"))
                if dep_h not in BAREMOS_DEPORTIVOS: dep_h = "General / Recreacional"
                pts_h = calcular_puntos(
                    float(ultima.get("SJ_cm",0) or 0),
                    float(ultima.get("CMJ_cm",0) or 0),
                    float(ultima.get("Abalakov_cm",0) or 0),
                    float(ultima.get("F_Rel_NKg",0) or 0),
                    float(ultima.get("Ratio_AdAb",1) or 1),
                    dep_h)
                pts_h_prev = None
                if len(df_at) >= 2:
                    ant = df_at.iloc[-2]
                    try:
                        dep_a = str(ant.get("Deporte","General / Recreacional"))
                        if dep_a not in BAREMOS_DEPORTIVOS: dep_a="General / Recreacional"
                        pts_h_prev = calcular_puntos(
                            float(ant.get("SJ_cm",0) or 0),
                            float(ant.get("CMJ_cm",0) or 0),
                            float(ant.get("Abalakov_cm",0) or 0),
                            float(ant.get("F_Rel_NKg",0) or 0),
                            float(ant.get("Ratio_AdAb",1) or 1),
                            dep_a)
                    except Exception: pass

                col_r,col_b2 = st.columns([2,1])
                with col_r:
                    st.plotly_chart(chart_radar(pts_h, pts_h_prev), use_container_width=True, key="h_radar")
                with col_b2:
                    nota_h = nota_global(pts_h)
                    nivel_h,color_h = clasificar(nota_h)
                    st.markdown(f"""
                    <div style="text-align:center;margin-top:40px">
                        <div class="score-badge">
                            <span class="num">{nota_h}</span><span class="denom">/ 10</span>
                        </div>
                        <p style="font-size:.9rem;font-weight:700;color:{color_h};margin-top:8px">{nivel_h}</p>
                        <p style="font-size:.75rem;color:#7ea8d8">Última evaluación</p>
                    </div>""", unsafe_allow_html=True)

                st.markdown("#### Evolución Histórica")
                evo = [("SJ_cm","Squat Jump (cm)"),("CMJ_cm","CMJ (cm)"),
                       ("Abalakov_cm","Abalakov (cm)"),("F_Rel_NKg","Fuerza Relativa (N/kg)")]
                for ca,cb in zip(evo[::2],evo[1::2]):
                    c1e,c2e = st.columns(2)
                    with c1e:
                        fig=chart_evolucion(df_at,ca[0],ca[1])
                        if fig: st.plotly_chart(fig,use_container_width=True,key=f"he_{ca[0]}")
                    with c2e:
                        fig=chart_evolucion(df_at,cb[0],cb[1])
                        if fig: st.plotly_chart(fig,use_container_width=True,key=f"he_{cb[0]}")

                # Evolución métricas avanzadas si existen
                evo_adv = [(c,l) for c,l in [
                    ("Sprint_10m_s","Sprint 10m (s)"),("VO2Max","VO2 Máx"),("VAM_kmh","VAM (km/h)")
                ] if c in df_at.columns and df_at[c].astype(float).sum()>0]
                if evo_adv:
                    st.markdown("#### Evolución — Métricas Avanzadas")
                    cols_adv = st.columns(len(evo_adv))
                    for col_adv,(met,lab) in zip(cols_adv,evo_adv):
                        with col_adv:
                            fig=chart_evolucion(df_at,met,lab)
                            if fig: st.plotly_chart(fig,use_container_width=True,key=f"ha_{met}")

                with st.expander("📋 Ver tabla completa"):
                    st.dataframe(df_at, use_container_width=True)

# ════════════════════════════════════════════════
#  TAB 3 — INFORME GRUPAL
# ════════════════════════════════════════════════
with tab_grupo:
    df_g = get_df()
    if df_g.empty or "Nombre" not in df_g.columns:
        st.info("Aún no hay evaluaciones en el sistema.")
        if st.button("🔄 Recargar", key="reload_grupo"):
            _invalidar_cache(); st.rerun()
    else:
        cg1,cg2 = st.columns([4,1])
        with cg1:
            deps_g = sorted([str(d2) for d2 in df_g["Deporte"].dropna().unique() if str(d2).strip()]) if "Deporte" in df_g.columns else []
            deporte_filtro = st.selectbox("Filtrar por deporte", ["Todos"]+deps_g)
        with cg2:
            st.markdown("<div style='margin-top:28px'>", unsafe_allow_html=True)
            if st.button("🔄 Actualizar", key="reload_grupo2"):
                _invalidar_cache(); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        df_grp = df_g.copy()
        if deporte_filtro != "Todos" and "Deporte" in df_grp.columns:
            df_grp = df_grp[df_grp["Deporte"]==deporte_filtro]
        try:
            df_grp = df_grp.sort_values("Fecha").groupby("Nombre",as_index=False).last()
        except Exception:
            pass

        st.markdown(f"**{len(df_grp)} atleta(s) en el grupo**")

        pares = [
            ("CMJ_cm","CMJ (cm)"),("SJ_cm","Squat Jump (cm)"),
            ("F_Rel_NKg","Fuerza Relativa (N/kg)"),("RSI_Mod","RSI Modificado"),
        ]
        for ca,cb in zip(pares[::2],pares[1::2]):
            c1g,c2g = st.columns(2)
            with c1g:
                fig=chart_barras_grupo(df_grp,ca[0],ca[1])
                if fig: st.plotly_chart(fig,use_container_width=True,key=f"gg_{ca[0]}")
            with c2g:
                fig=chart_barras_grupo(df_grp,cb[0],cb[1])
                if fig: st.plotly_chart(fig,use_container_width=True,key=f"gg_{cb[0]}")

        st.markdown("#### Tabla Resumen")
        cd=[c for c in ["Nombre","Deporte","Fecha","SJ_cm","CMJ_cm",
                         "Abalakov_cm","F_Rel_NKg","RSI_Mod","Ratio_AdAb",
                         "Sprint_10m_s","VO2Max","VAM_kmh"]
            if c in df_grp.columns]
        st.dataframe(df_grp[cd] if cd else df_grp, use_container_width=True)

        with st.spinner("Preparando PDF grupal…"):
            pdf_grp = generar_pdf_grupal(df_grp)
        st.download_button(
            label="📥 DESCARGAR INFORME GRUPAL (PDF)",
            data=pdf_grp,
            file_name=f"BioSport_Grupal_{deporte_filtro.replace(' ','_')}_{datetime.now().strftime('%d%m%Y')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
