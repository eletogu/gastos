import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
import requests

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Finanzas Leo & Cata", page_icon="🇨🇴", layout="wide")

# Presupuestos mensuales (Metas)
PRESUPUESTOS_FAMILIARES = {
    "Almuerzos de trabajo": 520000,
    "Almuerzos fines de semana": 1200000,
    "Mercado": 600000
}

# Categorías oficiales
CATEGORIAS_GASTOS = [
    "Almuerzos de trabajo", "Almuerzos fines de semana", "Mercado", 
    "Transporte", "Servicios", "Ocio", "Salud", 
    "Carro - Ingresos", "Carro - Gastos", 
    "Préstamo Personal", "Otro"
]

# --- 2. FUNCIONES DE APOYO ---
def enviar_notificacion(mensaje):
    """Envía alertas a Telegram"""
    try:
        token = st.secrets["telegram_token"]
        chat_id = st.secrets["telegram_chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": mensaje, "parse_mode": "Markdown"})
    except:
        pass

def cargar_datos():
    """Conecta con Google Sheets y limpia los datos"""
    conn = st.connection("gsheets", type=GSheetsConnection)
    data = conn.read(ttl="0")
    data.columns = data.columns.str.strip()
    data = data.dropna(how='all')
    data['Fecha'] = pd.to_datetime(data['Fecha'], dayfirst=True, errors='coerce')
    data['KM'] = pd.to_numeric(data['KM'], errors='coerce').fillna(0)
    data['Galones'] = pd.to_numeric(data['Galones'], errors='coerce').fillna(0)
    data['Monto'] = pd.to_numeric(data['Monto'], errors='coerce').fillna(0)
    return data

# Carga inicial de datos
df_v = cargar_datos()

# --- 3. FORMULARIOS DE REGISTRO ---
st.title("🏠 Finanzas Hogar & 🚗 Negocio Carro")

col_reg1, col_reg2 = st.columns(2)

with col_reg1:
    with st.expander("➕ REGISTRAR MOVIMIENTO (Gasto/Ingreso/Préstamo)", expanded=False):
        # DINÁMICO: La categoría va fuera del form para que los campos de gas aparezcan solos
        cat_g = st.selectbox("Selecciona la Categoría", CATEGORIAS_GASTOS)
        
        with st.form("nuevo_gasto", clear_on_submit=True):
            fecha_g = st.date_input("Fecha", datetime.now())
            con_g = st.text_input("Concepto (Ej: Tanqueo full, Mercado Éxito)")
            mon_g = st.number_input("Monto (COP)", min_value=0.0, step=1000.0)
            pag_g = st.selectbox("¿Quién realizó el movimiento?", ["Leonardo", "Cata"])
            
            # Variables de gasolina ocultas por defecto
            km_g, gal_g = 0, 0
            
            # Si se selecciona carro, mostramos los campos extra
            if cat_g == "Carro - Gastos":
                st.info("⛽ Datos de combustible detectados:")
                c_km, c_gl = st.columns(2)
                km_g = c_km.number_input("Kilometraje Actual", min_value=0.0, step=1.0)
                gal_g = c_gl.number_input("Cantidad de Galones", min_value=0.0, step=0.1)

            if st.form_submit_button("💾 Guardar Registro"):
                if con_g and mon_g > 0:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    nueva_f = pd.DataFrame([{"Fecha": fecha_g.strftime("%d/%m/%Y"), "Concepto": con_g, "Monto": mon_g, "Pagador": pag_g, "Categoría": cat_g, "KM": km_g, "Galones": gal_g}])
                    conn.update(data=pd.concat([conn.read(ttl="0"), nueva_f], ignore_index=True))
                    enviar_notificacion(f"✅ *Nuevo Registro*\n👤 {pag_g}\n📝 {con_g}\n💵 ${mon_g:,.0f} COP")
                    st.rerun()

with col_reg2:
    with st.expander("🤝 REGISTRAR ABONO (Pagar deudas)", expanded=False):
        with st.form("nuevo_abono", clear_on_submit=True):
            fecha_a = st.date_input("Fecha Abono", datetime.now())
            emisor = st.selectbox("¿Quién entrega el dinero?", ["Cata", "Leonardo"])
            receptor = "Leonardo" if emisor == "Cata" else "Cata"
            monto_a = st.number_input("Monto del Abono (COP)", min_value=0.0, step=1000.0)
            
            if st.form_submit_button("🤝 Confirmar Abono"):
                if monto_a > 0:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    nueva_f = pd.DataFrame([{"Fecha": fecha_a.strftime("%d/%m/%Y"), "Concepto": f"Abono a {receptor}", "Monto": monto_a, "Pagador": emisor, "Categoría": "Abono a Deuda", "KM": 0, "Galones": 0}])
                    conn.update(data=pd.concat([conn.read(ttl="0"), nueva_f], ignore_index=True))
                    enviar_notificacion(f"🤝 *Abono Registrado*\n👤 {emisor} ➡️ {receptor}\n💵 ${monto_a:,.0f} COP")
                    st.rerun()

st.divider()

# --- 4. FILTROS DE TIEMPO (Solo para reportes mensuales) ---
meses_dict = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
df_clean = df_v.dropna(subset=['Fecha'])
anhos = sorted(df_clean['Fecha'].dt.year.unique(), reverse=True)
if datetime.now().year not in anhos: anhos.insert(0, datetime.now().year)
anho_s = st.sidebar.selectbox("Año de reporte", anhos)
mes_s_n = st.sidebar.selectbox("Mes de reporte", list(meses_dict.values()), index=datetime.now().month-1)
mes_s_num = [k for k, v in meses_dict.items() if v == mes_s_n][0]

