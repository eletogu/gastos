import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gastos Casa", page_icon="💰")

st.title("🏠 Control de Gastos Compartidos")

# 1. Conexión usando los Secrets (la llave maestra)
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Leer datos actuales
df = conn.read(ttl="0") # ttl="0" asegura que siempre lea lo más nuevo

# --- FORMULARIO PARA REGISTRAR ---
with st.form("formulario_gastos"):
    st.subheader("Anotar Gasto Nuevo")
    fecha = st.date_input("Fecha", datetime.now())
    concepto = st.text_input("¿En qué se gastó?")
    monto = st.number_input("Monto", min_value=0.0, step=0.01)
    pagador = st.selectbox("¿Quién pagó?", ["Leonardo", "Esposa"])
    
    boton_guardar = st.form_submit_button("Guardar en Excel")

    if boton_guardar:
        if concepto and monto > 0:
            # Crear la nueva fila
            nueva_fila = pd.DataFrame([{
                "Fecha": fecha.strftime("%Y-%m-%d"),
                "Concepto": concepto,
                "Monto": monto,
                "Pagador": pagador
            }])
            
            # Unir con los datos viejos y subir a la nube
            df_actualizado = pd.concat([df, nueva_fila], ignore_index=True)
            conn.update(data=df_actualizado)
            
            st.success("✅ ¡Gasto guardado en Google Sheets!")
            st.rerun() # Recarga la app para mostrar el nuevo gasto
        else:
            st.error("Por favor completa los campos.")

# --- CÁLCULOS ---
df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
total_leo = df[df['Pagador'] == 'Leonardo']['Monto'].sum()
total_esposa = df[df['Pagador'] == 'Esposa']['Monto'].sum()
mitad = (total_leo + total_esposa) / 2

st.divider()
st.subheader("📊 Resumen de Cuentas")
c1, c2 = st.columns(2)
c1.metric("Leonardo pagó", f"${total_leo:,.2f}")
c2.metric("Esposa pagó", f"${total_esposa:,.2f}")

if total_leo > mitad:
    st.info(f"💡 Tu esposa te debe: **${total_leo - mitad:,.2f}**")
elif total_esposa > mitad:
    st.info(f"💡 Debes pagarle a tu esposa: **${total_esposa - mitad:,.2f}**")
else:
    st.success("✅ ¡Están a mano!")

st.subheader("📝 Historial")
st.dataframe(df.sort_index(ascending=False), use_container_width=True)