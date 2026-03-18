import streamlit as st

st.set_page_config(page_title="Bio Sport - Evaluaciones", page_icon="⚡", layout="centered")

st.title("⚡ Bio Sport - Evaluación")

st.header("1. Perfil del Atleta")
col1, col2 = st.columns(2)
with col1:
    nombre = st.text_input("Nombre")
    edad = st.number_input("Edad", min_value=10, max_value=100, step=1)
with col2:
    peso = st.number_input("Peso (kg)", min_value=30.0, max_value=150.0, step=0.1)
    deporte = st.text_input("Deporte / Posición")

st.header("2. Resultados Tecnología Garrido")
st.subheader("Fuerza e Isometría")
imtp = st.number_input("IMTP (Newtons)", min_value=0.0, step=10.0)

st.subheader("Saltometría (cm)")
col_sj, col_cmj, col_aba = st.columns(3)
with col_sj:
    sj = st.number_input("SJ", min_value=0.0, step=0.1)
with col_cmj:
    cmj = st.number_input("CMJ", min_value=0.0, step=0.1)
with col_aba:
    abalakov = st.number_input("Abalakov", min_value=0.0, step=0.1)

st.subheader("Dinamometría de Cadera")
col_ad, col_ab = st.columns(2)
with col_ad:
    aductores = st.number_input("Aductores", min_value=0.0, step=1.0)
with col_ab:
    abductores = st.number_input("Abductores", min_value=0.0, step=1.0)

notas = st.text_area("Notas o Sensaciones del Día")

if st.button("Calcular Resultados", type="primary"):
    if peso > 0:
        fuerza_relativa = imtp / peso
        
        st.markdown("---")
        st.header("📊 Informe de Resultados")
        
        # Lógica IMTP
        st.subheader("Tirón Isométrico (IMTP)")
        st.write(f"**Fuerza Relativa:** {fuerza_relativa:.2f} N/kg")
        if fuerza_relativa > 40:
            st.success("🟢 Óptimo (Excelente producción de fuerza)")
        elif 30 <= fuerza_relativa <= 40:
            st.warning("🟡 Medio (Aceptable, con margen de mejora)")
        else:
            st.error("🔴 Déficit (Fuerza base insuficiente)")
            
        # Lógica Ratio
        st.subheader("Ratio de Cadera (Aductores / Abductores)")
        if abductores > 0:
            ratio = aductores / abductores
            st.write(f"**Ratio:** {ratio:.2f}")
            if 0.90 <= ratio <= 1.10:
                st.success("🟢 Simetría (Fuerzas equilibradas, bajo riesgo)")
            elif (0.80 <= ratio < 0.90) or (1.10 < ratio <= 1.20):
                st.warning("🟡 Precaución (Leve dominancia, vigilar)")
            else:
                st.error("🔴 Desbalance (Alto riesgo de lesión)")
        else:
            st.info("Ingresa los datos de abductores para calcular el ratio.")
    else:
        st.error("⚠️ Por favor, ingresa el peso del atleta para poder calcular la fuerza relativa.")
