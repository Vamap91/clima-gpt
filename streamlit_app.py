import streamlit as st
import requests
from openai import OpenAI
import os
import time
from datetime import datetime
import json
import re
import unicodedata

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
    
    .diagnostic-card {
        background: linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%);
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        color: #2d3436;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
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
    
    .fallback-section {
        background: rgba(255, 255, 255, 0.1);
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #ffeaa7;
    }
</style>
""", unsafe_allow_html=True)

# Base de dados de coordenadas das cidades brasileiras
COORDENADAS_CIDADES = {
    'São Paulo': (-23.5505, -46.6333),
    'Rio de Janeiro': (-22.9068, -43.1729),
    'Brasília': (-15.7801, -47.9292),
    'Belo Horizonte': (-19.9167, -43.9345),
    'Fortaleza': (-3.7319, -38.5267),
    'Salvador': (-12.9714, -38.5014),
    'Curitiba': (-25.4244, -49.2654),
    'Recife': (-8.0476, -34.8770),
    'Porto Alegre': (-30.0346, -51.2177),
    'Manaus': (-3.1190, -60.0217),
    'Belém': (-1.4558, -48.5044),
    'Goiânia': (-16.6869, -49.2648),
    'Campinas': (-22.9099, -47.0626),
    'São Luís': (-2.5297, -44.3028),
    'João Pessoa': (-7.1195, -34.8450),
    'Teresina': (-5.0892, -42.8019),
    'Natal': (-5.7945, -35.2110),
    'Campo Grande': (-20.4697, -54.6201),
    'Cuiabá': (-15.6014, -56.0979),
    'Maceió': (-9.6658, -35.7353),
    'Vitória': (-20.3155, -40.3128),
    'Aracaju': (-10.9472, -37.0731),
    'Florianópolis': (-27.5954, -48.5480),
    'Palmas': (-10.1689, -48.3317),
    'Macapá': (0.0389, -51.0664),
    'Boa Vista': (2.8235, -60.6758),
    'Rio Branco': (-9.9749, -67.8243),
    'Porto Velho': (-8.7619, -63.9039),
    'Guarulhos': (-23.4538, -46.5333),
    'São Gonçalo': (-22.8268, -43.0537),
    'Duque de Caxias': (-22.7858, -43.3054),
    'Nova Iguaçu': (-22.7592, -43.4513),
    'São Bernardo do Campo': (-23.6914, -46.5646),
    'Osasco': (-23.5329, -46.7918),
    'Santo André': (-23.6540, -46.5391),
    'Jaboatão dos Guararapes': (-8.1129, -35.0148),
    'Contagem': (-19.9317, -44.0540)
}

# Mapeamento de estados para coordenadas (capitais)
COORDENADAS_ESTADOS = {
    'SP': (-23.5505, -46.6333),
    'RJ': (-22.9068, -43.1729),
    'MG': (-19.9167, -43.9345),
    'RS': (-30.0346, -51.2177),
    'SC': (-27.5954, -48.5480),
    'PR': (-25.4244, -49.2654),
    'BA': (-12.9714, -38.5014),
    'GO': (-16.6869, -49.2648),
    'DF': (-15.7801, -47.9292),
    'CE': (-3.7319, -38.5267),
    'PE': (-8.0476, -34.8770),
    'AM': (-3.1190, -60.0217),
    'PA': (-1.4558, -48.5044),
    'MA': (-2.5297, -44.3028),
    'PB': (-7.1195, -34.8450),
    'PI': (-5.0892, -42.8019),
    'RN': (-5.7945, -35.2110),
    'MS': (-20.4697, -54.6201),
    'MT': (-15.6014, -56.0979),
    'AL': (-9.6658, -35.7353),
    'ES': (-20.3155, -40.3128),
    'SE': (-10.9472, -37.0731),
    'TO': (-10.1689, -48.3317),
    'AP': (0.0389, -51.0664),
    'RR': (2.8235, -60.6758),
    'AC': (-9.9749, -67.8243),
    'RO': (-8.7619, -63.9039),
}

# Mapeamento de CEP para estados
CEP_PARA_ESTADO = {
    '01': 'SP', '02': 'SP', '03': 'SP', '04': 'SP', '05': 'SP',
    '06': 'SP', '07': 'SP', '08': 'SP', '09': 'SP', '10': 'SP',
    '11': 'SP', '12': 'SP', '13': 'SP', '14': 'SP', '15': 'SP',
    '16': 'SP', '17': 'SP', '18': 'SP', '19': 'SP',
    '20': 'RJ', '21': 'RJ', '22': 'RJ', '23': 'RJ', '24': 'RJ',
    '25': 'RJ', '26': 'RJ', '27': 'ES', '28': 'ES', '29': 'ES',
    '30': 'MG', '31': 'MG', '32': 'MG', '33': 'MG', '34': 'MG',
    '35': 'MG', '36': 'MG', '37': 'MG', '38': 'MG', '39': 'MG',
    '40': 'BA', '41': 'BA', '42': 'BA', '43': 'BA', '44': 'BA',
    '45': 'BA', '46': 'BA', '47': 'BA', '48': 'BA',
    '49': 'MG', '50': 'PE', '51': 'PE', '52': 'PE', '53': 'PE',
    '54': 'PE', '55': 'PE', '56': 'PE', '57': 'AL', '58': 'PB',
    '59': 'RN', '60': 'CE', '61': 'CE', '62': 'CE', '63': 'CE',
    '64': 'PI', '65': 'MT', '66': 'MT', '67': 'MT', '68': 'AC',
    '69': 'RO', '70': 'DF', '71': 'DF', '72': 'GO', '73': 'GO',
    '74': 'GO', '75': 'GO', '76': 'GO', '77': 'TO', '78': 'MT',
    '79': 'MS', '80': 'PR', '81': 'PR', '82': 'PR', '83': 'PR',
    '84': 'PR', '85': 'PR', '86': 'PR', '87': 'PR', '88': 'SC',
    '89': 'SC', '90': 'RS', '91': 'RS', '92': 'RS', '93': 'RS',
    '94': 'RS', '95': 'RS', '96': 'RS', '97': 'RS', '98': 'RS',
    '99': 'RS'
}

# APIs de CEP para fallback
CEP_APIS = [
    'https://viacep.com.br/ws/{}/json/',
    'https://brasilapi.com.br/api/cep/v1/{}',
    'https://cep.awesomeapi.com.br/json/{}'
]

def normalizar_texto(texto):
    """Remove acentos e normaliza texto para comparação"""
    if not texto:
        return ""
    # Remove acentos
    texto_normalizado = unicodedata.normalize('NFD', texto)
    texto_sem_acento = texto_normalizado.encode('ascii', 'ignore').decode('ascii')
    return texto_sem_acento.lower().strip()

def buscar_coordenadas_por_nome(nome_cidade):
    """Busca coordenadas por nome da cidade com algoritmo robusto"""
    if not nome_cidade:
        return None
    
    # Debug
    st.info(f"🔍 Buscando coordenadas para: '{nome_cidade}'")
    
    # Normaliza o nome de entrada
    nome_normalizado = normalizar_texto(nome_cidade)
    
    # 1. Busca exata primeiro
    for cidade, coords in COORDENADAS_CIDADES.items():
        if nome_cidade.strip() == cidade.strip():
            st.success(f"✅ Encontrou cidade exata: {cidade}")
            return coords
    
    # 2. Busca sem acentos
    for cidade, coords in COORDENADAS_CIDADES.items():
        if nome_normalizado == normalizar_texto(cidade):
            st.success(f"✅ Encontrou cidade (sem acentos): {cidade}")
            return coords
    
    # 3. Busca por substring
    for cidade, coords in COORDENADAS_CIDADES.items():
        if nome_normalizado in normalizar_texto(cidade):
            st.success(f"✅ Encontrou cidade (substring): {cidade}")
            return coords
    
    # 4. Busca reversa (nome contido na cidade)
    for cidade, coords in COORDENADAS_CIDADES.items():
        if normalizar_texto(cidade) in nome_normalizado:
            st.success(f"✅ Encontrou cidade (reversa): {cidade}")
            return coords
    
    # Se não encontrou, retorna None
    st.warning(f"⚠️ Cidade '{nome_cidade}' não encontrada")
    return None

def test_connectivity():
    """Testa conectividade básica"""
    test_urls = [
        "https://httpbin.org/status/200",
        "https://www.google.com",
        "https://api.github.com"
    ]
    
    working_urls = []
    for url in test_urls:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                working_urls.append(url)
        except:
            continue
    
    return len(working_urls) > 0, working_urls

def safe_request(url, timeout=10, max_retries=2):
    """Faz requisição HTTP com tratamento de erro"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=timeout, headers=headers)
            response.raise_for_status()
            return response
        except requests.exceptions.SSLError:
            try:
                response = requests.get(url, timeout=timeout, headers=headers, verify=False)
                response.raise_for_status()
                return response
            except:
                continue
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                st.warning(f"🔄 Tentativa {attempt + 1} falhou. Tentando novamente...")
                time.sleep(2)
                continue
            else:
                st.error(f"🔌 Erro de conexão após {max_retries} tentativas")
                return None
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                st.warning(f"⏱️ Timeout na tentativa {attempt + 1}. Tentando novamente...")
                time.sleep(1)
                continue
            else:
                st.error(f"⏱️ Timeout após {max_retries} tentativas")
                return None
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Erro na requisição: {str(e)}")
            return None
    return None

