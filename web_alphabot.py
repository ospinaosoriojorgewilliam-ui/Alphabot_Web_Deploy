import streamlit as st
import MetaTrader5 as mt5
import pandas as pd
import time
import requests
import json # Para el mando central
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
TOKEN_WEB = "8298927277:AAHMIU34BSf-IJfdP2K1gR6E2ye64IbjgEk"
CHAT_ID_WEB = "7934798710"

# ✅ CAMBIO ÚNICO: Sincronización de Magic Numbers con los Bots
MAGIC_ORO = 999
MAGIC_EURUSD = 888

MAGIC_NUMBERS = [MAGIC_ORO, MAGIC_EURUSD]
ARCHIVO_MANDO = "mando_central.json"

# --- NUEVA FUNCIÓN: RADAR DE NOTICIAS POR ACTIVO ---
def gestionar_noticias():
    ahora = datetime.now()
    # Noticias configuradas
    noticias = [
        {"hora": "10:00", "moneda": "USD", "evento": "IPC USD"},
        {"hora": "14:30", "moneda": "USD", "evento": "NFP USD"},
        {"hora": "09:00", "moneda": "EUR", "evento": "IPC EURO"}
    ]
    
    bloqueo_usd = False
    bloqueo_eur = False
    evento_proximo = ""

    for n in noticias:
        h_noticia = datetime.strptime(n['hora'], "%H:%M").replace(
            year=ahora.year, month=ahora.month, day=ahora.day
        )
        # Regla: 30 min antes y 60 min después
        if (h_noticia - timedelta(minutes=30)) <= ahora <= (h_noticia + timedelta(minutes=60)):
            if n['moneda'] == "USD": bloqueo_usd = True
            if n['moneda'] == "EUR": bloqueo_eur = True
            evento_proximo = n['evento']
    
    # Escribir órdenes para los bots
    orden = {
        "ORO": "PAUSA" if bloqueo_usd else "OPERANDO",
        "EURUSD": "PAUSA" if (bloqueo_usd or bloqueo_eur) else "OPERANDO",
        "evento": evento_proximo
    }
    with open(ARCHIVO_MANDO, "w") as f:
        json.dump(orden, f)
    
    return orden

def enviar_alerta_web(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN_WEB}/sendMessage"
    payload = {"chat_id": CHAT_ID_WEB, "text": mensaje}
    try: requests.post(url, data=payload)
    except: pass

