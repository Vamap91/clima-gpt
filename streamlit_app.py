import streamlit as st
import requests
from openai import OpenAI
import os
import time
from datetime import datetime
import json

# Configuração da página
st.set_page_config(
    page_title="Smart Clima",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado para UX único
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    
    .weather-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        color: white;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
    }
    
    .recommendation-card {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        color: white;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
    }
    
    .metric-card {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem;
        backdrop-filter: blur(10px);
    }
    
    .success-message {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
    }
    
    .error-message {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
    }
    
    .input-section {
        background: rgba(255, 255, 255, 0.05);
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# Funções auxiliares com tratamento de erro
def safe_request(url, timeout=10, max_retries=3):
    """Faz requisição HTTP com tratamento de erro e retry"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()  # Levanta exceção para status HTTP de erro
            return response
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                st.warning(f"Tentativa {attempt + 1} falhou. Tentando novamente...")
                time.sleep(2)
            else:
                st.error("❌ Erro de conexão. Verifique sua internet e tente novamente.")
                return None
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                st.warning(f"Timeout na tentativa {attempt + 1}. Tentando novamente...")
                time.sleep(2)
            else:
                st.error("❌ Timeout na requisição. Tente novamente.")
                return None
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Erro na requisição: {str(e)}")
            return None
    return None

def get_api_keys():
    """Obtém as chaves da API de forma segura"""
    try:
        openai_key = st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else os.environ.get("OPENAI_API_KEY")
        weather_key = st.secrets["WEATHER_API_KEY"] if "WEATHER_API_KEY" in st.secrets else os.environ.get("WEATHER_API_KEY")
        return openai_key, weather_key
    except Exception as e:
        st.error(f"❌ Erro ao obter chaves da API: {str(e)}")
        return None, None

def validate_cep(cep):
    """Valida formato do CEP"""
    import re
    # Remove caracteres não numéricos
    cep_clean = re.sub(r'\D', '', cep)
    # Verifica se tem 8 dígitos
    if len(cep_clean) == 8:
        return cep_clean
    return None

def cep_para_lat_lon(cep):
    """Converte CEP para coordenadas com tratamento de erro"""
    cep_clean = validate_cep(cep)
    if not cep_clean:
        return None, None, "CEP inválido. Use formato: 12345678"
    
    # Busca dados do CEP
    via_cep_url = f"https://viacep.com.br/ws/{cep_clean}/json/"
    response = safe_request(via_cep_url)
    
    if not response:
        return None, None, "Erro ao conectar com o serviço de CEP"
    
    try:
        via_cep = response.json()
        if "erro" in via_cep:
            return None, None, "CEP não encontrado"
        
        cidade = via_cep.get("localidade")
        uf = via_cep.get("uf")
        
        if not cidade or not uf:
            return None, None, "Dados incompletos do CEP"
        
        # Busca coordenadas
        weather_key = get_api_keys()[1]
        if not weather_key:
            return None, None, "Chave da API do clima não configurada"
        
        geo_url = f"http://api.weatherapi.com/v1/search.json?key={weather_key}&q={cidade},{uf}"
        geo_response = safe_request(geo_url)
        
        if not geo_response:
            return None, None, "Erro ao obter coordenadas"
        
        geo_data = geo_response.json()
        if geo_data:
            return geo_data[0]["lat"], geo_data[0]["lon"], None
        else:
            return None, None, "Localização não encontrada"
            
    except json.JSONDecodeError:
        return None, None, "Erro ao processar resposta do CEP"
    except Exception as e:
        return None, None, f"Erro inesperado: {str(e)}"

def get_weather(latitude, longitude):
    """Obtém dados do clima com tratamento de erro"""
    weather_key = get_api_keys()[1]
    if not weather_key:
        return {"erro": "Chave da API do clima não configurada"}
    
    url = f"http://api.weatherapi.com/v1/current.json?key={weather_key}&q={latitude},{longitude}&aqi=no"
    response = safe_request(url)
    
    if not response:
        return {"erro": "Erro ao conectar com o serviço de clima"}
    
    try:
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
                "icone": data["current"]["condition"]["icon"],
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
        else:
            return {"erro": "Dados do clima não disponíveis"}
    except json.JSONDecodeError:
        return {"erro": "Erro ao processar dados do clima"}
    except Exception as e:
        return {"erro": f"Erro inesperado: {str(e)}"}

def interpretar_clima(weather_data):
    """Gera recomendações usando OpenAI com tratamento de erro"""
    openai_key = get_api_keys()[0]
    if not openai_key:
        return "❌ Chave da API do OpenAI não configurada"
    
    try:
        client = OpenAI(api_key=openai_key)
        
        prompt = f"""Você é um assistente especialista em conforto térmico e saúde. Dê conselhos precisos e práticos.

CLIMA ATUAL: {weather_data['temperatura']}°C, sensação térmica de {weather_data['sensacao']}°C. 
Condição: {weather_data['descricao']}. Umidade: {weather_data['umidade']}%. Vento: {weather_data['vento_kmh']} km/h.

FORNEÇA RECOMENDAÇÕES ESPECÍFICAS:

## 🧥 ROUPAS RECOMENDADAS
- Exatamente o que vestir agora para este clima
- Tecidos e camadas ideais

## 🏠 AR-CONDICIONADO RESIDENCIAL
- Temperatura EXATA recomendada
- Configurações de umidade se necessário

## 🚗 AR-CONDICIONADO AUTOMOTIVO
- Temperatura EXATA recomendada
- Usar recirculação ou ar externo

## 👶 CUIDADOS COM BEBÊS
- Como vestir bebês neste clima
- Temperatura ideal do AC para ambientes com bebês
- Cuidados específicos de ventilação e umidade

Use linguagem clara e direta. Seja específico com temperaturas e instruções."""

        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.7
        )
        return resposta.choices[0].message.content.strip()
    
    except Exception as e:
        return f"❌ Erro ao gerar recomendações: {str(e)}"

# Interface principal
def main():
    # Header principal
    st.markdown("""
    <div class="main-header">
        <h1>🌡️ Smart Clima</h1>
        <p>Assistente Inteligente de Conforto Térmico</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar com informações
    with st.sidebar:
        st.markdown("### ℹ️ Sobre o App")
        st.markdown("""
        - 🎯 Recomendações personalizadas
        - 🤖 Powered by OpenAI
        - 🌍 Dados climáticos em tempo real
        - 👶 Cuidados especiais para bebês
        """)
        
        st.markdown("### 📊 Status do Sistema")
        openai_key, weather_key = get_api_keys()
        st.markdown(f"**OpenAI API:** {'✅ Configurada' if openai_key else '❌ Não configurada'}")
        st.markdown(f"**Weather API:** {'✅ Configurada' if weather_key else '❌ Não configurada'}")
    
    # Seção de entrada
    st.markdown('<div class="input-section">', unsafe_allow_html=True)
    st.markdown("### 📍 Informe sua localização")
    
    # Tabs para diferentes tipos de entrada
    tab1, tab2 = st.tabs(["🏠 Por CEP", "🌐 Por Coordenadas"])
    
    with tab1:
        st.markdown("**Digite seu CEP (apenas números):**")
        cep = st.text_input("CEP", placeholder="Ex: 01310100", key="cep_input")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            search_cep = st.button("🔍 Buscar", key="search_cep", type="primary")
        with col2:
            if st.button("📋 Usar CEP exemplo (São Paulo)", key="example_cep"):
                st.session_state.cep_input = "01310100"
                st.rerun()
    
    with tab2:
        st.markdown("**Digite as coordenadas:**")
        col1, col2 = st.columns(2)
        with col1:
            latitude = st.text_input("Latitude", placeholder="Ex: -23.550520", key="lat_input")
        with col2:
            longitude = st.text_input("Longitude", placeholder="Ex: -46.633308", key="lon_input")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            search_coords = st.button("🔍 Buscar", key="search_coords", type="primary")
        with col2:
            if st.button("📋 Usar coordenadas exemplo (São Paulo)", key="example_coords"):
                st.session_state.lat_input = "-23.550520"
                st.session_state.lon_input = "-46.633308"
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Processamento CEP
    if search_cep and cep:
        with st.spinner("🔍 Buscando localização..."):
            lat, lon, error = cep_para_lat_lon(cep)
            
            if error:
                st.markdown(f'<div class="error-message">❌ {error}</div>', unsafe_allow_html=True)
            elif lat and lon:
                st.markdown(f'<div class="success-message">✅ Coordenadas encontradas: {lat}, {lon}</div>', unsafe_allow_html=True)
                
                with st.spinner("🌤️ Obtendo dados do clima..."):
                    clima = get_weather(lat, lon)
                    if "erro" not in clima:
                        st.session_state.clima = clima
                        st.session_state.coordenadas = (lat, lon)
                        st.rerun()
                    else:
                        st.markdown(f'<div class="error-message">{clima["erro"]}</div>', unsafe_allow_html=True)
    
    # Processamento coordenadas
    if search_coords and latitude and longitude:
        try:
            lat = float(latitude)
            lon = float(longitude)
            
            with st.spinner("🌤️ Obtendo dados do clima..."):
                clima = get_weather(lat, lon)
                if "erro" not in clima:
                    st.session_state.clima = clima
                    st.session_state.coordenadas = (lat, lon)
                    st.rerun()
                else:
                    st.markdown(f'<div class="error-message">{clima["erro"]}</div>', unsafe_allow_html=True)
        except ValueError:
            st.markdown('<div class="error-message">❌ Coordenadas inválidas. Use formato numérico.</div>', unsafe_allow_html=True)
    
    # Exibição dos dados do clima
    if 'clima' in st.session_state:
        clima = st.session_state.clima
        
        # Card do clima
        st.markdown(f"""
        <div class="weather-card">
            <h2>🌤️ Clima em {clima['cidade']}, {clima['pais']}</h2>
            <p>Última atualização: {clima['timestamp']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Métricas do clima
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🌡️ Temperatura", f"{clima['temperatura']}°C", 
                     delta=f"Sensação: {clima['sensacao']}°C")
        
        with col2:
            st.metric("💧 Umidade", f"{clima['umidade']}%")
        
        with col3:
            st.metric("💨 Vento", f"{clima['vento_kmh']} km/h")
        
        with col4:
            st.metric("☁️ Condição", clima['descricao'])
        
        # Seção de recomendações
        st.markdown("""
        <div class="recommendation-card">
            <h3>🤖 Recomendações Personalizadas</h3>
            <p>Clique abaixo para obter recomendações inteligentes baseadas no clima atual</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            generate_recommendations = st.button("🎯 Gerar Recomendações", type="primary")
        with col2:
            if 'recomendacoes' in st.session_state:
                if st.button("🔄 Atualizar Recomendações"):
                    del st.session_state.recomendacoes
                    st.rerun()
        
        if generate_recommendations:
            with st.spinner("🤖 Analisando o clima e gerando recomendações..."):
                recomendacoes = interpretar_clima(clima)
                st.session_state.recomendacoes = recomendacoes
                st.rerun()
        
        # Exibir recomendações
        if 'recomendacoes' in st.session_state:
            st.markdown("### 📋 Suas Recomendações")
            st.markdown(st.session_state.recomendacoes)
            
            # Botão para salvar recomendações
            st.download_button(
                label="💾 Salvar Recomendações",
                data=f"# Recomendações Smart Clima\n\n**Local:** {clima['cidade']}, {clima['pais']}\n**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n**Temperatura:** {clima['temperatura']}°C\n\n{st.session_state.recomendacoes}",
                file_name=f"recomendacoes_clima_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown"
            )

if __name__ == "__main__":
    main()
