import streamlit as st
import requests
from datetime import datetime
from openai import OpenAI
import os

# Configuração da página
st.set_page_config(
    page_title="Smart Clima - Assistente de Conforto Térmico",
    page_icon="🌡️",
    layout="wide"
)

# Em produção, essas chaves virão das secrets do Streamlit
# Localmente, você pode definir como variáveis de ambiente ou usar st.secrets
def get_openai_key():
    return st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else os.environ.get("OPENAI_API_KEY")

def get_weather_key():
    return st.secrets["WEATHER_API_KEY"] if "WEATHER_API_KEY" in st.secrets else os.environ.get("WEATHER_API_KEY")

# Inicializa o cliente OpenAI com a chave da API
client = OpenAI(api_key=get_openai_key())
WEATHER_API_KEY = get_weather_key()

# Inicialização de variáveis de sessão
if 'last_locations' not in st.session_state:
    st.session_state.last_locations = []

if 'user_preferences' not in st.session_state:
    st.session_state.user_preferences = {
        'temp_preference': 'neutro',
        'home_schedule': ['08:00', '18:00'],
        'car_usage': ['07:30', '17:30']
    }

# Função para obter as coordenadas a partir do CEP
def cep_para_lat_lon(cep):
    via_cep = requests.get(f"https://viacep.com.br/ws/{cep}/json/").json()
    if "erro" not in via_cep:
        cidade = via_cep.get("localidade")
        uf = via_cep.get("uf")
        geo = requests.get(f"http://api.weatherapi.com/v1/search.json?key={WEATHER_API_KEY}&q={cidade},{uf}").json()
        if geo:
            return geo[0]["lat"], geo[0]["lon"]
    return None, None

# Função para obter dados meteorológicos atuais
def get_weather(latitude, longitude):
    url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={latitude},{longitude}&aqi=yes"
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
            "ultima_atualizacao": data["current"]["last_updated"]
        }
    return {"erro": "Não foi possível obter os dados do clima."}

# Função para obter previsão para as próximas horas
def get_forecast(latitude, longitude):
    url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={latitude},{longitude}&days=1&aqi=yes&hour=24"
    response = requests.get(url)
    data = response.json()
    if "forecast" in data:
        # Extrai as previsões horárias para as próximas 24 horas
        hourly_forecast = data["forecast"]["forecastday"][0]["hour"]
        
        # Filtra apenas as horas futuras começando da hora atual
        current_hour = datetime.now().hour
        future_forecast = hourly_forecast[current_hour:] + hourly_forecast[:current_hour]
        
        # Seleciona apenas as próximas 8 horas
        next_hours = future_forecast[:8]
        
        forecast_data = []
        for hour_data in next_hours:
            hour_time = datetime.fromisoformat(hour_data["time"].replace("Z", "+00:00"))
            forecast_data.append({
                "hora": hour_time.strftime("%H:%M"),
                "temperatura": hour_data["temp_c"],
                "descricao": hour_data["condition"]["text"],
                "umidade": hour_data["humidity"],
                "vento_kmh": hour_data["wind_kph"],
                "sensacao": hour_data["feelslike_c"],
                "chance_chuva": hour_data["chance_of_rain"]
            })
        
        return forecast_data
    
    return []

