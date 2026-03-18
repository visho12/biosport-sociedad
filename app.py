import streamlit as st

# Configuración de la página
st.set_page_config(page_title="Bio Sport - Evaluaciones", page_icon="⚡", layout="centered")

# --- ENCABEZADO CON LOGO ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    # Asegúrate de que el nombre aquí sea exactamente igual al archivo que subiste
    st.image("logo.png", use_container_width=True)

st.markdown("<h4 style='text-align: center; color: gray;'>Sistema de Evaluación de Rendimiento</h4>", unsafe_allow_html=True)
st.markdown("---")

# --- FORMULARIO EN DESPLEGABLE ---
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

# --- BOTÓN DE CÁLCULO ---
st.markdown("<br>", unsafe_allow_html=True)
calcular = st.button("📊 CALCULAR RESULTADOS", type="primary", use_container_width=True)

# --- DASHBOARD DE RESULTADOS ---
if calcular:
    if peso > 0:
        st.markdown("---")
        st.markdown("<h2 style='text-align: center;'>INFORME DEL ATLETA</h2>", unsafe_allow_html=True)
        
        fuerza_relativa = imtp / peso
        
        # --- SECCIÓN IMTP VISUAL ---
        st.write("### 🏋️ Fuerza Relativa (IMTP)")
        
        if fuerza_relativa > 40:
            estado_fuerza = "🟢 Óptimo"
            color_fuerza = "normal"
        elif 30 <= fuerza_relativa <= 40:
            estado_fuerza = "🟡 Medio"
            color_fuerza = "off"
        else:
            estado_fuerza = "🔴 Déficit"
            color_fuerza = "inverse"
            
        st.metric(label="Newtons por Kg", value=f"{fuerza_relativa:.2f} N/kg", delta=estado_fuerza, delta_color=color_fuerza)
        
        # --- SECCIÓN RATIO VISUAL ---
        st.write("### ⚖️ Balance de Cadera")
        if abductores > 0:
            ratio = aductores / abductores
            
            if 0.90 <= ratio <= 1.10:
                estado_ratio = "🟢 Simetría (Bajo Riesgo)"
                color_ratio = "normal"
            elif (0.80 <= ratio < 0.90) or (1.10 < ratio <= 1.20):
                estado_ratio = "🟡 Precaución (Leve Dominancia)"
                color_ratio = "off"
            else:
                estado_ratio = "🔴 Desbalance (Riesgo de Lesión)"
                color_ratio = "inverse"
                
            st.metric(label="Ratio (Aductores/Abductores)", value=f"{ratio:.2f}", delta=estado_ratio, delta_color=color_ratio)
            
            col_bar1, col_bar2 = st.columns(2)
            with col_bar1:
                st.info(f"**Aductores:** {aductores} N")
            with col_bar2:
                st.warning(f"**Abductores:** {abductores} N")
        else:
            st.info("Ingresa los datos de abductores para calcular el ratio.")
            
    else:
        st.error("⚠️ Por favor, ingresa el peso del atleta para calcular la fuerza relativa.")
