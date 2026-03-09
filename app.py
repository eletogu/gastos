import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Gastos Casa - Leo & Esposa", page_icon="💰", layout="centered")

# --- ENLACE DIRECTO QUE ME PASASTE ---
URL_DATOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQzfz6-STH-ExIgkD_2eILO860HPoaLenslqCc-gLdwCJLMYZfTR06oszHU1dxr5_G2tXPdDhj2b8pC/pub?output=csv"

st.title("🏠 Control de Gastos Compartidos")
st.write("Registren sus gastos y la app calculará las cuentas automáticamente.")

# --- CARGAR DATOS ---
try:
    # Leemos la hoja de Google Sheets
    df = pd.read_csv(URL_DATOS)
    
    # Limpiamos nombres de columnas por si acaso hay espacios
    df.columns = df.columns.str.strip()
    
    # Si la hoja está vacía, creamos la estructura base
    if df.empty:
        df = pd.DataFrame(columns=["Fecha", "Concepto", "Monto", "Pagador"])
except Exception as e:
    st.error("❌ No se pudo conectar con los datos.")
    st.info("Revisa que tu Google Sheet tenga la primera fila con: Fecha, Concepto, Monto, Pagador")
    st.stop()

# --- FORMULARIO PARA REGISTRAR ---
st.markdown("---")
with st.expander("➕ REGISTRAR UN NUEVO GASTO", expanded=False):
    with st.form("mi_formulario"):
        fecha = st.date_input("Fecha del gasto", datetime.now())
        concepto = st.text_input("¿En qué se gastó? (Ej: Supermercado, Arriendo)")
        monto = st.number_input("¿Cuánto costó?", min_value=0.0, step=0.01)
        pagador = st.selectbox("¿Quién pagó?", ["Leonardo", "Esposa"])
        
        enviar = st.form_submit_button("Anotar Gasto")
        
        if enviar:
            if concepto and monto > 0:
                st.success(f"✅ Gasto de {pagador} anotado temporalmente.")
                st.warning("⚠️ Nota: Para que se guarde permanentemente en el Excel, debes anotarlo directamente en la hoja de Google Sheets por ahora.")
            else:
                st.error("Por favor llena el concepto y el monto.")

# --- CÁLCULOS MATEMÁTICOS ---
# Aseguramos que 'Monto' sea número
df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)

total_leo = df[df['Pagador'] == 'Leonardo']['Monto'].sum()
total_esposa = df[df['Pagador'] == 'Esposa']['Monto'].sum()
total_general = total_leo + total_esposa
mitad = total_general / 2

# --- MOSTRAR RESULTADOS ---
st.markdown("### 📊 Resumen de Cuentas")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Leonardo")
    st.metric("Pagó", f"${total_leo:,.2f}")

with col2:
    st.subheader("Esposa")
    st.metric("Pagó", f"${total_esposa:,.2f}")

st.markdown("---")

# Lógica de quién debe a quién
if total_leo > mitad:
    deuda = total_leo - mitad
    st.info(f"💡 **Tu esposa debe pagarte: ${deuda:,.2f}**")
elif total_esposa > mitad:
    deuda = total_esposa - mitad
    st.info(f"💡 **Debes pagarle a tu esposa: ${deuda:,.2f}**")
else:
    st.success("✨ ¡Están totalmente a mano!")

# --- TABLA DE HISTORIAL ---
st.markdown("### 📝 Historial de Movimientos")
st.dataframe(df.sort_index(ascending=False), use_container_width=True)