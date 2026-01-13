import streamlit as st
import time

# Configuración profesional de Alphabot System
st.set_page_config(page_title="Alphabot System V7", layout="wide")

st.title("🛡️ Alphabot System - Panel de Control")
st.sidebar.header("Menú de Gestión")

# SIMULACIÓN DE DATOS PARA QUE LA WEB DESPIERTE
balance_prueba = 10500.0
equity_prueba = 10780.0

# DISEÑO DEL PANEL
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Balance Total", f"${balance_prueba:,.2f}")
with col2:
    st.metric("Equidad (Equity)", f"${equity_prueba:,.2f}")
with col3:
    st.metric("Estado del Bot", "ONLINE ✅")

st.markdown("---")
st.subheader("Configuración de Activos")
st.write("Operando: **ORO (Magic 999)** y **EURUSD (Magic 888)**")

# BOTÓN DE PÁNICO EN EL CELULAR
if st.sidebar.button("🚨 BOTÓN DE PÁNICO: CERRAR TODO"):
    st.sidebar.error("ORDEN DE CIERRE ENVIADA")

st.info("Nota: Esta es la vista previa. Conecta tu PC para ver datos reales.")








