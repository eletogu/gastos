import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import requests

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Finanzas Leo & Cata", page_icon="🇨🇴", layout="wide")

# Estilos CSS personalizados para mejorar la apariencia del menú lateral
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none;}
        .st-emotion-cache-16ids0d {font-size: 1.1rem; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

# Configuración de Presupuestos y Categorías
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

# --- 2. FUNCIONES DE APOYO ---
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

def calcular_detalle_balance(dataframe):
    cat_hogar = [c for c in CATEGORIAS_GASTOS if c not in ["Carro - Ingresos", "Carro - Gastos", "Préstamo Personal", "Otro"]]
    df_h = dataframe[dataframe['Categoría'].isin(cat_hogar)]
    t_leo_h = df_h[df_h['Pagador'] == 'Leonardo']['Monto'].sum()
    t_cata_h = df_h[df_h['Pagador'].isin(['Cata', 'Esposa'])]['Monto'].sum()
    dh = (t_leo_h - t_cata_h) / 2
    
    p_leo = dataframe[(dataframe['Categoría'] == "Préstamo Personal") & (dataframe['Pagador'] == "Leonardo")]['Monto'].sum()
    p_cata = dataframe[(dataframe['Categoría'] == "Préstamo Personal") & (dataframe['Pagador'] == "Cata")]['Monto'].sum()
    dp = p_leo - p_cata
    
    a_cata = dataframe[(dataframe['Categoría'] == "Abono a Deuda") & (dataframe['Pagador'] == "Cata")]['Monto'].sum()
    a_leo = dataframe[(dataframe['Categoría'] == "Abono a Deuda") & (dataframe['Pagador'] == "Leonardo")]['Monto'].sum()
    aj = a_leo - a_cata
    
    return dh, dp, aj, (t_leo_h, t_cata_h, p_leo, p_cata, a_leo, a_cata)

# Carga de datos global
df_v = cargar_datos()

# --- 3. NAVEGACIÓN LATERAL ---
with st.sidebar:
    st.image("https://img.icons8.com/clouds/200/home-automation.png", width=100)
    st.title("Menú Principal")
    modulo = st.radio(
        "Ir a:",
        ["🏠 Inicio", "➕ Registrar Gasto/Ingreso", "🤝 Registrar Abono", "📊 Reportes Mensuales", "📖 Historial y Edición"]
    )
    st.divider()
    st.info("💡 Consejo: Revisa tus presupuestos en la sección de Reportes.")

# --- 4. LÓGICA DE MÓDULOS ---

if modulo == "🏠 Inicio":
    st.title("🏠 Finanzas Hogar & 🚗 Negocio Carro")
    
    # Cálculos globales para el Inicio
    dh_t, dp_t, aj_t, raw = calcular_detalle_balance(df_v)
    saldo_total = dh_t + dp_t + aj_t
    
    st.subheader("Estado Actual de Cuentas")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.metric("Deuda por Hogar", f"${abs(dh_t):,.0f}")
    with c2:
        st.metric("Deuda por Préstamos", f"${abs(dp_t):,.0f}")
    with c3:
        st.metric("Abonos Realizados", f"${abs(raw[4] + raw[5]):,.0f}")
    
    if saldo_total > 0:
        st.warning(f"💡 **Cata debe a Leonardo: ${saldo_total:,.0f} COP**")
    elif saldo_total < 0:
        st.warning(f"💡 **Leonardo debe a Cata: ${abs(saldo_total):,.0f} COP**")
    else:
        st.success("✅ **¡Están totalmente a mano!**")

elif modulo == "➕ Registrar Gasto/Ingreso":
    st.header("➕ Registrar Nuevo Movimiento")
    cat_g = st.selectbox("Categoría", CATEGORIAS_GASTOS)
    
    with st.form("form_gasto", clear_on_submit=True):
        fecha_g = st.date_input("Fecha", datetime.now())
        con_g = st.text_input("Concepto")
        mon_g = st.number_input("Monto (COP)", min_value=0.0, step=1000.0)
        pag_g = st.selectbox("Pagador", ["Leonardo", "Cata"])
        
        km_g, gal_g = 0, 0
        if cat_g == "Carro - Gastos":
            st.divider()
            st.caption("⛽ Información de combustible")
            ckm, cgl = st.columns(2)
            km_g = ckm.number_input("Kilometraje", min_value=0.0)
            gal_g = cgl.number_input("Galones", min_value=0.0)
            
        if st.form_submit_button("💾 Guardar en la Nube"):
            if con_g and mon_g > 0:
                conn = st.connection("gsheets", type=GSheetsConnection)
                nueva_f = pd.DataFrame([{"Fecha": fecha_g.strftime("%d/%m/%Y"), "Concepto": con_g, "Monto": mon_g, "Pagador": pag_g, "Categoría": cat_g, "KM": km_g, "Galones": gal_g}])
                conn.update(data=pd.concat([conn.read(ttl="0"), nueva_f], ignore_index=True))
                enviar_notificacion(f"✅ *Nuevo Registro*\n👤 {pag_g}\n📝 {con_g}\n💵 ${mon_g:,.0f}")
                st.success("¡Registro guardado con éxito!")
                st.rerun()

elif modulo == "🤝 Registrar Abono":
    st.header("🤝 Registrar Abono entre Pareja")
    with st.form("form_abono", clear_on_submit=True):
        fecha_a = st.date_input("Fecha", datetime.now())
        emisor = st.selectbox("¿Quién entrega el dinero?", ["Cata", "Leonardo"])
        receptor = "Leonardo" if emisor == "Cata" else "Cata"
        monto_a = st.number_input("Monto (COP)", min_value=0.0, step=1000.0)
        
        if st.form_submit_button("🤝 Confirmar Entrega de Dinero"):
            if monto_a > 0:
                conn = st.connection("gsheets", type=GSheetsConnection)
                nueva_f = pd.DataFrame([{"Fecha": fecha_a.strftime("%d/%m/%Y"), "Concepto": f"Abono a {receptor}", "Monto": monto_a, "Pagador": emisor, "Categoría": "Abono a Deuda", "KM": 0, "Galones": 0}])
                conn.update(data=pd.concat([conn.read(ttl="0"), nueva_f], ignore_index=True))
                enviar_notificacion(f"🤝 *Abono Registrado*\n👤 {emisor} ➡️ {receptor}\n💵 ${monto_a:,.0f}")
                st.success(f"Abono de {emisor} registrado correctamente.")
                st.rerun()

elif modulo == "📊 Reportes Mensuales":
    st.header("📊 Análisis del Mes")
    
    # Filtros de mes/año
    meses_dict = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
    df_cl = df_v.dropna(subset=['Fecha'])
    anho_s = st.selectbox("Año", sorted(df_cl['Fecha'].dt.year.unique(), reverse=True))
    mes_s_n = st.selectbox("Mes", list(meses_dict.values()), index=datetime.now().month-1)
    mes_s_num = [k for k, v in meses_dict.items() if v == mes_s_n][0]
    
    df_mes = df_cl[(df_cl['Fecha'].dt.month == mes_s_num) & (df_cl['Fecha'].dt.year == anho_s)]
    
    t1, t2 = st.tabs(["🚗 Negocio Carro", "🎯 Presupuestos Hogar"])
    
    with t1:
        df_car = df_mes[df_mes['Categoría'].isin(["Carro - Ingresos", "Carro - Gastos"])]
        ing = df_car[df_car['Categoría'] == "Carro - Ingresos"]['Monto'].sum()
        gas = df_car[df_car['Categoría'] == "Carro - Gastos"]['Monto'].sum()
        st.metric("Utilidad del Negocio", f"${ing-gas:,.0f}")
        st.write(f"Ingresos: ${ing:,.0f} | Gastos: ${gas:,.0f}")

    with t2:
        for cat, lim in PRESUPUESTOS_FAMILIARES.items():
            gast = df_mes[df_mes['Categoría'] == cat]['Monto'].sum()
            st.write(f"**{cat}**")
            st.progress(min(gast/lim, 1.0))
            st.caption(f"${gast:,.0f} de ${lim:,.0f}")

elif modulo == "📖 Historial y Edición":
    st.header("📖 Historial de Movimientos")
    
    st.subheader("Últimos 5 registros")
    u5 = df_v.tail(5).iloc[::-1].copy()
    u5['Fecha'] = u5['Fecha'].dt.strftime('%d/%m/%Y')
    st.dataframe(u5, use_container_width=True, hide_index=True)
    
    st.divider()
    st.subheader("Eliminar Registro")
    st.warning("⚠️ Esta acción borrará el último registro del archivo de Google Sheets.")
    if st.checkbox("Confirmar que deseo eliminar el último registro"):
        if st.button("🗑️ Eliminar Definitivamente"):
            conn = st.connection("gsheets", type=GSheetsConnection)
            df_actual = conn.read(ttl="0")
            if not df_actual.empty:
                conn.update(data=df_actual.drop(df_actual.index[-1]))
                enviar_notificacion("❌ *Gasto Eliminado*")
                st.rerun()

    with st.expander("📂 Ver todo el historial"):
        st.dataframe(df_v, use_container_width=True)
