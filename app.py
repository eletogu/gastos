import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import requests

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Finanzas Leo & Cata", page_icon="🇨🇴", layout="wide")

PRESUPUESTOS_FAMILIARES = {
    "Almuerzos de trabajo": 520000,
    "Almuerzos fines de semana": 1200000,
    "Mercado": 600000
}

CATEGORIAS_GASTOS = [
    "Almuerzos de trabajo", "Almuerzos fines de semana", "Mercado", 
    "Transporte", "Servicios", "Ocio", "Salud", 
    "Carro - Ingresos", "Carro - Gastos", 
    "Préstamo Personal", "Otro"
]

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
    data['KM'] = pd.to_numeric(data['KM'], errors='coerce').fillna(0)
    data['Galones'] = pd.to_numeric(data['Galones'], errors='coerce').fillna(0)
    data['Monto'] = pd.to_numeric(data['Monto'], errors='coerce').fillna(0)
    return data

df_v = cargar_datos()

# --- FORMULARIOS ---
st.title("🏠 Finanzas Hogar & 🚗 Negocio Carro")

col_reg1, col_reg2 = st.columns(2)
with col_reg1:
    with st.expander("➕ REGISTRAR GASTO, INGRESO O PRÉSTAMO"):
        with st.form("nuevo_gasto", clear_on_submit=True):
            fecha_g = st.date_input("Fecha", datetime.now())
            cat_g = st.selectbox("Categoría", CATEGORIAS_GASTOS)
            con_g = st.text_input("Concepto")
            mon_g = st.number_input("Monto (COP)", min_value=0.0, step=1000.0)
            pag_g = st.selectbox("¿Quién realizó el movimiento?", ["Leonardo", "Cata"])
            km_g, gal_g = 0, 0
            if cat_g == "Carro - Gastos":
                c_km, c_gl = st.columns(2)
                km_g = c_km.number_input("KM Actual", min_value=0.0, step=1.0)
                gal_g = c_gl.number_input("Galones", min_value=0.0, step=0.1)
            if st.form_submit_button("💾 Guardar Registro"):
                conn = st.connection("gsheets", type=GSheetsConnection)
                nueva_f = pd.DataFrame([{"Fecha": fecha_g.strftime("%d/%m/%Y"), "Concepto": con_g, "Monto": mon_g, "Pagador": pag_g, "Categoría": cat_g, "KM": km_g, "Galones": gal_g}])
                conn.update(data=pd.concat([conn.read(ttl="0"), nueva_f], ignore_index=True))
                enviar_notificacion(f"✅ *Registro:* {con_g}\n👤 {pag_g}\n💵 ${mon_g:,.0f}")
                st.rerun()

with col_reg2:
    with st.expander("🤝 REGISTRAR ABONO"):
        with st.form("nuevo_abono", clear_on_submit=True):
            fecha_a = st.date_input("Fecha Abono", datetime.now())
            emisor = st.selectbox("¿Quién entrega?", ["Cata", "Leonardo"])
            monto_a = st.number_input("Monto (COP)", min_value=0.0, step=1000.0)
            if st.form_submit_button("🤝 Confirmar Abono"):
                conn = st.connection("gsheets", type=GSheetsConnection)
                nueva_f = pd.DataFrame([{"Fecha": fecha_a.strftime("%d/%m/%Y"), "Concepto": f"Abono a {'Leonardo' if emisor == 'Cata' else 'Cata'}", "Monto": monto_a, "Pagador": emisor, "Categoría": "Abono a Deuda", "KM": 0, "Galones": 0}])
                conn.update(data=pd.concat([conn.read(ttl="0"), nueva_f], ignore_index=True))
                enviar_notificacion(f"🤝 *Abono:* {emisor}\n💵 ${monto_a:,.0f}")
                st.rerun()

st.divider()

# --- FILTROS ---
meses_dict = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
df_clean = df_v.dropna(subset=['Fecha'])
anhos = sorted(df_clean['Fecha'].dt.year.unique(), reverse=True)
if datetime.now().year not in anhos: anhos.insert(0, datetime.now().year)
anho_s = st.sidebar.selectbox("Año", anhos)
mes_s_n = st.sidebar.selectbox("Mes", list(meses_dict.values()), index=datetime.now().month-1)
mes_s_num = [k for k, v in meses_dict.items() if v == mes_s_n][0]

