import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE TU HOJA (ESTO ES LO ÚNICO QUE DEBES CAMBIAR) ---
# Copia aquí el ID largo que sacaste en el Paso 1
ID_HOJA = "TU_ID_AQUI" 
URL_DATOS = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/export?format=csv&gid=0"

st.set_page_config(page_title="Gastos Leonardo y Esposa", page_icon="💰")
st.title("🏠 Control de Gastos del Hogar")

# --- LEER LOS DATOS ---
try:
    # Leemos la hoja directamente como un archivo CSV
    df = pd.read_csv(URL_DATOS)
    
    # Si la hoja está vacía, creamos la estructura
    if df.empty:
        df = pd.DataFrame(columns=["Fecha", "Concepto", "Monto", "Pagador"])
except:
    st.error("No pude conectar con Google Sheets. Revisa el ID y los permisos de compartir.")
    st.stop()

# --- FORMULARIO PARA REGISTRAR ---
with st.expander("➕ Registrar nuevo gasto"):
    with st.form("nuevo_gasto"):
        fecha = st.date_input("Fecha", datetime.now())
        concepto = st.text_input("¿En qué gastamos?")
        monto = st.number_input("Monto total", min_value=0.0, step=1.0)
        pagador = st.selectbox("¿Quién lo pagó?", ["Leonardo", "Esposa"])
        
        if st.form_submit_button("Guardar Gasto"):
            if concepto and monto > 0:
                st.success("¡Gasto anotado! (Para guardar permanentemente en la nube, necesitamos configurar la llave de escritura).")
                # Por ahora, esto solo lo muestra en pantalla para probar
                nueva_fila = pd.DataFrame([[fecha, concepto, monto, pagador]], columns=df.columns)
                df = pd.concat([df, nueva_fila], ignore_index=True)
            else:
                st.warning("Por favor llena todos los campos.")

# --- CUENTAS MATEMÁTICAS ---
total_leo = df[df['Pagador'] == 'Leonardo']['Monto'].sum()
total_esposa = df[df['Pagador'] == 'Esposa']['Monto'].sum()
mitad = (total_leo + total_esposa) / 2

st.divider()
col1, col2 = st.columns(2)
col1.metric("Leonardo pagó", f"${total_leo:,.0f}")
col2.metric("Esposa pagó", f"${total_esposa:,.0f}")

# ¿Quién le debe a quién?
if total_leo > mitad:
    st.info(f"💡 Tu esposa debe darte: **${total_leo - mitad:,.0f}**")
elif total_esposa > mitad:
    st.info(f"💡 Debes darle a tu esposa: **${total_esposa - mitad:,.0f}**")
else:
    st.success("✅ ¡Están a mano!")

st.subheader("📝 Historial de Gastos")
st.dataframe(df, use_container_width=True)