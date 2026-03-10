import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
import requests

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Finanzas Familiares", page_icon="📊", layout="wide")

# --- 1. CATEGORÍAS Y PRESUPUESTOS ---
# Solo mantenemos topes para lo que me pediste
PRESUPUESTOS_FAMILIARES = {
    "Almuerzos de trabajo": 520000,
    "Almuerzos fines de semana": 1200000,
    "Mercado": 600000
}

# Lista completa de categorías para el menú (incluyendo las que no tienen tope)
TODAS_CATEGORIAS = [
    "Almuerzos de trabajo", 
    "Almuerzos fines de semana", 
    "Mercado", 
    "Transporte", 
    "Servicios", 
    "Ocio", 
    "Salud", 
    "Otro"
]

def enviar_notificacion(mensaje):
    try:
        token = st.secrets["telegram_token"]
        chat_id = st.secrets["telegram_chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": mensaje, "parse_mode": "Markdown"})
    except:
        pass

# --- CARGA DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl="0")
df = df.dropna(how='all')
df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
df = df.dropna(subset=['Fecha'])
df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)

# --- FILTROS ---
st.sidebar.header("🔍 Histórico")
meses = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
años = sorted(df['Fecha'].dt.year.unique(), reverse=True)
if not años: años = [datetime.now().year]
anho_sel = st.sidebar.selectbox("Año", años)
mes_sel_nom = st.sidebar.selectbox("Mes", list(meses.values()), index=datetime.now().month-1)
mes_sel_num = [k for k, v in meses.items() if v == mes_sel_nom][0]

df_mes = df[(df['Fecha'].dt.month == mes_sel_num) & (df['Fecha'].dt.year == anho_sel)]

# --- FORMULARIO DE REGISTRO ---
with st.expander("➕ REGISTRAR GASTO DEL HOGAR", expanded=False):
    with st.form("nuevo_gasto"):
        c1, c2 = st.columns(2)
        fecha = c1.date_input("Fecha", datetime.now())
        cat_g = c2.selectbox("Categoría", TODAS_CATEGORIAS)
        
        con_g = st.text_input("Concepto (¿En qué se gastó?)")
        mon_g = st.number_input("Monto total", min_value=0.0, step=100.0)
        pag_g = st.selectbox("¿Quién pagó?", ["Leonardo", "Esposa"])
        
        if st.form_submit_button("💾 Guardar y Avisar"):
            if con_g and mon_g > 0:
                nueva_fila = pd.DataFrame([{
                    "Fecha": fecha.strftime("%Y-%m-%d"),
                    "Concepto": con_g,
                    "Monto": mon_g,
                    "Pagador": pag_g,
                    "Categoría": cat_g
                }])
                df_final = pd.concat([df, nueva_fila], ignore_index=True)
                conn.update(data=df_final)
                
                # Mensaje base
                aviso = f"💰 *Gasto Registrado*\n\n👤 {pag_g}\n📝 {con_g}\n💵 ${mon_g:,.0f}"
                
                # Alerta solo si tiene presupuesto definido
                if cat_g in PRESUPUESTOS_FAMILIARES:
                    gastado_total = df_mes[df_mes['Categoría'] == cat_g]['Monto'].sum() + mon_g
                    limite = PRESUPUESTOS_FAMILIARES[cat_g]
                    if gastado_total > limite:
                        aviso += f"\n\n🚨 *ALERTA:* Excedieron el presupuesto de *{cat_g}*."
                
                enviar_notificacion(aviso)
                st.success("¡Gasto guardado!")
                st.rerun()

# --- SECCIÓN DE PRESUPUESTOS ACTIVOS ---
st.header(f"🎯 Control de Presupuestos ({mes_sel_nom})")
if PRESUPUESTOS_FAMILIARES:
    cols = st.columns(len(PRESUPUESTOS_FAMILIARES))
    for i, (cat, limite) in enumerate(PRESUPUESTOS_FAMILIARES.items()):
        gastado = df_mes[df_mes['Categoría'] == cat]['Monto'].sum()
        progreso = min(gastado / limite, 1.0) if limite > 0 else 0
        with cols[i]:
            st.write(f"**{cat}**")
            st.progress(progreso)
            if gastado > limite:
                st.error(f"${gastado:,.0f} / ${limite:,.0f}")
            else:
                st.caption(f"${gastado:,.0f} de ${limite:,.0f}")

# --- DASHBOARD DE BALANCE ---
st.divider()
st.subheader("📊 Balance General del Mes")
if not df_mes.empty:
    t_leo = df_mes[df_mes['Pagador'] == 'Leonardo']['Monto'].sum()
    t_esp = df_mes[df_mes['Pagador'] == 'Esposa']['Monto'].sum()
    mitad = (t_leo + t_esp) / 2
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Leonardo pagó", f"${t_leo:,.0f}")
    col2.metric("Esposa pagó", f"${t_esp:,.0f}")
    
    if t_leo > mitad:
        col3.info(f"💡 Esposa debe: **${t_leo - mitad:,.0f}**")
    elif t_esp > mitad:
        col3.info(f"💡 Leonardo debe: **${t_esp - mitad:,.0f}**")
    else:
        col3.success("✅ ¡A mano!")

    st.plotly_chart(px.pie(df_mes, values='Monto', names='Categoría', hole=0.5, title="Distribución de Gastos"), use_container_width=True)
else:
    st.info("Aún no hay gastos registrados para este mes.")