def get_api_keys():
    """Obtém as chaves da API de forma segura"""
    openai_key = None
    weather_key = None
    
    try:
        openai_key = st.secrets["OPENAI_API_KEY"]
    except:
        openai_key = os.environ.get("OPENAI_API_KEY")
    
    try:
        weather_key = st.secrets["WEATHER_API_KEY"]
    except:
        weather_key = os.environ.get("WEATHER_API_KEY")
    
    return openai_key, weather_key

def validate_cep(cep):
    """Valida formato do CEP"""
    if not cep:
        return None
    cep_clean = re.sub(r'\D', '', cep)
    if len(cep_clean) == 8:
        return cep_clean
    return None

def formatar_endereco(endereco_info):
    """Formata o endereço de forma elegante"""
    if not endereco_info:
        return ""
    
    endereco_parts = []
    
    if endereco_info.get('rua'):
        endereco_parts.append(endereco_info['rua'])
    
    if endereco_info.get('bairro'):
        endereco_parts.append(endereco_info['bairro'])
    
    cidade_uf = []
    if endereco_info.get('cidade'):
        cidade_uf.append(endereco_info['cidade'])
    if endereco_info.get('uf'):
        cidade_uf.append(endereco_info['uf'])
    
    if cidade_uf:
        endereco_parts.append(" - ".join(cidade_uf))
    
    if endereco_info.get('cep'):
        cep_formatado = endereco_info['cep']
        if len(cep_formatado) == 8:
            cep_formatado = f"{cep_formatado[:5]}-{cep_formatado[5:]}"
        endereco_parts.append(f"CEP: {cep_formatado}")
    
    return " | ".join(endereco_parts)

