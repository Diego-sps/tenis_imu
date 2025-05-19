import streamlit as st
import asyncio
from bleak import BleakClient, BleakScanner
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Sensor IMU BLE", layout="centered")
st.title("🎾 Monitoramento em Tempo Real do Sensor IMU")

# Session state
if "dispositivos" not in st.session_state:
    st.session_state.dispositivos = []
if "dados" not in st.session_state:
    st.session_state.dados = []
if "caracteristicas" not in st.session_state:
    st.session_state.caracteristicas = []
if "endereco_conectado" not in st.session_state:
    st.session_state.endereco_conectado = ""

# 🔍 Scanner BLE
async def procurar_dispositivos():
    devices = await BleakScanner.discover()
    return [(d.name or "Desconhecido", d.address) for d in devices]

# 📑 Listar características
async def listar_caracteristicas(address):
    async with BleakClient(address) as client:
        services = await client.get_services()
        return [(char.uuid, char.properties) for service in services for char in service.characteristics]

# 📡 Callback para notify
def notification_handler(sender, data):
    try:
        valor = float(data.decode('utf-8').strip())  # Tenta converter para float
    except:
        valor = data.decode('utf-8').strip()
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.dados.append({"Horário": timestamp, "Valor": valor})

# 🔗 Conectar e receber
async def conectar_e_receber(address, char_uuid):
    async with BleakClient(address) as client:
        if await client.is_connected():
            st.success(f"🔗 Conectado ao {address}")
            try:
                await client.start_notify(char_uuid, notification_handler)
                await asyncio.sleep(10)  # Leitura por 10s
                await client.stop_notify(char_uuid)
            except Exception as e:
                st.error(f"Erro ao iniciar/parar notify: {e}")
        else:
            st.error("❌ Não foi possível conectar.")

# Botão escanear dispositivos
if st.button("🔍 Escanear dispositivos BLE"):
    st.session_state.dispositivos = asyncio.run(procurar_dispositivos())
    st.session_state.dados.clear()

# Se dispositivos foram encontrados
if st.session_state.dispositivos:
    opcoes = [f"{nome} - {addr}" for nome, addr in st.session_state.dispositivos]
    selecao = st.selectbox("Selecione um dispositivo:", opcoes)
    index = opcoes.index(selecao)
    endereco = st.session_state.dispositivos[index][1]
    st.session_state.endereco_conectado = endereco

    # Botão para listar características
    if st.button("📑 Listar características"):
        st.session_state.caracteristicas = asyncio.run(listar_caracteristicas(endereco))

# Se características disponíveis
if st.session_state.caracteristicas:
    st.subheader("📋 Características disponíveis:")
    tabela_caracts = [{"UUID": uuid, "Propriedades": ", ".join(props)} for uuid, props in st.session_state.caracteristicas]
    st.table(tabela_caracts)

    # Apenas as com notify
    notify_uuids = [uuid for uuid, props in st.session_state.caracteristicas if "notify" in props]
    if notify_uuids:
        char_escolhida = st.selectbox("Selecione UUID para leitura:", notify_uuids)

        if st.button("🟢 Iniciar leitura (10s)"):
            asyncio.run(conectar_e_receber(st.session_state.endereco_conectado, char_escolhida))

# Mostrar dados ao vivo
if st.session_state.dados:
    st.subheader("📊 Dados recebidos:")
    df = pd.DataFrame(st.session_state.dados)

    # Gráfico
    if df["Valor"].apply(lambda x: isinstance(x, float)).all():
        st.line_chart(df.set_index("Horário")["Valor"])
    st.dataframe(df, use_container_width=True)

    # Exportar CSV
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Baixar CSV", csv, "dados_ble.csv", "text/csv")
