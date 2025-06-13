import streamlit as st
import json
import pandas as pd
import investpy
import openai
import matplotlib.pyplot as plt
import numpy as np
import time
import datetime
from alpha_vantage.timeseries import TimeSeries
import re
import requests




# ============ NUEVO: FUNCIÓN PARA EXTRAER SECCIONES ============
def extract_numbered_blocks(text):
    # Busca los títulos que empiezan con un número y dos puntos
    pattern = r"(?sm)^(\d+)\.\s*(.*?)(?=^\d+\.|\Z)"
    matches = re.findall(pattern, text)
    bloques = {}
    for num, content in matches:
        bloques[int(num)] = content.strip()
    # Buscar conclusión si existe, aunque no esté enumerada
    conc_pat = r"(?i)(Conclusi[oó]n.*?)$"
    conc_match = re.search(conc_pat, text)
    conclusion = conc_match.group(1).strip() if conc_match else ""
    return bloques, conclusion

import csv
import io




def extraer_conclusion_json(text):
    """
    Busca el primer bloque JSON con la clave 'conclusion' y lo devuelve como dict.
    Si no se encuentra, retorna None.
    Si falta una llave de cierre al final, la agrega.
    """
    import re, json
    pattern = r'(\{[\s\S]*?"conclusion"[\s\S]*?\})'
    match = re.search(pattern, text)
    if match:
        json_str = match.group(1)
        # Limpieza: sin saltos de línea ni espacios extra
        json_str = json_str.replace('\n', '').replace('\r', '').strip()
        # Si falta la llave de cierre final, la agregamos
        if json_str.count('{') > json_str.count('}'):
            json_str += "}"
        try:
            return json.loads(json_str)['conclusion']
        except Exception as e:
            st.warning(f"Error al parsear el JSON: {e}\nContenido recibido: {json_str}")
            return None
    return None







# ============ FIN DE SECCIÓN NUEVA ============
# Configuración general
st.set_page_config(page_title="Análisis de MARKET MAP AI", layout="wide")
#openai.api_key = st.secrets["OPENAI_API_KEY"]
# Inicializa ticker seleccionado
if 'selected_ticker' not in st.session_state:
    st.session_state['selected_ticker'] = "AAPL"


# =====================
# CACHÉ y sesión
# =====================
import requests

@st.cache_data(ttl=3600)
def obtener_datos_y_analisis(ticker, selected_interval):
    # Cambia la URL si tu backend está en otro host/puerto
    url = "https://backendaimm-production.up.railway.app/analizar"
    payload = {
        "ticker": ticker,
        "intervalo": selected_interval
    }
    try:
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            data = response.json()
            resultado = data.get("resultado", "")
            return None, resultado  # El primer valor (data) es None, a menos que necesites reconstruir un DataFrame en el frontend
        else:
            return None, f"Error en API: {response.text}"
    except Exception as e:
        return None, f"Error conectando con backend: {e}"





if 'ultimo_analisis' not in st.session_state:
    st.session_state['ultimo_analisis'] = None

