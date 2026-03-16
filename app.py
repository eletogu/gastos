import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
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
    "Carro - Ingresos", "Carro - Gastos", "Otro"
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
    return data

df_visualizacion = cargar_datos()

# --- FORMULARIO DE REGISTRO ---
st.title("🏠 Finanzas Hogar & 🚗 Negocio Carro")

col_reg1, col_reg2 = st.columns(2)

with col_reg1:
    with st.expander("➕ REGISTRAR GASTO O INGRESO CARRO", expanded=False):
        with st.form("nuevo_gasto", clear_on_submit=True):
            fecha_g = st.date_input("Fecha", datetime.now())
            cat_g = st.selectbox("Categoría", CATEGORIAS_GASTOS)
            con_g = st.text_input("Concepto")
            mon_g = st.number_input("Monto (COP)", min_value=0.0, step=1000.0)
            pag_g = st.selectbox("¿Quién realizó el movimiento?", ["Leonardo", "Cata"])
            
            km_g, gal_g = 0, 0
            if cat_g == "Carro - Gastos":
                st.caption("⛽ Datos de tanqueo:")
                c_km, c_gl = st.columns(2)
                km_g = c_km.number_input("KM Actual", min_value=0.0, step=1.0)
                gal_g = c_gl.number_input("Galones", min_value=0.0, step=0.1)

            if st.form_submit_button("💾 Guardar Registro"):
                if con_g and mon_g > 0:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    df_db = conn.read(ttl="0") 
                    nueva_f = pd.DataFrame([{"Fecha": fecha_g.strftime("%d/%m/%Y"), "Concepto": con_g, "Monto": mon_g, "Pagador": pag_g, "Categoría": cat_g, "KM": km_g, "Galones": gal_g}])
                    conn.update(data=pd.concat([df_db, nueva_f], ignore_index=True))
                    enviar_notificacion(f"✅ *Nuevo Registro*\n👤 {pag_g}\n📝 {con_g}\n💵 ${mon_g:,.0f} COP")
                    st.rerun()

with col_reg2:
    with st.expander("💸 REGISTRAR ABONO ENTRE NOSOTROS", expanded=False):
        with st.form("nuevo_abono", clear_on_submit=True):
            fecha_a = st.date_input("Fecha Abono", datetime.now())
            emisor = st.selectbox("¿Quién entrega el dinero?", ["Cata", "Leonardo"])
            receptor = "Leonardo" if emisor == "Cata" else "Cata"
            monto_a = st.number_input("Monto del Abono (COP)", min_value=0.0, step=1000.0)
            
            if st.form_submit_button("🤝 Registrar Abono"):
                if monto_a > 0:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    df_db = conn.read(ttl="0")
                    nueva_f = pd.DataFrame([{"Fecha": fecha_a.strftime("%d/%m/%Y"), "Concepto": f"Abono a {receptor}", "Monto": monto_a, "Pagador": emisor, "Categoría": "Abono a Deuda", "KM": 0, "Galones": 0}])
                    conn.update(data=pd.concat([df_db, nueva_f], ignore_index=True))
                    enviar_notificacion(f"🤝 *Abono Registrado*\n👤 {emisor} le entregó ${monto_a:,.0f} a {receptor}")
                    st.rerun()

# --- 🕒 ÚLTIMOS MOVIMIENTOS ---
st.subheader("🕒 Últimos 5 movimientos")
col_t, col_b = st.columns([3, 1])
with col_t:
    u5 = df_visualizacion.tail(5).iloc[::-1]
    if not u5.empty:
        u5_d = u5.copy()
        u5_d['Fecha'] = u5_d['Fecha'].dt.strftime('%d/%m/%Y')
        st.dataframe(u5_d, use_container_width=True, hide_index=True)
with col_b:
    if st.checkbox("Confirmar borrar último") and st.button("🗑️ Eliminar"):
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_actual = conn.read(ttl="0")
        if not df_actual.empty:
            conn.update(data=df_actual.drop(df_actual.index[-1]))
            st.rerun()

st.divider()