def buscar_cep_completo(cep):
    """Busca dados completos do CEP usando múltiplas APIs"""
    cep_clean = validate_cep(cep)
    if not cep_clean:
        return None, None, None, "CEP inválido. Use formato: 12345678"
    
    # Tenta cada API de CEP
    for i, api_url in enumerate(CEP_APIS):
        try:
            url = api_url.format(cep_clean)
            st.info(f"🔍 Tentando API {i+1}/3: {url.split('/')[2]}")
            
            response = safe_request(url)
            if not response:
                continue
            
            data = response.json()
            endereco_info = {}
            
            # Processa resposta da ViaCEP
            if 'viacep' in url:
                if "erro" in data:
                    st.warning(f"⚠️ API {i+1}: CEP não encontrado")
                    continue
                endereco_info = {
                    'rua': data.get("logradouro", ""),
                    'bairro': data.get("bairro", ""),
                    'cidade': data.get("localidade", ""),
                    'uf': data.get("uf", ""),
                    'cep': data.get("cep", ""),
                    'complemento': data.get("complemento", ""),
                    'ddd': data.get("ddd", "")
                }
            
            # Processa resposta da BrasilAPI
            elif 'brasilapi' in url:
                if not data.get("city"):
                    st.warning(f"⚠️ API {i+1}: Dados incompletos")
                    continue
                endereco_info = {
                    'rua': data.get("street", ""),
                    'bairro': data.get("neighborhood", ""),
                    'cidade': data.get("city", ""),
                    'uf': data.get("state", ""),
                    'cep': cep_clean,
                    'complemento': "",
                    'ddd': ""
                }
            
            # Processa resposta da AwesomeAPI
            elif 'awesomeapi' in url:
                if data.get("status") == 400:
                    st.warning(f"⚠️ API {i+1}: CEP inválido")
                    continue
                endereco_info = {
                    'rua': data.get("address", ""),
                    'bairro': data.get("district", ""),
                    'cidade': data.get("city", ""),
                    'uf': data.get("state", ""),
                    'cep': cep_clean,
                    'complemento': "",
                    'ddd': data.get("ddd", "")
                }
            
            # Verifica se temos dados mínimos
            if not endereco_info.get('cidade') or not endereco_info.get('uf'):
                st.warning(f"⚠️ API {i+1}: Dados incompletos (cidade/UF)")
                continue
            
            # Sucesso! Busca coordenadas
            st.success(f"✅ API {i+1} funcionou! Dados obtidos com sucesso.")
            
            # Busca coordenadas usando a função robusta
            coordenadas = buscar_coordenadas_por_nome(endereco_info['cidade'])
            
            if coordenadas:
                return coordenadas[0], coordenadas[1], endereco_info, None
            else:
                # Fallback por estado
                uf = endereco_info.get('uf', '')
                if uf in COORDENADAS_ESTADOS:
                    coords = COORDENADAS_ESTADOS[uf]
                    st.warning(f"⚠️ Usando coordenadas da capital do estado {uf}")
                    return coords[0], coords[1], endereco_info, None
                else:
                    st.warning(f"⚠️ Coordenadas não encontradas para {endereco_info['cidade']}")
                    continue
                    
        except json.JSONDecodeError:
            st.warning(f"⚠️ API {i+1}: Erro ao processar resposta JSON")
            continue
        except Exception as e:
            st.warning(f"⚠️ API {i+1} falhou: {str(e)}")
            continue
    
    # Se chegou aqui, nenhuma API funcionou - fallback por região do CEP
    if len(cep_clean) >= 2:
        prefixo_cep = cep_clean[:2]
        if prefixo_cep in CEP_PARA_ESTADO:
            uf = CEP_PARA_ESTADO[prefixo_cep]
            coords = COORDENADAS_ESTADOS.get(uf)
            if coords:
                endereco_fallback = {
                    'rua': f"Região do CEP {cep_clean[:5]}-{cep_clean[5:]}",
                    'bairro': "Região aproximada",
                    'cidade': "Localização aproximada",
                    'uf': uf,
                    'cep': cep_clean,
                    'complemento': "Dados aproximados",
                    'ddd': ""
                }
                st.warning(f"⚠️ Usando localização aproximada baseada no CEP (Estado: {uf})")
                return coords[0], coords[1], endereco_fallback, None
    
    return None, None, None, "Não foi possível obter coordenadas do CEP usando nenhuma API"

