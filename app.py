import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
import requests

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Finanzas Familiares", page_icon="📊", layout="wide")

# --- 1. CONFIGURACIÓN DE PRESUPUESTOS ---
PRESUPUESTOS_FAMILIARES = {
    "Almuerzos de trabajo": 520000,
    "Almuerzos fines de semana": 1200000,
    "Mercado": 600000
}

TODAS_CATEGORIAS = ["Almuerzos de trabajo", "Almuerzos fines de semana", "Mercado", "Transporte", "Servicios", "Ocio", "Salud", "Otro"]

# --- FUNCIÓN DE NOTIFICACIÓN ---
def enviar_notificacion(mensaje):
    try:
        token = st.secrets["telegram_token"]
        chat_id = st.secrets["telegram_chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": mensaje, "parse_mode": "Markdown"})
    except:
        pass

# --- 2. CARGA Y LIMPIEZA DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)
df_raw = conn.read(ttl="0")

# Limpieza inicial de nombres de columnas y filas vacías
df_raw.columns = df_raw.columns.str.strip()
df = df_raw.dropna(how='all').copy()

# ARREGLO DE FECHAS: Forzamos que entienda que el día va primero (ej: 10/3/2026)
df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')

# Borramos lo que no sea fecha válida y limpiamos montos
df = df.dropna(subset=['Fecha'])
df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)

# --- 3. BARRA LATERAL (FILTROS) ---
st.sidebar.header("🔍 Histórico")
meses_dict = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}

anhos_lista = sorted(df['Fecha'].dt.year.unique(), reverse=True)
if datetime.now().year not in anhos_lista:
    anhos_lista.insert(0, datetime.now().year)

anho_sel = st.sidebar.selectbox("Año", anhos_lista)
mes_sel_nom = st.sidebar.selectbox("Mes", list(meses_dict.values()), index=datetime.now().month-1)
mes_sel_num = [k for k, v in meses_dict.items() if v == mes_sel_nom][0]

# Filtro para el tablero actual
df_mes = df[(df['Fecha'].dt.month == mes_sel_num) & (df['Fecha'].dt.year == anho_sel)]

# --- 4. FORMULARIO DE REGISTRO ---
st.title("🏠 Control de Gastos: Leo & Esposa")
with st.expander("➕ REGISTRAR NUEVO GASTO"):
    with st.form("nuevo_gasto"):
        c1, c2 = st.columns(2)
        fecha_g = c1.date_input("Fecha", datetime.now())
        cat_g = c2.selectbox("Categoría", TODAS_CATEGORIAS)
        con_g = st.text_input("Concepto")
        mon_g = st.number_input("Monto", min_value=0.0, step=100.0)
        pag_g = st.selectbox("¿Quién pagó?", ["Leonardo", "Esposa"])
        
        if st.form_submit_button("💾 Guardar"):
            if con_g and mon_g > 0:
                nueva_fila = pd.DataFrame([{"Fecha": fecha_g.strftime("%Y-%m-%d"), "Concepto": con_g, "Monto": mon_g, "Pagador": pag_g, "Categoría": cat_g}])
                df_final = pd.concat([df, nueva_fila], ignore_index=True)
                conn.update(data=df_final)
                
                # Alerta de presupuesto
                aviso = f"💰 *Gasto:* ${mon_g:,.0f}\n📝 {con_g} ({cat_g})"
                if cat_g in PRESUPUESTOS_FAMILIARES:
                    total_cat = df_mes[df_mes['Categoría'] == cat_g]['Monto'].sum() + mon_g
                    if total_cat > PRESUPUESTOS_FAMILIARES[cat_g]:
                        aviso += f"\n🚨 *ALERTA:* Límite de {cat_g} superado."
                
                enviar_notificacion(aviso)
                st.success("¡Guardado!")
                st.rerun()

# --- 5. VISUALIZACIÓN DE PRESUPUESTOS ---
st.header(f"🎯 Metas Familiares ({mes_sel_nom} {anho_sel})")
cols_p = st.columns(len(PRESUPUESTOS_FAMILIARES))
for i, (cat, limite) in enumerate(PRESUPUESTOS_FAMILIARES.items()):
    gastado = df_mes[df_mes['Categoría'] == cat]['Monto'].sum()
    progreso = min(gastado / limite, 1.0) if limite > 0 else 0
    with cols_p[i]:
        st.write(f"**{cat}**")
        st.progress(progreso)
        st.caption(f"${gastado:,.0f} de ${limite:,.0f}")

# --- 6. BALANCE GENERAL ---
st.divider()
st.subheader("📊 Cuentas del Mes")
if not df_mes.empty:
    t_leo = df_mes[df_mes['Pagador'] == 'Leonardo']['Monto'].sum()
    t_esp = df_mes[df_mes['Pagador'] == 'Esposa']['Monto'].sum()
    
    # Cálculo matemático del balance
    # $$ \text{Mitad} = \frac{\text{Total Leo} + \text{Total Esposa}}{2} $$
    mitad = (t_leo + t_esp) / 2
    
    b1, b2, b3 = st.columns(3)
    b1.metric("Leonardo pagó", f"${t_leo:,.0f}")
    b2.metric("Esposa pagó", f"${t_esp:,.0f}")
    
    if t_leo > mitad:
        b3.info(f"💡 Esposa debe: **${t_leo - mitad:,.0f}**")
    elif t_esp > mitad:
        b3.info(f"💡 Leonardo debe: **${t_esp - mitad:,.0f}**")
    else:
        b3.success("✅ ¡Están a mano!")

    st.plotly_chart(px.pie(df_mes, values='Monto', names='Categoría', hole=0.5, title="Distribución de Gastos"), use_container_width=True)
else:
    st.info("No hay datos para este mes.")

# --- 7. INVESTIGADOR DE DATOS (DEBUG) ---
with st.expander("🛠️ INVESTIGADOR DE DATOS"):
    st.write("Fila con error detectada anteriormente:")
    st.dataframe(df_raw[pd.to_datetime(df_raw['Fecha'], dayfirst=True, errors='coerce').isna()])
    st.write("Todos los datos procesados correctamente:")
    st.dataframe(df)