# --- FILTROS ---
meses_dict = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
df_v = df_visualizacion.dropna(subset=['Fecha'])
anhos = sorted(df_v['Fecha'].dt.year.unique(), reverse=True)
if datetime.now().year not in anhos: anhos.insert(0, datetime.now().year)
anho_s = st.sidebar.selectbox("Año", anhos)
mes_s_n = st.sidebar.selectbox("Mes", list(meses_dict.values()), index=datetime.now().month-1)
mes_s_num = [k for k, v in meses_dict.items() if v == mes_s_n][0]
df_mes = df_v[(df_v['Fecha'].dt.month == mes_s_num) & (df_v['Fecha'].dt.year == anho_s)]

# --- DASHBOARD CARRO ---
st.header(f"🚗 Balance Carro ({mes_s_n})")
df_carro = df_mes[df_mes['Categoría'].isin(["Carro - Ingresos", "Carro - Gastos"])]
ing = df_carro[df_carro['Categoría'] == "Carro - Ingresos"]['Monto'].sum()
gas = df_carro[df_carro['Categoría'] == "Carro - Gastos"]['Monto'].sum()
c1, c2, c3 = st.columns(3)
c1.metric("Ingresos", f"${ing:,.0f}")
c2.metric("Gastos", f"${gas:,.0f}")
c3.metric("Utilidad", f"${ing-gas:,.0f}")

st.divider()

# --- 👥 CUENTAS CLARAS CON HISTORIAL ---
st.header(f"👥 Cuentas Claras ({mes_s_n})")

df_hogar = df_mes[~df_mes['Categoría'].isin(["Carro - Ingresos", "Carro - Gastos", "Abono a Deuda"])]
t_leo = df_hogar[df_hogar['Pagador'] == 'Leonardo']['Monto'].sum()
t_cata = df_hogar[df_hogar['Pagador'].isin(['Cata', 'Esposa'])]['Monto'].sum()

abonos_cata_a_leo = df_mes[(df_mes['Categoría'] == "Abono a Deuda") & (df_mes['Pagador'] == "Cata")]['Monto'].sum()
abonos_leo_a_cata = df_mes[(df_mes['Categoría'] == "Abono a Deuda") & (df_mes['Pagador'] == "Leonardo")]['Monto'].sum()

diferencia_gastos = (t_leo - t_cata) / 2
ajuste_abonos = abonos_leo_a_cata - abonos_cata_a_leo
deuda_final = diferencia_gastos + ajuste_abonos

b1, b2 = st.columns(2)
b1.metric("Leo pagó (Hogar)", f"${t_leo:,.0f}")
b2.metric("Cata pagó (Hogar)", f"${t_cata:,.0f}")

if deuda_final > 0:
    st.info(f"💡 **Cata debe a Leonardo: ${deuda_final:,.0f} COP**")
elif deuda_final < 0:
    st.info(f"💡 **Leonardo debe a Cata: ${abs(deuda_final):,.0f} COP**")
else:
    st.success("✅ ¡Están totalmente a mano!")

# --- TABLA DE HISTORIAL DE ABONOS ---
with st.expander("📖 Ver historial de abonos de este mes"):
    df_abonos_mes = df_mes[df_mes['Categoría'] == "Abono a Deuda"].copy()
    if not df_abonos_mes.empty:
        df_abonos_mes['Fecha'] = df_abonos_mes['Fecha'].dt.strftime('%d/%m/%Y')
        st.write(f"Total abonado este mes: **${(abonos_cata_a_leo + abonos_leo_a_cata):,.0f} COP**")
        st.dataframe(df_abonos_mes[['Fecha', 'Pagador', 'Concepto', 'Monto']], use_container_width=True, hide_index=True)
    else:
        st.write("No se han registrado abonos en este mes.")

st.divider()

# --- METAS HOGAR ---
st.header(f"🎯 Metas Hogar ({mes_s_n})")
cols_p = st.columns(len(PRESUPUESTOS_FAMILIARES))
for i, (cat, lim) in enumerate(PRESUPUESTOS_FAMILIARES.items()):
    gastado = df_mes[df_mes['Categoría'] == cat]['Monto'].sum()
    with cols_p[i]:
        st.write(f"**{cat}**")
        st.progress(min(gastado/lim, 1.0))
        st.caption(f"${gastado:,.0f} / ${lim:,.0f}")

st.plotly_chart(px.pie(df_mes[df_mes['Categoría'] != "Abono a Deuda"], values='Monto', names='Categoría', hole=0.5, title="Distribución de Gastos"), use_container_width=True)