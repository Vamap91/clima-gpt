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
                    'complemento': "Dados a
