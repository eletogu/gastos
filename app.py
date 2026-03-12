import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
import requests

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Finanzas Familiares - Leo & Cata", page_icon="🇨🇴", layout="wide")

PRESUPUESTOS_FAMILIARES = {
    "Almuerzos de trabajo": 520000,
    "Almuerzos fines de semana": 1200000,
    "Mercado": 600000
}

TODAS_CATEGORIAS = ["Almuerzos de trabajo", "Almuerzos fines de semana", "Mercado", "Transporte", "Servicios", "Ocio", "Salud", "Otro"]

def enviar_notificacion(mensaje):
    try:
        token = st.secrets["telegram_token"]
        chat_id = st.secrets["telegram_chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": mensaje, "parse_mode": "Markdown"})
    except:
        pass

def cargar_datos():
    conn = st.connection("gsheets", type=GSheetsConnection)
    data = conn.read(ttl="0")
    data.columns = data.columns.str.strip()
    data = data.dropna(how='all')
    data['Fecha'] = pd.to_datetime(data['Fecha'], dayfirst=True, errors='coerce')
    return data

df_visualizacion = cargar_datos()

# --- FORMULARIO DE REGISTRO ---
st.title("🏠 Control de Gastos: Leo & Cata")

with st.expander("➕ REGISTRAR NUEVO GASTO", expanded=False):
    with st.form("nuevo_gasto", clear_on_submit=True):
        c1, c2 = st.columns(2)
        fecha_g = c1.date_input("Fecha", datetime.now())
        cat_g = c2.selectbox("Categoría", TODAS_CATEGORIAS)
        con_g = st.text_input("Concepto")
        mon_g = st.number_input("Monto (COP)", min_value=0.0, step=1000.0)
        pag_g = st.selectbox("¿Quién pagó?", ["Leonardo", "Cata"])
        
        if st.form_submit_button("💾 Guardar"):
            if con_g and mon_g > 0:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_db = conn.read(ttl="0") 
                nueva_fila = pd.DataFrame([{
                    "Fecha": fecha_g.strftime("%d/%m/%Y"), 
                    "Concepto": con_g,
                    "Monto": mon_g,
                    "Pagador": pag_g,
                    "Categoría": cat_g
                }])
                df_final = pd.concat([df_db, nueva_fila], ignore_index=True)
                conn.update(data=df_final)
                
                aviso = f"💰 *Gasto:* ${mon_g:,.0f} COP\n👤 {pag_g}\n📝 {con_g} ({cat_g})\n📅 {fecha_g.strftime('%d/%m/%Y')}"
                enviar_notificacion(aviso)
                st.success("¡Gasto guardado!")
                st.rerun()

# --- 🕒 ÚLTIMOS MOVIMIENTOS Y ELIMINACIÓN ---
st.subheader("🕒 Últimos 5 movimientos")
col_tabla, col_borrar = st.columns([3, 1])

with col_tabla:
    ultimos_5 = df_visualizacion.tail(5).iloc[::-1]
    if not ultimos_5.empty:
        ultimos_5_display = ultimos_5.copy()
        ultimos_5_display['Fecha'] = ultimos_5_display['Fecha'].dt.strftime('%d/%m/%Y')
        st.dataframe(ultimos_5_display, use_container_width=True, hide_index=True)
    else:
        st.info("No hay registros.")

with col_borrar:
    st.write("⚠️ **Zona de Peligro**")
    confirmar = st.checkbox("Confirmar borrar último")
    if confirmar:
        if st.button("🗑️ Eliminar último registro"):
            conn = st.connection("gsheets", type=GSheetsConnection)
            df_actual = conn.read(ttl="0")
            if not df_actual.empty:
                # Obtenemos info del que vamos a borrar para avisar
                fila_borrada = df_actual.iloc[-1]
                # Quitamos la última fila
                df_nuevo = df_actual.drop(df_actual.index[-1])
                conn.update(data=df_nuevo)
                
                # Notificación de borrado
                aviso_borrado = f"❌ *Gasto Eliminado*\nSe borró: {fila_borrada['Concepto']} por ${fila_borrada['Monto']:,.0f}"
                enviar_notificacion(aviso_borrado)
                
                st.warning("Registro eliminado.")
                st.rerun()
            else:
                st.error("No hay nada que borrar.")

st.divider()

# --- FILTROS Y DASHBOARD ---
st.sidebar.header("🔍 Histórico")
meses_dict = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
df_valid_dates = df_visualizacion.dropna(subset=['Fecha'])
anhos_lista = sorted(df_valid_dates['Fecha'].dt.year.unique(), reverse=True)
if datetime.now().year not in anhos_lista: anhos_lista.insert(0, datetime.now().year)

anho_sel = st.sidebar.selectbox("Año", anhos_lista)
mes_sel_nom = st.sidebar.selectbox("Mes", list(meses_dict.values()), index=datetime.now().month-1)
mes_sel_num = [k for k, v in meses_dict.items() if v == mes_sel_nom][0]

df_mes = df_valid_dates[(df_valid_dates['Fecha'].dt.month == mes_sel_num) & (df_valid_dates['Fecha'].dt.year == anho_sel)]

# --- DASHBOARD ---
st.header(f"🎯 Reporte de {mes_sel_nom} {anho_sel}")
if not df_mes.empty:
    # Presupuestos
    cols_p = st.columns(len(PRESUPUESTOS_FAMILIARES))
    for i, (cat, limite) in enumerate(PRESUPUESTOS_FAMILIARES.items()):
        gastado = df_mes[df_mes['Categoría'] == cat]['Monto'].sum()
        progreso = min(gastado / limite, 1.0) if limite > 0 else 0
        with cols_p[i]:
            st.write(f"**{cat}**")
            st.progress(progreso)
            st.caption(f"${gastado:,.0f} / ${limite:,.0f} COP")

    # Balance
    st.divider()
    t_leo = df_mes[df_mes['Pagador'] == 'Leonardo']['Monto'].sum()
    t_cata = df_mes[df_mes['Pagador'].isin(['Cata', 'Esposa'])]['Monto'].sum()
    mitad = (t_leo + t_cata) / 2
    
    b1, b2, b3 = st.columns(3)
    b1.metric("Leonardo pagó", f"${t_leo:,.0f}")
    b2.metric("Cata pagó", f"${t_cata:,.0f}")
    
    if t_leo > mitad:
        b3.info(f"💡 Cata debe: **${t_leo - mitad:,.0f} COP**")
    elif t_cata > mitad:
        b3.info(f"💡 Leo debe: **${t_cata - mitad:,.0f} COP**")
    else:
        b3.success("✅ ¡Atán a mano!")

    st.plotly_chart(px.pie(df_mes, values='Monto', names='Categoría', hole=0.5, title="Gastos por Categoría"), use_container_width=True)
else:
    st.info("No hay datos para el mes seleccionado.")