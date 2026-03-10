import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
import requests

st.set_page_config(page_title="Finanzas Familiares", page_icon="📊", layout="wide")

# --- CONFIGURACIÓN ---
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

# --- CARGA Y LIMPIEZA TOTAL ---
conn = st.connection("gsheets", type=GSheetsConnection)
df_raw = conn.read(ttl="0")

# 1. Limpiar espacios en los nombres de las columnas
df_raw.columns = df_raw.columns.str.strip()

# 2. Limpiar espacios dentro de los datos y quitar filas vacías
df = df_raw.dropna(how='all').copy()
for col in df.columns:
    if df[col].dtype == "object":
        df[col] = df[col].astype(str).str.strip()

# 3. Convertir Fecha y Monto con seguridad
df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
df = df.dropna(subset=['Fecha'])
df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)

# --- FILTROS ---
st.sidebar.header("🔍 Histórico")
meses_dict = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}

# Asegurar que el año actual aparezca
anhos_lista = sorted(df['Fecha'].dt.year.unique(), reverse=True)
if datetime.now().year not in anhos_lista:
    anhos_lista.insert(0, datetime.now().year)

anho_sel = st.sidebar.selectbox("Año", anhos_lista)
mes_sel_nom = st.sidebar.selectbox("Mes", list(meses_dict.values()), index=datetime.now().month-1)
mes_sel_num = [k for k, v in meses_dict.items() if v == mes_sel_nom][0]

# FILTRO CRÍTICO: Aquí es donde se decide qué mostrar
df_mes = df[(df['Fecha'].dt.month == mes_sel_num) & (df['Fecha'].dt.year == anho_sel)]

# --- FORMULARIO ---
with st.expander("➕ REGISTRAR GASTO DEL HOGAR"):
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

# --- VISUALIZACIÓN ---
st.header(f"🎯 Presupuestos de {mes_sel_nom} {anho_sel}")

if not df_mes.empty:
    # 1. Barras de Presupuesto
    cols_p = st.columns(len(PRESUPUESTOS_FAMILIARES))
    for i, (cat, limite) in enumerate(PRESUPUESTOS_FAMILIARES.items()):
        gastado = df_mes[df_mes['Categoría'] == cat]['Monto'].sum()
        progreso = min(gastado / limite, 1.0) if limite > 0 else 0
        with cols_p[i]:
            st.write(f"**{cat}**")
            st.progress(progreso)
            st.caption(f"${gastado:,.0f} / ${limite:,.0f}")

    # 2. Balance General
    st.divider()
    st.subheader("📊 Balance General")
    t_leo = df_mes[df_mes['Pagador'] == 'Leonardo']['Monto'].sum()
    t_esp = df_mes[df_mes['Pagador'] == 'Esposa']['Monto'].sum()
    mitad = (t_leo + t_esp) / 2
    
    b1, b2, b3 = st.columns(3)
    b1.metric("Leo pagó", f"${t_leo:,.0f}")
    b2.metric("Esposa pagó", f"${t_esp:,.0f}")
    
    if t_leo > mitad:
        b3.info(f"💡 Esposa debe: **${t_leo - mitad:,.0f}**")
    elif t_esp > mitad:
        b3.info(f"💡 Leo debe: **${t_esp - mitad:,.0f}**")
    else:
        b3.success("✅ ¡A mano!")

    st.plotly_chart(px.pie(df_mes, values='Monto', names='Categoría', hole=0.5), use_container_width=True)
else:
    st.info(f"No hay datos registrados para {mes_sel_nom} {anho_sel}. Verifica que la fecha en el Excel sea correcta.")

# --- SECCIÓN DE DEPURACIÓN MEJORADA ---
st.divider()
with st.expander("🛠️ INVESTIGADOR DE DATOS (Haz clic aquí)"):
    st.write("### 1. Todos los datos encontrados en Google Sheets:")
    # Mostramos TODO lo que el robot lee, sin filtros de mes
    st.dataframe(df) 
    
    st.write("### 2. Diagnóstico de la fila perdida:")
    # Revisamos si hay fechas que fallaron (NaT significa Not a Time)
    filas_con_error = df_raw[pd.to_datetime(df_raw['Fecha'], errors='coerce').isna()]
    if not filas_con_error.empty:
        st.warning("⚠️ Se encontraron filas con fechas que la App no entiende:")
        st.write(filas_con_error)
    else:
        st.success("✅ Todas las fechas en el Excel parecen estar correctas.")