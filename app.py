import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
import requests

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Finanzas Hogar - Leo & Esposa", page_icon="📊", layout="wide")

# --- FUNCIÓN PARA NOTIFICACIONES DE TELEGRAM ---
def enviar_notificacion(mensaje):
    try:
        token = st.secrets["telegram_token"]
        chat_id = st.secrets["telegram_chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": mensaje, "parse_mode": "Markdown"})
    except Exception as e:
        st.sidebar.warning(f"Error de notificación: {e}")

st.title("🏠 Sistema de Gastos Compartidos")

# --- 1. CONEXIÓN Y CARGA DE DATOS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl="0")

    # --- LIMPIEZA DE DATOS (PARA EVITAR ERRORES DE FECHA) ---
    df = df.dropna(how='all') # Borrar filas totalmente vacías
    
    # Convertimos Fecha ignorando errores (coerce los vuelve NaT/vacíos)
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    
    # Borramos filas donde la fecha no se pudo leer
    df = df.dropna(subset=['Fecha'])
    
    # Aseguramos que Monto sea numérico
    df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
except Exception as e:
    st.error("Hubo un problema cargando los datos del Excel.")
    st.info("Asegúrate de que la Fila 1 tenga: Fecha, Concepto, Monto, Pagador, Categoría")
    st.stop()

# --- 2. BARRA LATERAL: FILTRO POR MES ---
st.sidebar.header("🔍 Histórico de Meses")
meses_nombres = {1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun", 
                 7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"}

# Años y meses disponibles en los datos registrados
años_disponibles = sorted(df['Fecha'].dt.year.unique(), reverse=True)
if not años_disponibles: años_disponibles = [datetime.now().year]

anho_sel = st.sidebar.selectbox("Selecciona el Año", años_disponibles)
mes_sel_nom = st.sidebar.selectbox("Selecciona el Mes", list(meses_nombres.values()), index=datetime.now().month-1)
mes_sel_num = [k for k, v in meses_nombres.items() if v == mes_sel_nom][0]

# Filtrar datos para el tablero
df_mes = df[(df['Fecha'].dt.month == mes_sel_num) & (df['Fecha'].dt.year == anho_sel)]

# --- 3. FORMULARIO PARA REGISTRAR GASTO ---
with st.expander("➕ REGISTRAR NUEVO GASTO", expanded=False):
    with st.form("nuevo_gasto_form"):
        col_a, col_b = st.columns(2)
        fecha_g = col_a.date_input("Fecha", datetime.now())
        cat_g = col_b.selectbox("Categoría", ["Mercado", "Servicios", "Arriendo", "Salud", "Ocio", "Transporte", "Otro"])
        
        con_g = st.text_input("Concepto (Ej: Pago Internet)")
        mon_g = st.number_input("Monto total", min_value=0.0, step=100.0)
        pag_g = st.selectbox("¿Quién pagó?", ["Leonardo", "Esposa"])
        
        btn_guardar = st.form_submit_button("💾 Guardar Gasto")

        if btn_guardar:
            if con_g and mon_g > 0:
                # Crear nueva fila
                nueva_fila = pd.DataFrame([{
                    "Fecha": fecha_g.strftime("%Y-%m-%d"),
                    "Concepto": con_g,
                    "Monto": mon_g,
                    "Pagador": pag_g,
                    "Categoría": cat_g
                }])
                
                # Actualizar Google Sheets
                df_final = pd.concat([df, nueva_fila], ignore_index=True)
                conn.update(data=df_final)
                
                # Notificación Telegram
                texto_bot = f"💰 *¡Gasto Registrado!*\n\n" \
                            f"👤 *Pagó:* {pag_g}\n" \
                            f"📝 *Concepto:* {con_g}\n" \
                            f"🏷️ *Categoría:* {cat_g}\n" \
                            f"💵 *Monto:* ${mon_g:,.0f}"
                enviar_notificacion(texto_bot)
                
                st.success("✅ ¡Gasto guardado y notificado!")
                st.rerun()
            else:
                st.error("Por favor llena todos los campos.")

# --- 4. DASHBOARD DE RESULTADOS ---
st.header(f"📊 Resumen de {mes_sel_nom} {anho_sel}")

if not df_mes.empty:
    t_leo = df_mes[df_mes['Pagador'] == 'Leonardo']['Monto'].sum()
    t_esp = df_mes[df_mes['Pagador'] == 'Esposa']['Monto'].sum()
    total_mes = t_leo + t_esp
    cuota = total_mes / 2

    # Métricas
    m1, m2, m3 = st.columns(3)
    m1.metric("Leonardo pagó", f"${t_leo:,.0f}")
    m2.metric("Esposa pagó", f"${t_esp:,.0f}")

    if t_leo > cuota:
        m3.info(f"💡 Esposa debe dar a Leo: **${t_leo - cuota:,.0f}**")
    elif t_esp > cuota:
        m3.info(f"💡 Leo debe dar a Esposa: **${t_esp - cuota:,.0f}**")
    else:
        m3.success("✅ ¡Cuentas claras! Están a mano.")

    st.divider()

    # Gráfica y Tabla
    g1, g2 = st.columns([1, 1])
    with g1:
        st.write("🍩 **Gastos por Categoría**")
        fig = px.pie(df_mes, values='Monto', names='Categoría', hole=0.5)
        st.plotly_chart(fig, use_container_width=True)
    with g2:
        st.write("📑 **Movimientos del Mes**")
        st.dataframe(df_mes[['Fecha', 'Concepto', 'Monto', 'Pagador', 'Categoría']].sort_values('Fecha', ascending=False), hide_index=True)
else:
    st.info(f"No hay gastos registrados en {mes_sel_nom} {anho_sel}.")