# --- LÓGICA DE CÁLCULO DE DEUDAS ---
def calcular_balance(dataframe):
    cat_hogar = [c for c in CATEGORIAS_GASTOS if c not in ["Carro - Ingresos", "Carro - Gastos", "Préstamo Personal", "Otro"]]
    # Gastos Hogar (50/50)
    df_h = dataframe[dataframe['Categoría'].isin(cat_hogar)]
    t_leo_h = df_h[df_h['Pagador'] == 'Leonardo']['Monto'].sum()
    t_cata_h = df_h[df_h['Pagador'].isin(['Cata', 'Esposa'])]['Monto'].sum()
    # Préstamos (100%)
    p_leo = dataframe[(dataframe['Categoría'] == "Préstamo Personal") & (dataframe['Pagador'] == "Leonardo")]['Monto'].sum()
    p_cata = dataframe[(dataframe['Categoría'] == "Préstamo Personal") & (dataframe['Pagador'] == "Cata")]['Monto'].sum()
    # Abonos
    a_cata = dataframe[(dataframe['Categoría'] == "Abono a Deuda") & (dataframe['Pagador'] == "Cata")]['Monto'].sum()
    a_leo = dataframe[(dataframe['Categoría'] == "Abono a Deuda") & (dataframe['Pagador'] == "Leonardo")]['Monto'].sum()
    
    return ((t_leo_h - t_cata_h) / 2) + (p_leo - p_cata) + (a_leo - a_cata)

# 1. Saldo Anterior (Todo antes del mes actual seleccionado)
fecha_inicio_mes = datetime(anho_s, mes_s_num, 1)
df_anterior = df_clean[df_clean['Fecha'] < fecha_inicio_mes]
saldo_anterior = calcular_balance(df_anterior)

# 2. Saldo Total (Toda la historia)
saldo_total = calcular_balance(df_clean)

# --- 👥 SECCIÓN DE DEUDAS ---
st.header(f"👥 Cuentas Claras")
c_m1, c_m2, c_m3 = st.columns(3)

# Tarjeta Saldo Anterior
label_ant = "Leonardo cobra" if saldo_anterior > 0 else "Cata cobra"
c_m1.metric(f"Viene del mes anterior", f"${abs(saldo_anterior):,.0f}", help="Suma de deudas y abonos antes de este mes")

# Tarjeta Saldo Total Actual
c_m2.metric("SALDO TOTAL HOY", f"${abs(saldo_total):,.0f}", delta=f"{saldo_total - saldo_anterior:,.0f} este mes", delta_color="inverse")

with st.container():
    if saldo_total > 0:
        st.info(f"💡 **Cata debe a Leonardo: ${saldo_total:,.0f} COP**")
    elif saldo_total < 0:
        st.info(f"💡 **Leonardo debe a Cata: ${abs(saldo_total):,.0f} COP**")
    else:
        st.success("✅ **¡Están totalmente a mano!**")

st.divider()

# --- 🚗 SECCIÓN CARRO & METAS (MENSUAL) ---
df_mes = df_clean[(df_clean['Fecha'].dt.month == mes_s_num) & (df_clean['Fecha'].dt.year == anho_s)]
st.header(f"📊 Reporte Mensual: {mes_s_n} {anho_s}")

col_c1, col_c2 = st.columns([1, 2])
with col_c1:
    st.subheader("🚗 Carro")
    df_c_mes = df_mes[df_mes['Categoría'].isin(["Carro - Ingresos", "Carro - Gastos"])]
    ing = df_c_mes[df_c_mes['Categoría'] == "Carro - Ingresos"]['Monto'].sum()
    gas = df_c_mes[df_c_mes['Categoría'] == "Carro - Gastos"]['Monto'].sum()
    st.metric("Utilidad Carro", f"${ing-gas:,.0f}")
    st.caption(f"Ingresos: ${ing:,.0f} | Gastos: ${gas:,.0f}")

with col_c2:
    st.subheader("🎯 Presupuestos")
    cp = st.columns(len(PRESUPUESTOS_FAMILIARES))
    for i, (cat, lim) in enumerate(PRESUPUESTOS_FAMILIARES.items()):
        gastado = df_mes[df_mes['Categoría'] == cat]['Monto'].sum()
        cp[i].write(f"**{cat}**")
        cp[i].progress(min(gastado/lim, 1.0))
        cp[i].caption(f"${gastado:,.0f} / ${lim:,.0f}")

st.plotly_chart(px.pie(df_mes[~df_mes['Categoría'].isin(["Abono a Deuda", "Préstamo Personal", "Carro - Ingresos", "Carro - Gastos"])], 
                       values='Monto', names='Categoría', hole=0.5), use_container_width=True)