# =====================
# UI y estilo
# =====================
st.markdown("""
    <style>
    body { background-color: #0f172a; color: white; }
    .stApp { background-color: #0f172a; color: white; }
    .card {
        background-color: #1e293b;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    div.stButton > button {
        background-color: #3b82f6;
        color: white;
        border-radius: 8px;
        border: none;
        transition: background-color 0.3s ease;
    }
    div.stButton > button:hover {
        background-color: #2563eb;
    }
    .card-metricas {
        background-color: #1e293b;
        padding: 25px;
        border-radius: 12px;
        margin-top: 20px;
        margin-bottom: 20px;
    }
    .metric-title {
        font-size: 14px;
        color: #cbd5e1;
        margin-bottom: 5px;
    }
    .metric-value {
        font-size: 22px;
        font-weight: bold;
        color: white;
    }
    .metric-sub {
        font-size: 13px;
        color: #94a3b8;
    }
    .metric-sub.positive {
        color: #4ade80;
    }
    .metric-sub.negative {
        color: #f87171;
    }
   .metric-box {
    background-color: #1e2533;
    padding: 15px;
    border-radius: 10px;
    text-align: left;
    margin-bottom: 10px;
}
 .symbol-card {
    background-color: #1e2533;
    padding: 20px;
    border-radius: 12px;
    margin-top: 20px;
    margin-bottom: 20px;
}

.symbol-button {
    display: inline-block;
    padding: 8px 14px;
    border-radius: 16px;
    font-size: 13px;
    margin-right: 8px;
    margin-bottom: 8px;
    background-color: #334155;
    color: white;
}

.symbol-button.positive {
    background-color: #166534;
    color: #bbf7d0;
}

.symbol-button.negative {
    background-color: #7f1d1d;
    color: #fecaca;
}

.symbol-selected {
    background-color: #2563eb !important;
    color: white !important;
}

.symbol-search {
    padding: 8px 12px;
    border-radius: 8px;
    border: none;
    width: 100%;
    background-color: #0f172a;
    color: white;
    font-size: 13px;
}
.timeframe-button {
    display: inline-block;
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 13px;
    margin-right: 8px;
    margin-bottom: 8px;
    background-color: #334155;
    color: white;
    cursor: pointer;
}

.timeframe-button.selected {
    background-color: #2563eb;
    color: white;
}
/* Estilo mejorado para botones de temporalidad */
div[role="radiogroup"] > label {
    background-color: #334155;
    color: white !important;
    padding: 6px 14px;
    border-radius: 8px;
    margin-right: 6px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-weight: 500;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* Hover */
div[role="radiogroup"] > label:hover {
    background-color: #475569 !important;
    color: white !important;
}

/* ✅ Selección activa: ambas versiones de Streamlit */
div[role="radiogroup"] > label[data-selected="true"],
div[role="radiogroup"] > label[aria-checked="true"] {
    background-color: #3b82f6 !important;
    color: white !important;
    font-weight: 700;
}

/* Forzar texto blanco en todo el contenido interno */
div[role="radiogroup"] > label * {
    color: white !important;
    opacity: 1 !important;
}

/* Oculta el círculo del radio */
div[role="radiogroup"] > label > div:first-child {
    display: none !important;
}

</style>

""", unsafe_allow_html=True)

# =====================
# Encabezado y selección
# =====================
st.title("Análisis MARKET MAP AI")

tickers = ["AAPL", "MSFT", "TSLA", "GOOGL", "NVDA","AMZN"]
intervalos = ["1h", "1d", "1wk"]
# --- NUEVA barra de control horizontal ---
ticker_changes = {
    "AAPL": "+1.2%",
    "MSFT": "+0.8%",
    "GOOGL": "-0.5%",
    "AMZN": "+1.7%",
    "NVDA": "-1.2",
    "TSLA": "+2.3%"
}
tickers = list(ticker_changes.keys())

# Abre el panel contenedor visual, justo después del título
st.markdown(
    """
    <div style='background-color:#232f45; padding:32px 36px 36px 36px; border-radius:22px; margin-bottom:32px; margin-top:12px;'>
    """, 
    unsafe_allow_html=True
)

#st.markdown("<div class='symbol-card'>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([5, 2, 4])

with col1:
    st.markdown("**Activos**", unsafe_allow_html=True)
    for symbol, change in ticker_changes.items():
        css_class = "symbol-button"
        if symbol == st.session_state['selected_ticker']:
            css_class += " symbol-selected"
        elif "-" in change:
            css_class += " negative"
        else:
            css_class += " positive"
        if st.button(f"{symbol} {change}", key=f"btn_{symbol}"):
            st.session_state['selected_ticker'] = symbol

with col2:
    st.markdown("**Ticker**", unsafe_allow_html=True)
    ticker = st.selectbox(
        "",
        tickers,
        index=tickers.index(st.session_state['selected_ticker']),
        key="select_ticker"
    )
    if ticker != st.session_state['selected_ticker']:
        st.session_state['selected_ticker'] = ticker

