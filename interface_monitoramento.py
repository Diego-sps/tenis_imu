# streamlit_app.py
import streamlit as st
import asyncio
from bleak import BleakClient, BleakScanner
import re
import pandas as pd
from datetime import datetime

# Configurações iniciais
CHAR_UUID = "0000xxxx-0000-1000-8000-00805f9b34fb"  # substitua com UUID real
DEVICE_NAME = "XIAO_TENIS"  # substitua com nome correto

st.set_page_config(page_title="Monitoramento Sensorial", layout="centered")
st.title("🎾 Monitoramento em Tempo Real do Sensor IMU")
st.text_input("CHAR_UUID", CHAR_UUID, key="char_uuid_input")
st.text_input("DEVICE_NAME", DEVICE_NAME, key="device_name_input")

# Iniciar buffers se ainda não foram iniciados
if "data_buffer" not in st.session_state:
    st.session_state.data_buffer = pd.DataFrame(columns=["timestamp", "ax", "ay", "az", "battery"])

# Placeholder para widgets
acc_placeholder = st.empty()
bat_placeholder = st.empty()

chart_ax = st.line_chart()
chart_ay = st.line_chart()
chart_az = st.line_chart()

# Função para extrair valores
def parse_data(data_str):
    match = re.findall(r"[-+]?\d*\.\d+|\d+", data_str)
    if len(match) >= 4:
        ax, ay, az, battery = map(float, match)
        return ax, ay, az, battery
    return None

# Callback BLE
def callback(sender, data):
    decoded = data.decode("utf-8")
    parsed = parse_data(decoded)

    if parsed:
        ax, ay, az, battery = parsed
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Adiciona nova linha ao buffer
        new_row = {"timestamp": timestamp, "ax": ax, "ay": ay, "az": az, "battery": battery}
        st.session_state.data_buffer = pd.concat(
            [st.session_state.data_buffer, pd.DataFrame([new_row])],
            ignore_index=True
        )

        # Manter os últimos 50 valores apenas
        if len(st.session_state.data_buffer) > 50:
            st.session_state.data_buffer = st.session_state.data_buffer.tail(50).reset_index(drop=True)

        # Atualiza widgets
        acc_placeholder.metric("📊 Aceleração (g)", f"X: {ax:.2f} | Y: {ay:.2f} | Z: {az:.2f}")
        bat_placeholder.progress(int(battery), text=f"🔋 Bateria: {battery:.0f}%")

        # Atualiza gráficos
        chart_ax.line_chart(st.session_state.data_buffer[["timestamp", "ax"]].set_index("timestamp"))
        chart_ay.line_chart(st.session_state.data_buffer[["timestamp", "ay"]].set_index("timestamp"))
        chart_az.line_chart(st.session_state.data_buffer[["timestamp", "az"]].set_index("timestamp"))

# Conexão BLE
async def read_data(address):
    async with BleakClient(address) as client:
        await client.start_notify(CHAR_UUID, callback)
        while True:
            await asyncio.sleep(1)

async def run():
    devices = await BleakScanner.discover()
    xiao = next((d for d in devices if DEVICE_NAME in d.name), None)

    if not xiao:
        st.error("Dispositivo XIAO não encontrado. Verifique se está ligado.")
        return

    await read_data(xiao.address)

# Executar a rotina BLE se ainda não foi iniciada
if "ble_started" not in st.session_state:
    st.session_state.ble_started = True
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run())