def get_weather_fallback(latitude, longitude):
    """Obtém dados do clima usando múltiplas APIs"""
    weather_key = get_api_keys()[1]
    
    if weather_key:
        try:
            url = f"http://api.weatherapi.com/v1/current.json?key={weather_key}&q={latitude},{longitude}&aqi=no"
            response = safe_request(url)
            
            if response:
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
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "fallback": False
                    }
        except Exception as e:
            st.warning(f"⚠️ WeatherAPI falhou: {str(e)}")
    
    # Fallback com dados baseados em coordenadas
    weather_fallback = {
        "temperatura": 23.5,
        "umidade": 65,
        "vento_kmh": 15.2,
        "descricao": "Parcialmente nublado",
        "cidade": f"Lat: {latitude:.2f}, Lon: {longitude:.2f}",
        "pais": "Brasil",
        "sensacao": 25.0,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "fallback": True
    }
    
    # Estimativa baseada em latitude
    if latitude < -30:
        weather_fallback.update({"temperatura": 18.0, "descricao": "Clima temperado"})
    elif latitude < -15:
        weather_fallback.update({"temperatura": 24.0, "descricao": "Clima tropical"})
    else:
        weather_fallback.update({"temperatura": 28.0, "descricao": "Clima quente"})
    
    return weather_fallback

