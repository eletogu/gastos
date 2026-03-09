import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
import requests

st.set_page_config(page_title="Finanzas Familiares", page_icon="💰", layout="wide")

# --- FUNCIÓN PARA ENVIAR NOTIFICACIONES ---
def enviar_notificacion(mensaje):
    token = st.secrets["telegram_token"]
    chat_id = st.secrets["telegram_chat_id"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        # Enviamos con parse_mode='Markdown' para que los negritas se vean bien
        requests.post(url, json={"chat_id": chat_id, "text": mensaje, "parse_mode": "Markdown"})
    except Exception as e:
        st.warning(f"No se pudo enviar la notificación: {e}")

st.title("🏠 Control de Gastos: Leonardo & Esposa")

# 1. Conexión con Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl="0")

# Limpieza de datos
df['Fecha'] = pd.to_datetime(df['Fecha'])
df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)

# --- BARRA LATERAL: FILTROS ---
st.sidebar.header("🔍 Histórico")
meses = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
anho_sel = st.sidebar.selectbox("Año", sorted(df['Fecha'].dt.year.unique(), reverse=True))
mes_sel_nom = st.sidebar.selectbox("Mes", list(meses.values()), index=datetime.now().month-1)
mes_sel_num = [k for k, v in meses.items() if v == mes_sel_nom][0]

df_filtrado = df[(df['Fecha'].dt.month == mes_sel_num) & (df['Fecha'].dt.year == anho_sel)]

# --- FORMULARIO DE REGISTRO ---
with st.expander("➕ REGISTRAR NUEVO GASTO", expanded=False):
    with st.form("nuevo_gasto"):
        c1, c2 = st.columns(2)
        fecha = c1.date_input("Fecha", datetime.now())
        categoria = c2.selectbox("Categoría", ["Mercado", "Servicios", "Arriendo", "Salud", "Ocio", "Transporte", "Otro"])
        concepto = st.text_input("¿Qué se compró?")
        monto = st.number_input("Valor", min_value=0.0, step=100.0)
        pagador = st.selectbox("¿Quién pagó?", ["Leonardo", "Esposa"])
        
        if st.form_submit_button("Guardar Gasto"):
            if concepto and monto > 0:
                nueva_fila = pd.DataFrame([{
                    "Fecha": fecha.strftime("%Y-%m-%d"), 
                    "Concepto": concepto, 
                    "Monto": monto, 
                    "Pagador": pagador, 
                    "Categoría": categoria
                }])
                df_actualizado = pd.concat([df, nueva_fila], ignore_index=True)
                conn.update(data=df_actualizado)
                
                # PREPARAR Y ENVIAR MENSAJE
                aviso = f"💰 *¡Nuevo Gasto Registrado!*\n\n" \
                        f"👤 *Pagó:* {pagador}\n" \
                        f"📝 *Concepto:* {concepto}\n" \
                        f"🏷️ *Categoría:* {categoria}\n" \
                        f"💵 *Monto:* ${monto:,.0f}"
                enviar_notificacion(aviso)
                
                st.success("✅ Guardado y notificado a Telegram.")
                st.rerun()

# --- DASHBOARD ---
st.header(f"📊 Reporte de {mes_sel_nom} {anho_sel}")

if not df_filtrado.empty:
    t_leo = df_filtrado[df_filtrado['Pagador'] == 'Leonardo']['Monto'].sum()
    t_esp = df_filtrado[df_filtrado['Pagador'] == 'Esposa']['Monto'].sum()
    mitad = (t_leo + t_esp) / 2

    m1, m2, m3 = st.columns(3)
    m1.metric("Leonardo pagó", f"${t_leo:,.0f}")
    m2.metric("Esposa pagó", f"${t_esp:,.0f}")

    if t_leo > mitad:
        m3.info(f"💡 Esposa debe dar a Leo: **${t_leo - mitad:,.0f}**")
    elif t_esp > mitad:
        m3.info(f"💡 Leo debe dar a Esposa: **${t_esp - mitad:,.0f}**")
    else:
        m3.success("✅ ¡Están a mano este mes!")

    st.divider()
    g1, g2 = st.columns([1, 1])
    with g1:
        fig = px.pie(df_filtrado, values='Monto', names='Categoría', hole=0.5, title="Distribución del Gasto")
        st.plotly_chart(fig, use_container_width=True)
    with g2:
        st.write("📝 **Detalle del Mes**")
        st.dataframe(df_filtrado[['Fecha', 'Concepto', 'Monto', 'Pagador', 'Categoría']].sort_values('Fecha', ascending=False), hide_index=True)
else:
    st.info("No hay registros para este período.")