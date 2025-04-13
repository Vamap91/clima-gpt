import streamlit as st
import requests
from openai import OpenAI
import os

# Em produção, essas chaves virão das secrets do Streamlit
def get_openai_key():
    return st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else os.environ.get("OPENAI_API_KEY")

def get_weather_key():
    return st.secrets["WEATHER_API_KEY"] if "WEATHER_API_KEY" in st.secrets else os.environ.get("WEATHER_API_KEY")

# Inicializa o cliente OpenAI com a chave da API
client = OpenAI(api_key=get_openai_key())
WEATHER_API_KEY = get_weather_key()

def cep_para_lat_lon(cep):
    via_cep = requests.get(f"https://viacep.com.br/ws/{cep}/json/").json()
    if "erro" not in via_cep:
        cidade = via_cep.get("localidade")
        uf = via_cep.get("uf")
        geo = requests.get(f"http://api.weatherapi.com/v1/search.json?key={WEATHER_API_KEY}&q={cidade},{uf}").json()
        if geo:
            return geo[0]["lat"], geo[0]["lon"]
    return None, None

def get_weather(latitude, longitude):
    url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={latitude},{longitude}&aqi=no"
    response = requests.get(url)
    data = response.json()
    if "current" in data and "location" in data:
        return {
            "temperatura": data["current"]["temp_c"],
            "umidade": data["current"]["humidity"],
            "vento_kmh": data["current"]["wind_kph"],
            "descricao": data["current"]["condition"]["text"],
            "cidade": data["location"]["name"],
            "pais": data["location"]["country"],
            "sensacao": data["current"]["feelslike_c"],
        }
    return {"erro": "Não foi possível obter os dados do clima."}

def interpretar_clima(weather_data):
    prompt = f"""Você é um assistente especialista em conforto térmico. Dê conselhos precisos sem usar "talvez", "pode ser", ou "considere".

CLIMA ATUAL: {weather_data['temperatura']}°C, sensação térmica de {weather_data['sensacao']}°C. 
Condição: {weather_data['descricao']}. Umidade: {weather_data['umidade']}%. Vento: {weather_data['vento_kmh']} km/h.

FORNEÇA:
1. ROUPAS RECOMENDADAS: Exatamente o que vestir agora para este clima.
2. AR-CONDICIONADO EM CASA: Temperatura EXATA recomendada para o ar-condicionado.
3. AR-CONDICIONADO NO CARRO: Temperatura EXATA recomendada e se deve usar recirculação ou ar externo.

Use frases diretas e comandos curtos. Divida a resposta claramente em seções numeradas (1, 2, 3)."""

    resposta = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return resposta.choices[0].message.content.strip()

# Interface do usuário
st.title("Smart Clima - Assistente de Conforto Térmico")

# Entrada de dados
st.header("Informe sua localização")

# Opções de entrada
option = st.radio("Escolha uma opção:", ["CEP", "Coordenadas"])

if option == "CEP":
    cep = st.text_input("CEP (somente números):", placeholder="Ex: 01310100")
    search_button = st.button("Buscar por CEP")
    
    if search_button and cep:
        with st.spinner("Buscando localização..."):
            lat, lon = cep_para_lat_lon(cep)
            if lat and lon:
                st.success(f"Coordenadas encontradas: {lat}, {lon}")
                
                with st.spinner("Obtendo clima..."):
                    clima = get_weather(lat, lon)
                    if "erro" not in clima:
                        st.session_state.clima = clima
                    else:
                        st.error(clima["erro"])
            else:
                st.error("Não foi possível obter coordenadas via CEP.")
else:
    col1, col2 = st.columns(2)
    with col1:
        latitude = st.text_input("Latitude:", placeholder="Ex: -23.550520")
    with col2:
        longitude = st.text_input("Longitude:", placeholder="Ex: -46.633308")
    
    search_button = st.button("Buscar por Coordenadas")
    
    if search_button and latitude and longitude:
        with st.spinner("Obtendo clima..."):
            clima = get_weather(latitude, longitude)
            if "erro" not in clima:
                st.session_state.clima = clima
            else:
                st.error(clima["erro"])

# Exibir informações do clima
if 'clima' in st.session_state:
    clima = st.session_state.clima
    
    st.header(f"Clima em {clima['cidade']}, {clima['pais']}")
    
    # Exibir detalhes do clima
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"{clima['temperatura']}°C")
        st.write(f"Sensação térmica: {clima['sensacao']}°C")
        st.write(f"Condição: {clima['descricao']}")
    
    with col2:
        st.metric("Umidade", f"{clima['umidade']}%")
        st.metric("Vento", f"{clima['vento_kmh']} km/h")
    
    # Interpretação do clima com GPT
    st.header("Recomendações Personalizadas")
    
    if st.button("Gerar Recomendações"):
        with st.spinner("Analisando o clima e gerando recomendações..."):
            recomendacoes = interpretar_clima(clima)
            st.session_state.recomendacoes = recomendacoes
    
    if 'recomendacoes' in st.session_state:
        st.write(st.session_state.recomendacoes)