def interpretar_clima(weather_data):
    """Gera recomendações usando OpenAI com fallback"""
    openai_key = get_api_keys()[0]
    
    # Fallback com recomendações baseadas em regras
    def recomendacoes_fallback(temp, umidade, vento, descricao):
        recomendacoes = f"""
## 🧥 ROUPAS RECOMENDADAS

**Para {temp}°C:**
"""
        
        if temp < 15:
            recomendacoes += """
- Casaco pesado ou jaqueta
- Calça comprida
- Sapatos fechados
- Cachecol e gorro se necessário
"""
        elif temp < 22:
            recomendacoes += """
- Casaco leve ou blusa de manga longa
- Calça ou bermuda
- Sapatos fechados ou tênis
"""
        elif temp < 28:
            recomendacoes += """
- Camiseta ou blusa leve
- Shorts ou calça leve
- Sapatos abertos ou tênis
"""
        else:
            recomendacoes += """
- Roupas leves e claras
- Shorts e camiseta
- Sandálias ou sapatos ventilados
- Protetor solar
"""
        
        recomendacoes += f"""

## 🏠 AR-CONDICIONADO RESIDENCIAL
- Temperatura recomendada: **{max(18, min(26, temp - 2))}°C**
- Umidade atual: {umidade}% {"(ideal: 50-60%)" if umidade < 50 or umidade > 60 else "(ideal)"}

## 🚗 AR-CONDICIONADO AUTOMOTIVO
- Temperatura recomendada: **{max(18, min(24, temp - 3))}°C**
- Use ar externo se a temperatura externa for agradável
- Recirculação interno se muito quente ou frio

## 👶 CUIDADOS COM BEBÊS
- Vista o bebê com uma camada a mais que você usaria
- AC para bebês: **{max(20, min(24, temp - 1))}°C**
- Mantenha umidade entre 40-60%
- Evite correntes de ar diretas
"""
        
        return recomendacoes
    
    # Tenta usar OpenAI
    if openai_key:
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
            st.warning(f"⚠️ OpenAI API falhou: {str(e)}. Usando recomendações baseadas em regras.")
    
    # Fallback para recomendações baseadas em regras
    return recomendacoes_fallback(
        weather_data['temperatura'],
        weather_data['umidade'],
        weather_data['vento_kmh'],
        weather_data['descricao']
    )