# --- 5. LÓGICA DE BALANCE ACUMULADO ---
def calcular_detalle_balance(dataframe):
    cat_hogar = [c for c in CATEGORIAS_GASTOS if c not in ["Carro - Ingresos", "Carro - Gastos", "Préstamo Personal", "Otro"]]
    # Hogar (50/50)
    df_h = dataframe[dataframe['Categoría'].isin(cat_hogar)]
    t_leo_h = df_h[df_h['Pagador'] == 'Leonardo']['Monto'].sum()
    t_cata_h = df_h[df_h['Pagador'].isin(['Cata', 'Esposa'])]['Monto'].sum()
    # Préstamos (100%)
    p_leo = dataframe[(dataframe['Categoría'] == "Préstamo Personal") & (dataframe['Pagador'] == "Leonardo")]['Monto'].sum()
    p_cata = dataframe[(dataframe['Categoría'] == "Préstamo Personal") & (dataframe['Pagador'] == "Cata")]['Monto'].sum()
    # Abonos
    a_cata = dataframe[(dataframe['Categoría'] == "Abono a Deuda") & (dataframe['Pagador'] == "Cata")]['Monto'].sum()
    a_leo = dataframe[(dataframe['Categoría'] == "Abono a Deuda") & (dataframe['Pagador'] == "Leonardo")]['Monto'].sum()
    
    dh = (t_leo_h - t_cata_h) / 2
    dp = p_leo - p_cata
    aj = a_leo - a_cata
    return dh, dp, aj, (t_leo_h, t_cata_h, p_leo, p_cata, a_leo, a_cata)

# Cálculo de Saldo Anterior y Total
fecha_corte = datetime(anho_s, mes_s_num, 1)
df_ant = df_clean[df_clean['Fecha'] < fecha_corte]
dh_a, dp_a, aj_a, _ = calcular_detalle_balance(df_ant)
saldo_anterior = dh_a + dp_a + aj_a

dh_t, dp_t, aj_t, raw = calcular_detalle_balance(df_clean)
saldo_total = dh_t + dp_t + aj_t

# --- 6. SECCIÓN DE CUENTAS CLARAS ---
st.header("👥 Cuentas Claras")
c1, c2 = st.columns(2)
c1.metric("Viene del pasado", f"${abs(saldo_anterior):,.0f}", help="Deuda acumulada antes del mes seleccionado")
c2.metric("SALDO TOTAL HOY", f"${abs(saldo_total):,.0f}", delta=f"{saldo_total - saldo_anterior:,.0f} este mes", delta_color="inverse")

if saldo_total > 0:
    st.info(f"💡 **Cata debe a Leonardo: ${saldo_total:,.0f} COP**")
elif saldo_total < 0:
    st.info(f"💡 **Leonardo debe a Cata: ${abs(saldo_total):,.0f} COP**")
else:
    st.success("✅ **¡Están totalmente a mano!**")

with st.expander("🔍 VER DETALLE DE LA DEUDA (Historial completo)"):
    d1, d2, d3 = st.columns(3)
    d1.write(f"🏠 **Hogar (50%):**\n${abs(dh_t):,.0f}")
    d2.write(f"💸 **Préstamos (100%):**\n${abs(dp_t):,.0f}")
    d3.write(f"🤝 **Abonos hechos:**\n${abs(raw[4] + raw[5]):,.0f}")
    
    st.caption("Últimos movimientos de Préstamos y Abonos:")
    df_h_tabs = df_clean[df_clean['Categoría'].isin(["Préstamo Personal", "Abono a Deuda"])].tail(10).iloc[::-1]
    if not df_h_tabs.empty:
        df_h_tabs['Fecha'] = df_h_tabs['Fecha'].dt.strftime('%d/%m/%Y')
        st.dataframe(df_h_tabs[['Fecha', 'Pagador', 'Categoría', 'Concepto', 'Monto']], use_container_width=True, hide_index=True)

st.divider()

# --- 7. REPORTE MENSUAL (CARRO Y METAS) ---
df_mes = df_clean[(df_clean['Fecha'].dt.month == mes_s_num) & (df_clean['Fecha'].dt.year == anho_s)]
st.header(f"📊 Reporte de {mes_s_n} {anho_s}")

col_car, col_met = st.columns([1, 2])

with col_car:
    st.subheader("🚗 Negocio Carro")
    df_c_m = df_mes[df_mes['Categoría'].isin(["Carro - Ingresos", "Carro - Gastos"])]
    ing = df_c_m[df_c_m['Categoría'] == "Carro - Ingresos"]['Monto'].sum()
    gas = df_c_m[df_c_m['Categoría'] == "Carro - Gastos"]['Monto'].sum()
    st.metric("Utilidad del Mes", f"${ing-gas:,.0f}")
    st.caption(f"Ingresos: ${ing:,.0f} | Gastos: ${gas:,.0f}")

with col_met:
    st.subheader("🎯 Presupuestos Hogar")
    cp = st.columns(len(PRESUPUESTOS_FAMILIARES))
    for i, (cat, lim) in enumerate(PRESUPUESTOS_FAMILIARES.items()):
        gast = df_mes[df_mes['Categoría'] == cat]['Monto'].sum()
        with cp[i]:
            st.write(f"**{cat}**")
            st.progress(min(gast/lim, 1.0))
            st.caption(f"${gast:,.0f} / ${lim:,.0f}")

st.plotly_chart(px.pie(df_mes[~df_mes['Categoría'].isin(["Abono a Deuda", "Préstamo Personal", "Carro - Ingresos", "Carro - Gastos"])], 
                       values='Monto', names='Categoría', hole=0.5, title="Distribución de Gastos Reales"), use_container_width=True)