import streamlit as st
import requests
from openai import OpenAI
import os

# Em produção, essas chaves virão das secrets do Streamlit
# Localmente, você pode definir como variáveis de ambiente ou usar st.secrets
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
            "pais": data["location"]["country"]
        }
    return {"erro": "Não foi possível obter os dados do clima."}

def interpretar_clima(weather_data):
    prompt = f"""Você é um assistente de clima prático. Não use "talvez", "pode ser", "considere". Diga exatamente:

1. Quais roupas a pessoa deve usar AGORA, com base em {weather_data['temperatura']}°C e {weather_data['descricao']}
2. Qual a temperatura EXATA para o ar-condicionado da casa
3. Qual a temperatura EXATA para o ar-condicionado do carro

Use frases diretas e comandos curtos."""

    resposta = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return resposta.choices[0].message.content.strip()

# Interface do usuário
st.set_page_config(page_title="Clima com IA")
st.title("Agente do Clima com GPT")

st.markdown("### Informe sua Localização:")
cep = st.text_input("CEP (opcional)")
latitude = st.text_input("Latitude (opcional)")
longitude = st.text_input("Longitude (opcional)")

if st.button("Buscar Clima"):
    if cep:
        lat, lon = cep_para_lat_lon(cep)
        if lat and lon:
            latitude, longitude = str(lat), str(lon)
        else:
            st.error("Não foi possível obter coordenadas via CEP.")

    if latitude and longitude:
        clima = get_weather(latitude, longitude)
        if "erro" not in clima:
            st.markdown(f"### Localizado em: {clima['cidade']}, {clima['pais']}")
            st.subheader("Clima Atual")
            st.write(f"Temperatura: {clima['temperatura']}°C")
            st.write(f"Umidade: {clima['umidade']}%")
            st.write(f"Vento: {clima['vento_kmh']} km/h")
            st.write(f"Descrição: {clima['descricao']}")

            st.subheader("Instruções do GPT")
            analise = interpretar_clima(clima)
            st.write(analise)
        else:
            st.error(clima["erro"])
    else:
        st.warning("Informe um CEP ou coordenadas válidas.")