# Função para interpretar o clima usando o GPT
def interpretar_clima(weather_data, forecast_data, preferences):
    # Enriquecendo o prompt com mais contexto e preferências do usuário
    temp_preference = preferences.get('temp_preference', 'neutro')
    home_schedule = preferences.get('home_schedule', ['08:00', '18:00'])
    car_usage = preferences.get('car_usage', ['07:30', '17:30'])
    
    # Formatando os dados de previsão para as próximas horas
    forecast_text = "Previsão para as próximas horas:\n"
    for i, hour in enumerate(forecast_data[:5]):  # Limitamos a 5 horas para não sobrecarregar o contexto
        forecast_text += f"- {hour['hora']}: {hour['temperatura']}°C, {hour['descricao']}, {hour['chance_chuva']}% chance de chuva\n"
    
    prompt = f"""Você é um assistente especialista em conforto térmico, climatização e economia de energia. Dê conselhos práticos e precisos - sem usar "talvez", "pode ser", ou "considere".

CLIMA ATUAL: {weather_data['temperatura']}°C, sensação térmica de {weather_data['sensacao']}°C. Condição: {weather_data['descricao']}. Umidade: {weather_data['umidade']}%. Vento: {weather_data['vento_kmh']} km/h.

{forecast_text}

PREFERÊNCIAS DO USUÁRIO:
- Preferência de temperatura: {temp_preference} (se "frio", prefere ambientes mais frescos; se "calor", prefere ambientes mais aquecidos; se "neutro", prefere temperatura moderada)
- Horário em casa: Das {home_schedule[0]} às {home_schedule[1]}
- Horário no carro: Das {car_usage[0]} às {car_usage[1]}

FORNEÇA:
1. ROUPAS RECOMENDADAS: Exatamente o que vestir agora, específico para a temperatura e condições atuais.
2. PROGRAMAÇÃO DO AR-CONDICIONADO EM CASA:
   - Temperatura EXATA recomendada para o ar-condicionado da casa
   - Horários ideais para ligar/desligar com base na previsão e presença em casa
   - Economia estimada de energia seguindo suas recomendações (em %)
3. CONFIGURAÇÃO DO AR-CONDICIONADO NO CARRO:
   - Temperatura EXATA para o ar-condicionado do carro
   - Orientação sobre quando pré-climatizar o carro antes de sair
   - Se deve usar recirculação ou ar externo

Use frases diretas e comandos curtos. Divida a resposta claramente em seções numeradas (1, 2, 3)."""

    resposta = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return resposta.choices[0].message.content.strip()