def asegurar_sl_por_dinero(posiciones, monto_total_protegido):
    profit_actual = sum(p.profit for p in posiciones)
    if profit_actual <= 0: return
    for p in posiciones:
        ratio = p.profit / profit_actual
        dinero_posicion = monto_total_protegido * ratio
        simbolo = mt5.symbol_info(p.symbol)
        tick_val = simbolo.trade_tick_value
        if p.type == mt5.ORDER_TYPE_BUY:
            nuevo_sl = p.price_open + (dinero_posicion / (p.volume * (1.0/simbolo.point) * tick_val))
        else:
            nuevo_sl = p.price_open - (dinero_posicion / (p.volume * (1.0/simbolo.point) * tick_val))
        request = {"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket, "sl": round(nuevo_sl, simbolo.digits), "tp": p.tp}
        mt5.order_send(request)

st.set_page_config(page_title="Alphabot System | Auditoría & Blindaje", layout="wide")

# --- SEPARACIÓN DE BLINDAJES EN SESIÓN ---
if 'blindaje_oro' not in st.session_state: st.session_state['blindaje_oro'] = 0
if 'blindaje_eurusd' not in st.session_state: st.session_state['blindaje_eurusd'] = 0

st.sidebar.title("🛡️ Alphabot Control")
if st.sidebar.button('🚨 BOTÓN DE PÁNICO: CERRAR TODO', use_container_width=True):
    posiciones = mt5.positions_get()
    if posiciones:
        for p in posiciones: mt5.Close(p.symbol, ticket=p.ticket)
        enviar_alerta_web("⚠️ CIERRE MASIVO EJECUTADO")

def obtener_datos():
    if not mt5.initialize(): return None, None, None
    acc = mt5.account_info()
    pos = [p for p in (mt5.positions_get() or []) if p.magic in MAGIC_NUMBERS]
    desde = datetime.now().replace(hour=0, minute=0, second=0)
    hist = mt5.history_deals_get(desde, datetime.now() + timedelta(hours=1))
    return acc, pos, hist

placeholder = st.empty()

while True:
    with placeholder.container():
        acc, pos, hist = obtener_datos()
        if acc:
            # --- EJECUCIÓN DEL MANDO DE NOTICIAS ---
            status_noticias = gestionar_noticias()
            if status_noticias['evento']:
                st.error(f"### 📡 NOTICIA ACTIVA: {status_noticias['evento']} (Bots en Pausa)")
            else:
                st.success("### 📡 Mercado Limpio de Noticias")

            # 2. MÉTRICAS
            pos_oro = [p for p in pos if p.magic == MAGIC_ORO]
            pos_eur = [p for p in pos if p.magic == MAGIC_EURUSD]
            profit_oro = sum(p.profit for p in pos_oro)
            profit_eur = sum(p.profit for p in pos_eur)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Balance Total", f"${acc.balance:,.2f}")
            c2.metric("Profit ORO", f"${profit_oro:.2f}", delta=f"Escudo: {st.session_state['blindaje_oro']}")
            c3.metric("Profit EURUSD", f"${profit_eur:.2f}", delta=f"Escudo: {st.session_state['blindaje_eurusd']}")
            c4.metric("Equidad", f"${acc.equity:,.2f}")

            # --- LÓGICA DE ESCUDO POR ACTIVO ---
            # Lógica ORO
            if st.session_state['blindaje_oro'] == 0 and profit_oro >= 500:
                st.session_state['blindaje_oro'] = 400
                asegurar_sl_por_dinero(pos_oro, 400)
                enviar_alerta_web(f"🛡️ ORO: $400 asegurados.")
            elif st.session_state['blindaje_oro'] >= 400 and profit_oro >= (st.session_state['blindaje_oro'] + 500):
                st.session_state['blindaje_oro'] += 400
                asegurar_sl_por_dinero(pos_oro, st.session_state['blindaje_oro'])
            
            # Lógica EURUSD
            if st.session_state['blindaje_eurusd'] == 0 and profit_eur >= 500:
                st.session_state['blindaje_eurusd'] = 400
                asegurar_sl_por_dinero(pos_eur, 400)
                enviar_alerta_web(f"🛡️ EURUSD: $400 asegurados.")
            elif st.session_state['blindaje_eurusd'] >= 400 and profit_eur >= (st.session_state['blindaje_eurusd'] + 500):
                st.session_state['blindaje_eurusd'] += 400
                asegurar_sl_por_dinero(pos_eur, st.session_state['blindaje_eurusd'])
            
            # Reset de blindajes independientes
            if not pos_oro: st.session_state['blindaje_oro'] = 0
            if not pos_eur: st.session_state['blindaje_eurusd'] = 0

            # 4. HISTORIAL DE OPERACIONES
            st.markdown("### 📋 Auditoría de Operaciones (Hoy)")
            if hist:
                df_h = pd.DataFrame([h._asdict() for h in hist])
                df_h = df_h[(df_h['magic'].isin(MAGIC_NUMBERS)) & (df_h['entry'] == 1)]
                if not df_h.empty:
                    df_h['Estado'] = df_h['profit'].apply(lambda x: "✅ Profit" if x > 0 else "🛡️ SL")
                    df_h['Hora'] = pd.to_datetime(df_h['time'], unit='s').dt.strftime('%H:%M')
                    st.dataframe(df_h[['Hora', 'symbol', 'volume', 'profit', 'Estado']], use_container_width=True)

            # 5. MONITOR EN VIVO
            st.markdown("### 🚀 Monitor en Tiempo Real")
            if pos:
                df_p = pd.DataFrame([p._asdict() for p in pos])
                st.dataframe(df_p[['symbol', 'type', 'volume', 'profit', 'magic']], use_container_width=True)

            st.caption(f"Alphabot System v12.0 | {time.strftime('%H:%M:%S')}")
        time.sleep(10)