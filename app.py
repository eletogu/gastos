import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Gastos Casa", page_icon="💰")

st.title("🏠 Control de Gastos")

# 1. Conexión segura a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Leer datos existentes
df = conn.read(worksheet="Gastos", ttl="0")

# 2. Formulario para registrar nuevos gastos
with st.expander("➕ Registrar nuevo gasto"):
    with st.form("formulario_gasto"):
        fecha = st.date_input("Fecha", datetime.now())
        concepto = st.text_input("¿En qué gastamos?")
        monto = st.number_input("Monto total", min_value=0.0, step=1.0)
        pagador = st.selectbox("¿Quién lo pagó?", ["Leonardo", "Esposa"])
        
        submit = st.form_submit_button("Guardar Gasto")

        if submit and concepto and monto > 0:
            # Crear nueva fila
            nueva_fila = pd.DataFrame([{
                "Fecha": fecha.strftime("%Y-%m-%d"),
                "Concepto": concepto,
                "Monto": monto,
                "Pagador": pagador
            }])
            
            # Concatenar y actualizar la nube
            updated_df = pd.concat([df, nueva_fila], ignore_index=True)
            conn.update(worksheet="Gastos", data=updated_df)
            st.success("¡Gasto guardado!")
            st.rerun()

# 3. Lógica Matemática de Cuentas
# Calculamos totales por persona
total_leo = df[df['Pagador'] == 'Leonardo']['Monto'].sum()
total_esposa = df[df['Pagador'] == 'Esposa']['Monto'].sum()
total_gastado = total_leo + total_esposa
cuota_por_persona = total_gastado / 2

# 4. Mostrar Resumen Financiero
st.subheader("📊 Resumen del Mes")
col1, col2 = st.columns(2)
col1.metric("Leonardo pagó", f"${total_leo:,.0f}")
col2.metric("Esposa pagó", f"${total_esposa:,.0f}")

st.divider()

# Lógica de compensación
if total_leo > cuota_por_persona:
    deuda = total_leo - cuota_por_persona
    st.info(f"💡 Tu esposa debe darte: **${deuda:,.0f}**")
elif total_esposa > cuota_por_persona:
    deuda = total_esposa - cuota_por_persona
    st.info(f"💡 Debes darle a tu esposa: **${deuda:,.0f}**")
else:
    st.success("✅ ¡Están totalmente a mano!")

# 5. Historial de movimientos
st.subheader("📝 Historial")
st.dataframe(df.sort_index(ascending=False), use_container_width=True)