def main():
    # Header principal
    st.markdown("""
    <div class="main-header">
        <h1>🌡️ Smart Clima</h1>
        <p>Assistente Inteligente de Conforto Térmico</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar com diagnósticos
    with st.sidebar:
        st.markdown("### 🔧 Diagnósticos do Sistema")
        
        # Teste de conectividade
        with st.expander("🔌 Teste de Conectividade"):
            if st.button("Testar Conexão"):
                is_connected, working_urls = test_connectivity()
                if is_connected:
                    st.success(f"✅ Conectado! URLs funcionando: {len(working_urls)}")
                else:
                    st.error("❌ Sem conexão com a internet")
        
        # Status das APIs
        st.markdown("### 📊 Status das APIs")
        openai_key, weather_key = get_api_keys()
        st.markdown(f"**OpenAI:** {'✅ Configurada' if openai_key else '❌ Não configurada'}")
        st.markdown(f"**Weather:** {'✅ Configurada' if weather_key else '❌ Não configurada'}")
        
        if not openai_key:
            st.warning("⚠️ OpenAI não configurada. Usando recomendações baseadas em regras.")
        
        if not weather_key:
            st.warning("⚠️ Weather API não configurada. Usando dados estimados.")
        
        # Informações sobre cidades disponíveis
        st.markdown("### 🏙️ Cidades Disponíveis")
        st.markdown(f"**Total:** {len(COORDENADAS_CIDADES)} cidades")
        st.markdown("**Todas funcionam offline!**")
    
    # Seção de entrada
    st.markdown('<div class="input-section">', unsafe_allow_html=True)
    st.markdown("### 📍 Informe sua localização")
    
    # Tabs para diferentes tipos de entrada
    tab1, tab2, tab3 = st.tabs(["🏠 Por CEP", "🌐 Por Coordenadas", "🏙️ Por Cidade"])
    
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
            if st.button("📋 Usar coordenadas exemplo", key="example_coords"):
                st.session_state.lat_input = "-23.550520"
                st.session_state.lon_input = "-46.633308"
                st.rerun()
    
    with tab3:
        st.markdown("**Selecione uma cidade:**")
        cidades_disponiveis = list(COORDENADAS_CIDADES.keys())
        cidades_disponiveis.sort()  # Ordena alfabeticamente
        
        cidade = st.selectbox("Cidade", cidades_disponiveis, key="cidade_select")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            search_cidade = st.button("🔍 Buscar", key="search_cidade", type="primary")
        with col2:
            st.markdown("*Todas as cidades funcionam offline*")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Processamento CEP
    if search_cep and cep:
        with st.spinner("🔍 Buscando localização via CEP..."):
            lat, lon, endereco_info, error = buscar_cep_completo(cep)
            
            if error:
                st.markdown(f'<div class="error-message">❌ {error}</div>', unsafe_allow_html=True)
                st.markdown("""
                <div class="fallback-section">
                    <h4>💡 Alternativas:</h4>
                    <ul>
                        <li>Tente usar coordenadas diretamente</li>
                        <li>Selecione uma cidade próxima na aba "Por Cidade"</li>
                        <li>Verifique se o CEP está correto</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Exibe o endereço encontrado
                if endereco_info:
                    endereco_formatado = formatar_endereco(endereco_info)
                    st.markdown(f"""
                    <div class="success-message">
                        <h4>✅ Endereço encontrado:</h4>
                        <p><strong>{endereco_formatado}</strong></p>
                        <p>Coordenadas: {lat}, {lon}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="success-message">✅ Coordenadas encontradas: {lat}, {lon}</div>', unsafe_allow_html=True)
                
                with st.spinner("🌤️ Obtendo dados do clima..."):
                    clima = get_weather_fallback(lat, lon)
                    
                    # Adiciona informações do endereço ao clima
                    if endereco_info:
                        clima["endereco"] = endereco_info
                        clima["endereco_formatado"] = endereco_formatado
                        # Usa o nome da cidade do CEP se disponível
                        if endereco_info.get('cidade'):
                            clima["cidade"] = endereco_info['cidade']
                    
                    st.session_state.clima = clima
                    st.session_state.coordenadas = (lat, lon)
                    st.rerun()
    
    # Processamento coordenadas
    if search_coords and latitude and longitude:
        try:
            lat = float(latitude)
            lon = float(longitude)
            
            # Validação básica das coordenadas
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                st.error("❌ Coordenadas inválidas. Latitude: -90 a 90, Longitude: -180 a 180")
            else:
                with st.spinner("🌤️ Obtendo dados do clima..."):
                    clima = get_weather_fallback(lat, lon)
                    st.session_state.clima = clima
                    st.session_state.coordenadas = (lat, lon)
                    st.rerun()
        except ValueError:
            st.markdown('<div class="error-message">❌ Coordenadas inválidas. Use formato numérico.</div>', unsafe_allow_html=True)
    
    # Processamento cidade
    if search_cidade and cidade:
        try:
            st.info(f"🔍 Buscando coordenadas para: {cidade}")
            
            # Busca coordenadas usando a função robusta
            coordenadas = buscar_coordenadas_por_nome(cidade)
            
            if coordenadas:
                lat, lon = coordenadas
                
                with st.spinner("🌤️ Obtendo dados do clima..."):
                    clima = get_weather_fallback(lat, lon)
                    clima["cidade"] = cidade  # Usa o nome selecionado
                    st.session_state.clima = clima
                    st.session_state.coordenadas = (lat, lon)
                    st.rerun()
            else:
                st.error(f"❌ Não foi possível encontrar coordenadas para {cidade}")
                st.info("💡 Isso não deveria acontecer. Verifique se a cidade está na lista.")
                
        except Exception as e:
            st.error(f"❌ Erro ao buscar cidade: {str(e)}")
            # Fallback: usar São Paulo
            st.warning("🔄 Usando São Paulo como fallback")
            lat, lon = -23.5505, -46.6333
            clima = get_weather_fallback(lat, lon)
            clima["cidade"] = "São Paulo (fallback)"
            st.session_state.clima = clima
            st.session_state.coordenadas = (lat, lon)
            st.rerun()
    
    # Exibição dos dados do clima
    if 'clima' in st.session_state:
        clima = st.session_state.clima
        
        # Aviso se usando dados de fallback
        if clima.get("fallback", False):
            st.markdown("""
            <div class="diagnostic-card">
                <h4>⚠️ Modo Offline</h4>
                <p>Usando dados estimados baseados na localização. Para dados precisos, verifique sua conexão e configure as APIs.</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Card do clima com endereço
        clima_header = f"🌤️ Clima em {clima['cidade']}, {clima['pais']}"
        
        # Se tiver endereço do CEP, exibe informações mais detalhadas
        if clima.get('endereco'):
            endereco_info = clima['endereco']
            
            st.markdown(f"""
            <div class="weather-card">
                <h2>{clima_header}</h2>
                <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                    <h4>📍 Endereço Completo:</h4>
                    <p><strong>{clima.get('endereco_formatado', '')}</strong></p>
                    {f"<p>🏠 <strong>Rua:</strong> {endereco_info.get('rua', 'Não disponível')}</p>" if endereco_info.get('rua') else ""}
                    {f"<p>🏘️ <strong>Bairro:</strong> {endereco_info.get('bairro', 'Não disponível')}</p>" if endereco_info.get('bairro') else ""}
                    {f"<p>📞 <strong>DDD:</strong> {endereco_info.get('ddd', 'Não disponível')}</p>" if endereco_info.get('ddd') else ""}
                </div>
                <p>Última atualização: {clima['timestamp']}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="weather-card">
                <h2>{clima_header}</h2>
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
            <p>Obtenha recomendações inteligentes baseadas no clima atual</p>
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
            with st.spinner("🤖 Gerando recomendações..."):
                recomendacoes = interpretar_clima(clima)
                st.session_state.recomendacoes = recomendacoes
                st.rerun()
        
        # Exibir recomendações
        if 'recomendacoes' in st.session_state:
            st.markdown("### 📋 Suas Recomendações")
            st.markdown(st.session_state.recomendacoes)
            
            # Botão para salvar recomendações
            endereco_completo = ""
            if clima.get('endereco_formatado'):
                endereco_completo = f"**Endereço:** {clima['endereco_formatado']}\n"
            
            st.download_button(
                label="💾 Salvar Recomendações",
                data=f"# Recomendações Smart Clima\n\n**Local:** {clima['cidade']}, {clima['pais']}\n{endereco_completo}**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n**Temperatura:** {clima['temperatura']}°C\n**Modo:** {'Offline' if clima.get('fallback', False) else 'Online'}\n\n{st.session_state.recomendacoes}",
                file_name=f"recomendacoes_clima_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown"
            )
            
            # Feedback do usuário
            st.markdown("---")
            st.markdown("### 📝 Feedback")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("👍 Útil"):
                    st.success("Obrigado pelo feedback!")
            with col2:
                if st.button("👎 Não útil"):
                    st.info("Obrigado! Vamos melhorar.")
            with col3:
                if st.button("🔄 Gerar Novamente"):
                    del st.session_state.recomendacoes
                    st.rerun()
    
    # Seção de ajuda
    if not st.session_state.get('clima'):
        st.markdown("---")
        st.markdown("### 🆘 Problemas de Conexão?")
        
        with st.expander("🔧 Soluções para Problemas Comuns"):
            st.markdown("""
            **Se não conseguir conectar:**
            
            1. **Verifique sua internet** - Teste acessando outros sites
            2. **Use coordenadas** - Mais confiável que CEP
            3. **Selecione uma cidade** - Funciona offline
            4. **Aguarde um momento** - Algumas redes são mais lentas
            
            **APIs não configuradas:**
            - OpenAI: Configure `OPENAI_API_KEY` para recomendações avançadas
            - Weather: Configure `WEATHER_API_KEY` para dados precisos
            
            **Mesmo sem APIs, o app funciona com:**
            - Dados climáticos estimados
            - Recomendações baseadas em regras
            - Múltiplas cidades brasileiras
            """)
        
        st.markdown("### 🎯 Teste Rápido")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🏙️ Testar com São Paulo", type="primary"):
                clima = get_weather_fallback(-23.5505, -46.6333)
                clima["cidade"] = "São Paulo"
                st.session_state.clima = clima
                st.rerun()
        
        with col2:
            if st.button("🏖️ Testar com Rio de Janeiro", type="primary"):
                clima = get_weather_fallback(-22.9068, -43.1729)
                clima["cidade"] = "Rio de Janeiro"
                st.session_state.clima = clima
                st.rerun()
        
        # Mostrar cidades disponíveis
        st.markdown("### 🏙️ Cidades Disponíveis")
        with st.expander("Ver todas as cidades"):
            cidades_organizadas = {}
            for cidade in COORDENADAS_CIDADES.keys():
                primeira_letra = cidade[0].upper()
                if primeira_letra not in cidades_organizadas:
                    cidades_organizadas[primeira_letra] = []
                cidades_organizadas[primeira_letra].append(cidade)
            
            for letra in sorted(cidades_organizadas.keys()):
                st.markdown(f"**{letra}:** {', '.join(sorted(cidades_organizadas[letra]))}")

if __name__ == "__main__":
    main()