with col3:
    st.markdown("**Temporalidad**", unsafe_allow_html=True)
    selected_interval = st.radio(
        "",
        ["15M", "1H", "1D", "1W", "1M"],
        key="interval_radio",
        horizontal=True,
    )

    # Forzamos visualmente el botón seleccionado con CSS dinámico
    st.markdown(f"""
        <style>
        div[role="radiogroup"] > label:nth-child({['15M','1H','1D','1W','1M'].index(selected_interval)+1}) {{
            background-color: #3b82f6 !important;
            color: white !important;
            font-weight: 700;
        }}
        </style>
    """, unsafe_allow_html=True)

    # Centramos visualmente los botones
    st.markdown("""
        <style>
        div[role="radiogroup"] {
            display: flex;
            justify-content: flex-start;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 6px;
        }
        </style>
    """, unsafe_allow_html=True)


import matplotlib.pyplot as plt



# --- Simula tus precios. En la vida real usa tu dataframe de precios! ---
import numpy as np
import pandas as pd
np.random.seed(1)
dias = pd.date_range("2024-03-08", "2024-06-06", freq="B")
precios = np.cumsum(np.random.normal(0.6, 1.1, len(dias))) + 164


# Inicializa variables para que nunca estén indefinidas
bloques = {}
conclusion = ""
conclusion_json = None


# ================== ...tu código y UI arriba... ==================

# ========== ZONA DE RESULTADOS Y GRÁFICA EN DOS COLUMNAS ==========


# Justo antes de los bloques de sección:
# Cuando obtienes el resultado, haz:


if st.button("🔍 Obtener análisis", key="analisis_btn"):
    with st.spinner("Market Map AI is Generating the Analysis"):
        data, resultado = obtener_datos_y_analisis(ticker, selected_interval)
        bloques, conclusion_text = extract_numbered_blocks(resultado)
        conclusion_json = extraer_conclusion_json(resultado)
        st.session_state['ultimo_analisis'] = (data, resultado)
        st.session_state['bloques'] = bloques
        st.session_state['conclusion'] = conclusion_text
        st.session_state['conclusion_json'] = conclusion_json
        st.write("DEBUG - Texto de conclusión:", repr(conclusion_text))
        st.write("DEBUG - JSON de conclusión:", conclusion_json)
        # Actualiza variables locales también, para el render inmediato
        conclusion = conclusion_text
elif 'bloques' in st.session_state:
    bloques = st.session_state['bloques']
    conclusion = st.session_state.get('conclusion', "")
    conclusion_json = st.session_state.get('conclusion_json', None)

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("""
<div style='height:2px; background:linear-gradient(to right, #334155 10%, #3b82f6 90%); border-radius:2px; margin: -6px 0 24px 0;'></div>
""", unsafe_allow_html=True)


# ================== MOSTRAR SECCIONES ==================
def seccion_html(titulo, contenido, emoji):
    return f"""
    <div style="background-color:#1e293b; padding: 20px; border-radius: 12px; margin-top: 20px;">
        <h3 style="color:white; margin-bottom:10px;">{emoji} {titulo}</h3>
        <div style="background-color:#334155; padding: 15px; border-radius: 10px;">
            <p style="color:white; font-size:15px;">
                {contenido.strip() if contenido else 'Aquí va a ir el análisis de la AI. Este texto es un placeholder.'}
            </p>
        </div>
    </div>
    """

col_izq, col_der = st.columns([1.2, 1])  # Puedes ajustar la proporción si quieres

with col_der:
    st.markdown(seccion_html("Resultados completos de la AI", bloques.get(1, ""), "🤖"), unsafe_allow_html=True)
    st.markdown(seccion_html("Proyección de Precios Target y Stop Loss", bloques.get(4, ""), "🎯"), unsafe_allow_html=True)
    st.markdown(seccion_html("Probabilidad de Subida o Bajada", bloques.get(3, ""), "📊"), unsafe_allow_html=True)
    # Agregar la conclusión al final de la evaluación si existe
    eval_content = bloques.get(5, "")
    if conclusion:
        eval_content += "\n\n" + conclusion
    st.markdown(seccion_html("Evaluación de Riesgo/Beneficio", eval_content, "⚖️"), unsafe_allow_html=True)
    st.text(f"Conclusión (debug): {conclusion}")




