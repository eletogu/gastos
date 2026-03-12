import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
import requests

st.set_page_config(page_title="Finanzas Leo & Cata", page_icon="🚗", layout="wide")

# --- CONFIGURACIÓN ---
PRESUPUESTOS_FAMILIARES = {
    "Almuerzos de trabajo": 520000,
    "Almuerzos fines de semana": 1200000,
    "Mercado": 600000
}

TODAS_CATEGORIAS = [
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
    # Aseguramos que KM y Galones sean números
    data['KM'] = pd.to_numeric(data['KM'], errors='coerce').fillna(0)
    data['Galones'] = pd.to_numeric(data['Galones'], errors='coerce').fillna(0)
    return data

df_visualizacion = cargar_datos()

# --- FORMULARIO DE REGISTRO ---
st.title("🏠 Finanzas Hogar & 🚗 Negocio Carro")

with st.expander("➕ REGISTRAR MOVIMIENTO", expanded=False):
    with st.form("nuevo_gasto", clear_on_submit=True):
        c1, c2 = st.columns(2)
        fecha_g = c1.date_input("Fecha", datetime.now())
        cat_g = c2.selectbox("Categoría", TODAS_CATEGORIAS)
        con_g = st.text_input("Concepto (Ej: Carrera Uber, Gasolina)")
        mon_g = st.number_input("Monto (COP)", min_value=0.0, step=1000.0)
        pag_g = st.selectbox("¿Quién realizó el movimiento?", ["Leonardo", "Cata"])
        
        # --- CAMPOS EXTRA PARA GASOLINA ---
        km_g = 0.0
        gal_g = 0.0
        if cat_g == "Carro - Gastos":
            st.info("⛽ Si es tanqueo, llena estos datos para medir eficiencia:")
            col_km, col_gal = st.columns(2)
            km_g = col_km.number_input("Kilometraje Actual", min_value=0.0, step=1.0)
            gal_g = col_gal.number_input("Galones", min_value=0.0, step=0.1)

        if st.form_submit_button("💾 Guardar"):
            if con_g and mon_g > 0:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_db = conn.read(ttl="0") 
                nueva_fila = pd.DataFrame([{
                    "Fecha": fecha_g.strftime("%d/%m/%Y"), 
                    "Concepto": con_g,
                    "Monto": mon_g,
                    "Pagador": pag_g,
                    "Categoría": cat_g,
                    "KM": km_g,
                    "Galones": gal_g
                }])
                df_final = pd.concat([df_db, nueva_fila], ignore_index=True)
                conn.update(data=df_final)
                
                aviso = f"✅ *Registro Exitoso*\n👤 {pag_g}\n📝 {con_g}\n💵 ${mon_g:,.0f} COP"
                enviar_notificacion(aviso)
                st.success("¡Guardado!")
                st.rerun()

# --- 🕒 ÚLTIMOS MOVIMIENTOS Y ELIMINACIÓN ---
st.subheader("🕒 Últimos 5 movimientos")
col_t, col_b = st.columns([3, 1])
with col_t:
    ultimos_5 = df_visualizacion.tail(5).iloc[::-1]
    if not ultimos_5.empty:
        u5_disp = ultimos_5.copy()
        u5_disp['Fecha'] = u5_disp['Fecha'].dt.strftime('%d/%m/%Y')
        st.dataframe(u5_disp, use_container_width=True, hide_index=True)

with col_b:
    confirmar = st.checkbox("Confirmar borrar último")
    if confirmar and st.button("🗑️ Eliminar último"):
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_actual = conn.read(ttl="0")
        if not df_actual.empty:
            df_nuevo = df_actual.drop(df_actual.index[-1])
            conn.update(data=df_nuevo)
            st.rerun()

st.divider()

# --- FILTROS ---
st.sidebar.header("🔍 Histórico")
meses_dict = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
df_v = df_visualizacion.dropna(subset=['Fecha'])
anhos = sorted(df_v['Fecha'].dt.year.unique(), reverse=True)
if datetime.now().year not in anhos: anhos.insert(0, datetime.now().year)

anho_s = st.sidebar.selectbox("Año", anhos)
mes_s_n = st.sidebar.selectbox("Mes", list(meses_dict.values()), index=datetime.now().month-1)
mes_s_num = [k for k, v in meses_dict.items() if v == mes_s_n][0]

df_mes = df_v[(df_v['Fecha'].dt.month == mes_s_num) & (df_v['Fecha'].dt.year == anho_s)]

# --- 🚗 MÓDULO CARRO (CON EFICIENCIA) ---
st.header(f"🚗 Balance Negocio Carro ({mes_s_n})")
df_carro = df_mes[df_mes['Categoría'].isin(["Carro - Ingresos", "Carro - Gastos"])]

ingresos_c = df_carro[df_carro['Categoría'] == "Carro - Ingresos"]['Monto'].sum()
gastos_c = df_carro[df_carro['Categoría'] == "Carro - Gastos"]['Monto'].sum()
utilidad = ingresos_c - gastos_c

# Lógica de Eficiencia (KM/G)
df_gas = df_carro[(df_carro['KM'] > 0) & (df_carro['Galones'] > 0)].sort_values('Fecha')
eficiencia_promedio = 0
if len(df_gas) >= 2:
    distancia = df_gas['KM'].iloc[-1] - df_gas['KM'].iloc[0]
    total_gal = df_gas['Galones'].iloc[1:].sum()
    if total_gal > 0:
        eficiencia_promedio = distancia / total_gal

c1, c2, c3, c4 = st.columns(4)
c1.metric("Ingresos", f"${ingresos_c:,.0f}")
c2.metric("Gastos", f"${gastos_c:,.0f}")
c3.metric("Utilidad", f"${utilidad:,.0f}")
c4.metric("Eficiencia", f"{eficiencia_promedio:.1f} km/gal" if eficiencia_promedio > 0 else "---")

# --- 🎯 METAS DEL HOGAR ---
st.divider()
st.header(f"🎯 Metas del Hogar ({mes_s_n})")
cols_p = st.columns(len(PRESUPUESTOS_FAMILIARES))
for i, (cat, limite) in enumerate(PRESUPUESTOS_FAMILIARES.items()):
    gastado = df_mes[df_mes['Categoría'] == cat]['Monto'].sum()
    prog = min(gastado / limite, 1.0) if limite > 0 else 0
    with cols_p[i]:
        st.write(f"**{cat}**")
        st.progress(prog)
        st.caption(f"${gastado:,.0f} / ${limite:,.0f} COP")

# --- 📊 BALANCE DE DEUDAS ---
st.subheader("👥 Cuentas Claras (Leo & Cata)")
df_hogar = df_mes[~df_mes['Categoría'].isin(["Carro - Ingresos", "Carro - Gastos"])]
t_leo = df_hogar[df_hogar['Pagador'] == 'Leonardo']['Monto'].sum()
t_cata = df_hogar[df_hogar['Pagador'].isin(['Cata', 'Esposa'])]['Monto'].sum()
mitad = (t_leo + t_cata) / 2

b1, b2, b3 = st.columns(3)
b1.metric("Leonardo pagó", f"${t_leo:,.0f}")
b2.metric("Cata pagó", f"${t_cata:,.0f}")

if t_leo > mitad:
    b3.info(f"💡 Cata debe a Leo: **${t_leo - mitad:,.0f} COP**")
elif t_cata > mitad:
    b3.info(f"💡 Leo debe a Cata: **${t_cata - mitad:,.0f} COP**")
else:
    b3.success("✅ ¡A mano!")