# Função para salvar histórico de localizações
def save_location(cidade, latitude, longitude):
    # Verifica se já existe essa localização no histórico
    for loc in st.session_state.last_locations:
        if loc['cidade'] == cidade and loc['latitude'] == latitude and loc['longitude'] == longitude:
            # Move para o topo se já existir
            st.session_state.last_locations.remove(loc)
            st.session_state.last_locations.insert(0, loc)
            return
    
    # Adiciona nova localização no topo
    new_location = {
        'cidade': cidade,
        'latitude': latitude,
        'longitude': longitude,
        'timestamp': datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    
    # Mantém apenas as últimas 5 localizações
    st.session_state.last_locations.insert(0, new_location)
    if len(st.session_state.last_locations) > 5:
        st.session_state.last_locations = st.session_state.last_locations[:5]

# Estilo personalizado via CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #FF9900;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.8rem;
        color: #FF9900;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .recommendation-box {
        background-color: rgba(255, 153, 0, 0.1);
        border-left: 4px solid #FF9900;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .current-temp {
        font-size: 3rem;
        font-weight: bold;
        color: #1E88E5;
    }
    .weather-desc {
        font-size: 1.2rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Layout principal
st.markdown("<h1 class='main-header'>Smart Clima</h1>", unsafe_allow_html=True)
st.markdown("### Assistente de Conforto Térmico")

# Layout em duas colunas
col1, col2 = st.columns([1, 2])

with col1:
    # Entrada de localização
    st.markdown("#### Localização")
    
    # Abas para diferentes métodos de entrada
    tab1, tab2, tab3 = st.tabs(["CEP", "Coordenadas", "Histórico"])
    
    with tab1:
        cep = st.text_input("CEP (somente números)", placeholder="Ex: 01310100")
        if st.button("Buscar por CEP", use_container_width=True):
            if cep:
                with st.spinner("Buscando localização..."):
                    lat, lon = cep_para_lat_lon(cep)
                    if lat and lon:
                        latitude, longitude = str(lat), str(lon)
                        st.session_state.latitude = latitude
                        st.session_state.longitude = longitude
                        
                        with st.spinner("Obtendo clima..."):
                            clima = get_weather(latitude, longitude)
                            if "erro" not in clima:
                                st.session_state.clima = clima
                                forecast = get_forecast(latitude, longitude)
                                st.session_state.forecast_data = forecast
                                
                                # Salva localização no histórico
                                save_location(clima['cidade'], latitude, longitude)
                            else:
                                st.error(clima["erro"])
                    else:
                        st.error("Não foi possível obter coordenadas via CEP.")
            else:
                st.warning("Informe um CEP válido.")
    
    with tab2:
        latitude = st.text_input("Latitude", placeholder="Ex: -23.550520")
        longitude = st.text_input("Longitude", placeholder="Ex: -46.633308")
        if st.button("Buscar por Coordenadas", use_container_width=True):
            if latitude and longitude:
                st.session_state.latitude = latitude
                st.session_state.longitude = longitude
                
                with st.spinner("Obtendo clima..."):
                    clima = get_weather(latitude, longitude)
                    if "erro" not in clima:
                        st.session_state.clima = clima
                        forecast = get_forecast(latitude, longitude)
                        st.session_state.forecast_data = forecast
                        
                        # Salva localização no histórico
                        save_location(clima['cidade'], latitude, longitude)
                    else:
                        st.error(clima["erro"])
            else:
                st.warning("Informe coordenadas válidas.")
    
    with tab3:
        st.markdown("#### Localizações recentes")
        if len(st.session_state.last_locations) > 0:
            for idx, loc in enumerate(st.session_state.last_locations):
                location_str = f"{loc['cidade']} ({loc['timestamp']})"
                if st.button(location_str, key=f"hist_{idx}", use_container_width=True):
                    latitude, longitude = str(loc['latitude']), str(loc['longitude'])
                    st.session_state.latitude = latitude
                    st.session_state.longitude = longitude
                    
                    with st.spinner("Obtendo clima..."):
                        clima = get_weather(latitude, longitude)
                        if "erro" not in clima:
                            st.session_state.clima = clima
                            forecast = get_forecast(latitude, longitude)
                            st.session_state.forecast_data = forecast
                        else:
                            st.error(clima["erro"])
        else:
            st.info("Nenhuma localização no histórico.")
            
    # Botão para usar geolocalização (simulado)
    st.markdown("#### Usar localização atual")
    if st.button("📍 Detectar minha localização", use_container_width=True):
        st.info("Esta funcionalidade requer JavaScript. Estamos simulando para demonstração.")
        # Coordenadas de São Paulo como exemplo
        latitude, longitude = "-23.550520", "-46.633308"
        st.session_state.latitude = latitude
        st.session_state.longitude = longitude
        
        with st.spinner("Obtendo clima..."):
            clima = get_weather(latitude, longitude)
            if "erro" not in clima:
                st.session_state.clima = clima
                forecast = get_forecast(latitude, longitude)
                st.session_state.forecast_data = forecast
                
                # Salva localização no histórico
                save_location(clima['cidade'], latitude, longitude)
            else:
                st.error(clima["erro"])
    
    # Seção de Preferências do Usuário
    with st.expander("⚙️ Preferências Personalizadas", expanded=False):
        st.markdown("#### Seu perfil de conforto térmico")
        temp_pref = st.radio(
            "Preferência de temperatura:",
            ["Gosto de ambientes mais frescos", "Neutro", "Gosto de ambientes mais aquecidos"],
            index=1
        )
        
        if temp_pref == "Gosto de ambientes mais frescos":
            st.session_state.user_preferences['temp_preference'] = "frio"
        elif temp_pref == "Gosto de ambientes mais aquecidos":
            st.session_state.user_preferences['temp_preference'] = "calor"
        else:
            st.session_state.user_preferences['temp_preference'] = "neutro"
        
        st.markdown("#### Rotina diária")
        col_home1, col_home2 = st.columns(2)
        with col_home1:
            home_start = st.time_input("Horário que chega em casa:", datetime.strptime("18:00", "%H:%M").time())
        with col_home2:
            home_end = st.time_input("Horário que sai de casa:", datetime.strptime("08:00", "%H:%M").time())
        
        st.session_state.user_preferences['home_schedule'] = [
            home_start.strftime("%H:%M"),
            home_end.strftime("%H:%M")
        ]
        
        col_car1, col_car2 = st.columns(2)
        with col_car1:
            car_start = st.time_input("Horário que entra no carro (manhã):", datetime.strptime("07:30", "%H:%M").time())
        with col_car2:
            car_end = st.time_input("Horário que entra no carro (tarde):", datetime.strptime("17:30", "%H:%M").time())
        
        st.session_state.user_preferences['car_usage'] = [
            car_start.strftime("%H:%M"),
            car_end.strftime("%H:%M")
        ]

# Coluna para exibição de resultados
with col2:
    if 'clima' in st.session_state and 'forecast_data' in st.session_state and st.session_state.forecast_data:
        clima = st.session_state.clima
        forecast = st.session_state.forecast_data
        
        # Exibir informações do clima atual
        st.markdown(f"<h2 class='sub-header'>Clima em {clima['cidade']}, {clima['pais']}</h2>", unsafe_allow_html=True)
        
        # Card com clima atual
        col_temp, col_details = st.columns([1, 2])
        
        with col_temp:
            st.markdown(f"<div class='current-temp'>{clima['temperatura']}°C</div>", unsafe_allow_html=True)
            st.markdown(f"<div>Sensação: {clima['sensacao']}°C</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='weather-desc'>{clima['descricao']}</div>", unsafe_allow_html=True)
        
        with col_details:
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.metric("Umidade", f"{clima['umidade']}%")
            with col_d2:
                st.metric("Vento", f"{clima['vento_kmh']} km/h")
            
            st.markdown(f"Atualizado em: {clima['ultima_atualizacao']}")
        
        # Previsão para as próximas horas (simplificada)
        st.markdown("<h3 class='sub-header'>Previsão para as próximas horas</h3>", unsafe_allow_html=True)
        
        # Detalhes da previsão por hora (simplificado)
        forecast_cols = st.columns(4)
        for i, hour in enumerate(forecast[:4]):  # Mostra as próximas 4 horas
            with forecast_cols[i]:
                st.markdown(f"<b>{hour['hora']}</b>: {hour['temperatura']}°C", unsafe_allow_html=True)
                st.write(f"{hour['descricao']}")
                if hour['chance_chuva'] > 0:
                    st.write(f"🌧️ {hour['chance_chuva']}% chance de chuva")
        
        # Interpretação do clima usando GPT
        st.markdown("<h3 class='sub-header'>Recomendações Personalizadas</h3>", unsafe_allow_html=True)
        
        # Botão para gerar ou atualizar recomendações
        if st.button("Gerar Recomendações Personalizadas", use_container_width=True):
            with st.spinner("Analisando condições e gerando recomendações personalizadas..."):
                recomendacoes = interpretar_clima(clima, forecast, st.session_state.user_preferences)
                st.session_state.recomendacoes = recomendacoes
        
        # Exibir recomendações se disponíveis
        if 'recomendacoes' in st.session_state:
            st.markdown("<div class='recommendation-box'>", unsafe_allow_html=True)
            st.markdown(st.session_state.recomendacoes.replace('\n', '<br>'), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    
    # Mensagem inicial quando não há dados
    elif 'clima' not in st.session_state:
        st.info("👈 Informe sua localização para obter recomendações personalizadas de clima e conforto térmico.")

# Rodapé com informações adicionais
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <small>Smart Clima v1.1 - Desenvolvido com ❤️ por você</small><br>
    <small>Dados de clima fornecidos por Weather API</small>
</div>
""", unsafe_allow_html=True)