with col_izq:
    st.markdown("#### 📊 Price, Target y Stop")
    if st.button("📊 Ver gráfica de proyección"):
        conclusion_json = st.session_state.get('conclusion_json', None)
        if conclusion_json:
            # Extrae los valores y asegúrate que son floats
            last = float(conclusion_json.get('last_price'))
            target = float(conclusion_json.get('probable_target'))
            stop = float(conclusion_json.get('probable_stop'))

            # Normalización visual:
            last_y = 0.5    # Last siempre al 50%
            target_y = 0.9  # Target siempre al 90% (arriba)
            dist_target = target - last
            dist_stop = last - stop

            if dist_target == 0:
                pos_stop = 0.1  # Si target == last, lo mandamos abajo
            else:
                # Stop relativo, cuanto más lejos esté del last, más abajo lo ubicamos
                pos_stop = last_y - (dist_stop / dist_target) * (target_y - last_y)
                # Limita a un rango lógico
                pos_stop = max(0.1, min(pos_stop, 0.49))

            y_vals = [pos_stop, last_y, target_y]
            labels = [
                f"Stop\n${stop:.2f}",
                f"Last\n${last:.2f}",
                f"Target\n${target:.2f}"
            ]
            colors = ['#f87171', '#60a5fa', '#22d3ee']

            fig2, ax2 = plt.subplots(figsize=(4, 2))
            for y, color, label in zip(y_vals, colors, labels):
                ax2.axhline(y, color=color, linewidth=1, linestyle='--')
                ax2.text(0.07, y, label, va='center', ha='left', fontsize=11, color=color, weight='bold')

            ax2.set_ylim(0, 1)
            ax2.set_yticks([])
            ax2.set_xticks([])
            ax2.set_facecolor('#1e2533')
            fig2.patch.set_facecolor('#1e2533')
            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_visible(False)
            ax2.spines['bottom'].set_visible(False)
            ax2.spines['left'].set_visible(False)
            st.pyplot(fig2)
        else:
            st.warning("No se pudo extraer el bloque JSON de la conclusión para graficar.")

    # Bloque de métricas bajo el gráfico:
    conclusion_json = st.session_state.get('conclusion_json', None)
    if conclusion_json:
        rr_ratio = conclusion_json.get('risk_reward_ratio', None)
        probability = conclusion_json.get('probability', None)
    else:
        rr_ratio = None
        probability = None

    if rr_ratio is not None:
        st.markdown("""
            <div style="background-color:#1e293b; padding:18px 16px 10px 18px; border-radius:12px; margin-top:22px;">
                <h4 style="color:white; margin-bottom:6px;">⚖️ Risk Reward Ratio</h4>
                <p style="color:#fbbf24; font-size:21px; font-weight:700; margin-bottom:0;">
                    {}</p>
            </div>
        """.format(rr_ratio), unsafe_allow_html=True)

   # Probability bar con color dinámico
    if probability is not None:
        prob = float(probability)
        # Determina el color de la barra
        if prob < 50:
            bar_color = "#ef4444"   # rojo
        elif 50 <= prob < 60:
            bar_color = "#f59e42"   # naranja
        elif 60 <= prob < 80:
            bar_color = "#fbbf24"   # amarillo
        else:
            bar_color = "#22d46c"   # verde

        st.markdown(f"""
            <div style="background-color:#1e293b; padding:18px 16px 20px 18px; border-radius:12px; margin-top:22px;">
                <h4 style="color:white; margin-bottom:6px;">📊 Probability</h4>
                <div style="background-color:#334155; border-radius:7px; height:30px; width:100%; margin-bottom:8px; position:relative;">
                    <div style="height:100%; width:{prob}%; background:{bar_color}; border-radius:7px;"></div>
                    <div style="position:absolute; left:0; top:0; width:100%; height:30px; display:flex; align-items:center; justify-content:center; color:white; font-size:19px; font-weight:700;">
                        {prob:.1f}%
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)





# ===================== MOSTRAR RESULTADO COMPLETO (RAW) =====================
st.markdown(
    """
    <div style="background-color:#1e2533; padding: 20px; border-radius: 12px; margin-top: 20px;">
        <h3 style="color:white; margin-bottom:10px;">📝 Resultado completo de la AI</h3>
        <div style="background-color:#334155; padding: 15px; border-radius: 10px;">
            <pre style="color:white; font-size:14px; white-space: pre-wrap;">{}</pre>
        </div>
    </div>
    """.format(
        st.session_state['ultimo_analisis'][1] if 'ultimo_analisis' in st.session_state and st.session_state['ultimo_analisis'] else ""
    ),
    unsafe_allow_html=True,
)

# =====================
# Mostrar último análisis guardado
# =====================
if st.button("🕘 Mostrar último análisis"):
    if st.session_state['ultimo_analisis'] is not None:
        data, resultado = st.session_state['ultimo_analisis']
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("🧠 Último análisis cargado")
        st.markdown(resultado, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("📈 Proyección de Precios")
        precios = np.linspace(data["Close"].min(), data["Close"].max(), 30) + np.random.normal(0, 0.3, 30)
        dias = np.arange(len(precios))
        precio_actual = float(data["Close"].iloc[-1])
        target = precio_actual * 1.05
        stop_loss = precio_actual * 0.97

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(dias, precios, color='blue', linewidth=2)
        ax.axhline(precio_actual, color='green', linestyle='--', label=f'Actual: ${precio_actual:.2f}')
        ax.axhline(target, color='purple', linestyle='--', label=f'Target: ${target:.2f}')
        ax.axhline(stop_loss, color='red', linestyle='--', label=f'Stop Loss: ${stop_loss:.2f}')
        ax.fill_between(dias, precio_actual * 0.99, precio_actual * 1.01, color='gray', alpha=0.2, label='Zona Neutra')
        ax.set_facecolor('#0f172a')
        fig.patch.set_facecolor('#0f172a')
        ax.tick_params(colors='white')
        ax.set_title("Proyección de precios", color='white')
        ax.legend(facecolor='#1e293b', edgecolor='white', labelcolor='white')
        st.pyplot(fig)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("No hay ningún análisis guardado todavía.")

# --- Título y datos de ejemplo (usa tus propios datos reales) ---
st.markdown("""
<div style="background-color:#1e2533; padding: 28px 32px 32px 32px; border-radius: 18px; margin-bottom: 20px;">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <span style="font-size:2.2rem; font-weight:700; color:white;">AAPL</span>
            <span style="font-size:2.2rem; font-weight:700; color:#4ade80; margin-left:8px;">$182.63</span><br>
            <span style="font-size:1.1rem; color:#cbd5e1;">Apple Inc. • NASDAQ</span>
        </div>
        <div>
            <span style="margin-right:8px; background:#222d3c; padding:7px 16px; border-radius:8px; color:#cbd5e1;">1D</span>
            <span style="margin-right:8px; background:#222d3c; padding:7px 16px; border-radius:8px; color:#cbd5e1;">1S</span>
            <span style="background:#3b82f6; padding:7px 16px; border-radius:8px; color:white; font-weight:600;">1M</span>
            <span style="margin-left:8px; background:#222d3c; padding:7px 16px; border-radius:8px; color:#cbd5e1;">3M</span>
            <span style="margin-left:8px; background:#222d3c; padding:7px 16px; border-radius:8px; color:#cbd5e1;">1A</span>
            <span style="margin-left:8px; background:#222d3c; padding:7px 16px; border-radius:8px; color:#cbd5e1;">5A</span>
        </div>
    </div>
""", unsafe_allow_html=True)        

        # --- Gráfica tipo análisis técnico ---
fig, ax = plt.subplots(figsize=(8.5, 4))
ax.plot(dias, precios, color='#3b82f6', linewidth=2.7)
ax.set_facecolor('#1e2533')
fig.patch.set_facecolor('#1e2533')
ax.spines['bottom'].set_color('#1e293b')
ax.spines['top'].set_color('#1e293b')
ax.spines['left'].set_color('#1e293b')
ax.spines['right'].set_color('#1e293b')
ax.tick_params(colors='#94a3b8', labelsize=7)
ax.grid(False)
ax.set_xlabel("")
ax.set_ylabel("")
plt.xticks(
    [dias[0], dias[len(dias)//3], dias[2*len(dias)//3], dias[-1]],
    [d.strftime("%e %b") for d in [dias[0], dias[len(dias)//3], dias[2*len(dias)//3], dias[-1]]]
)
plt.yticks(fontsize=7)

st.pyplot(fig)

#comandos de actuallizacion en visul termina
#git add iamarketmap_frontend.py
#git commit -m "fondo de la seccion superior"
#git push

