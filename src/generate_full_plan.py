import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import openai
from dotenv import load_dotenv
from langchain.agents import Tool, AgentExecutor, LLMSingleActionAgent
from langchain_community.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import BaseChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from typing import List, Union, Dict
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from sklearn.linear_model import LinearRegression

# Carrega variáveis de ambiente
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def traduzir_dia(dia_en):
    """Traduz o nome do dia da semana de inglês para português"""
    traducao = {
        "Monday": "Segunda-feira",
        "Tuesday": "Terça-feira",
        "Wednesday": "Quarta-feira",
        "Thursday": "Quinta-feira",
        "Friday": "Sexta-feira",
        "Saturday": "Sábado",
        "Sunday": "Domingo"
    }
    return traducao.get(dia_en, dia_en)

def analisar_dados_garmin(arquivo_csv):
    """Analisa os dados do Garmin para extrair informações relevantes"""
    try:
        # Verifica se o arquivo existe
        if not os.path.exists(arquivo_csv):
            print(f"Erro: O arquivo '{arquivo_csv}' não foi encontrado.")
            return None
        
        # Carrega os dados
        df = pd.read_csv(arquivo_csv)
        print("Colunas disponíveis:", df.columns.tolist())
        
        # Verifica se as colunas necessárias existem
        colunas_necessarias = ['distancia_km', 'duracao_minutos', 'pace_min_km', 'averageHR', 'startTimeLocal']
        for coluna in colunas_necessarias:
            if coluna not in df.columns:
                print(f"Erro: Coluna '{coluna}' não encontrada no arquivo CSV.")
                return None
        
        # Converte colunas para numérico, tratando erros
        for coluna in ['distancia_km', 'duracao_minutos', 'pace_min_km', 'averageHR']:
            df[coluna] = pd.to_numeric(df[coluna], errors='coerce')
        
        # Converte coluna de data para datetime
        df['startTimeLocal'] = pd.to_datetime(df['startTimeLocal'], errors='coerce')
        
        # Calcula métricas com tratamento de erros
        media_distancia = df['distancia_km'].mean()
        max_distancia = df['distancia_km'].max()
        media_duracao = df['duracao_minutos'].mean()
        media_pace = df['pace_min_km'].mean()
        media_fc = df['averageHR'].mean()
        
        # Verifica se há pelo menos 2 registros para calcular a melhora do pace
        if len(df) > 1:
            melhora_pace = df['pace_min_km'].iloc[-1] - df['pace_min_km'].iloc[0]
        else:
            melhora_pace = 0
        
        # Calcula volume semanal médio
        df['semana'] = df['startTimeLocal'].dt.isocalendar().week
        volume_semanal = df.groupby('semana')['distancia_km'].sum().mean()
        
        # Formata período de dados
        data_min = df['startTimeLocal'].min()
        data_max = df['startTimeLocal'].max()
        periodo_dados = f"{data_min.strftime('%d/%m/%Y')} a {data_max.strftime('%d/%m/%Y')}"
        
        # Cria o resumo com valores convertidos para float
        resumo = {
            'media_distancia': float(media_distancia),
            'max_distancia': float(max_distancia),
            'media_duracao': float(media_duracao),
            'media_pace': float(media_pace),
            'melhora_pace': float(melhora_pace),
            'media_fc': float(media_fc),
            'total_atividades': len(df),
            'periodo_dados': periodo_dados,
            'volume_semanal': float(volume_semanal)
        }
        
        print("\nResumo dos dados calculado com sucesso!")
        return resumo
    except Exception as e:
        print(f"Erro ao analisar dados: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None

class AgenteGarminBase:
    def __init__(self, llm):
        self.llm = llm
        self.memory = ConversationBufferMemory()

class AgenteDados(AgenteGarminBase):
    def __init__(self, llm):
        super().__init__(llm)
        self.system_prompt = """Você é um especialista em análise de dados de corrida.
        Sua função é validar e processar dados do Garmin para garantir que estejam corretos.
        
        Você deve retornar APENAS um JSON válido com as métricas calculadas.
        """
    
    def validar_dados(self, df: pd.DataFrame) -> Dict:
        try:
            df['startTimeLocal'] = pd.to_datetime(df['startTimeLocal'])
            df = df.sort_values('startTimeLocal')
            
            # Filtra dados inválidos
            df['pace_min_km'] = pd.to_numeric(df['pace_min_km'], errors='coerce')
            df = df[df['pace_min_km'].between(4.0, 12.0)]
            
            # Usa resample para volume semanal
            volume_semanal = df.set_index('startTimeLocal').resample('W')['distancia_km'].sum().mean()
            
            metricas = {
                "max_distancia": float(df['distancia_km'].max()),
                "media_distancia": float(df.tail(30)['distancia_km'].mean()),
                "pace_medio": float(df.tail(30)['pace_min_km'].mean()),
                "fc_media": float(df['averageHR'].mean()),
                "volume_semanal": float(volume_semanal)
            }
            
            return metricas
            
        except Exception as e:
            print(f"Erro ao processar dados: {str(e)}")
            return None

    def _calcular_taxa_progresso(self, serie: pd.Series) -> float:
        """Calcula taxa de progresso semanal usando regressão linear"""
        if len(serie) < 2:
            return 0.0
        
        X = np.arange(len(serie)).reshape(-1, 1)
        y = serie.values.reshape(-1, 1)
        reg = LinearRegression().fit(X, y)
        
        # Converte coeficiente angular em taxa semanal
        taxa_semanal = (reg.coef_[0] * 7) / serie.mean()
        return taxa_semanal

class AgenteProgressao(AgenteGarminBase):
    def __init__(self, llm):
        super().__init__(llm)
        self.system_prompt = """Você é um especialista em periodização de treino.
        Sua função é criar uma progressão segura de treinos longos para meia maratona.
        
        Regras importantes:
        1. Treinos longos devem ser SEMPRE aos sábados
        2. Domingos são SEMPRE dias de descanso
        3. Aumento máximo de 10% na distância por semana
        4. Progressão deve ser gradual até 21km
        """
    
    def calcular_progressao(self, metricas: Dict) -> List[float]:
        prompt = f"""
        Com base nestas métricas:
        - Distância máxima atual: {metricas['max_distancia']} km
        - Pace médio: {metricas['pace_medio']} min/km
        - Volume semanal: {metricas['volume_semanal']} km
        
        Crie um plano de treinos longos para os próximos 9 SÁBADOS, considerando:
        1. Todos os treinos longos serão aos sábados
        2. Comece com {metricas['max_distancia']:.1f} km
        3. Aumente NO MÁXIMO 10% por semana
        4. NÃO ultrapasse 21km em NENHUMA hipótese
        5. O último treino DEVE ser exatamente 21km
        
        Retorne APENAS um array JSON com 9 números entre {metricas['max_distancia']:.1f} e 21.0
        
        Exemplo de formato esperado para progressão segura:
        [14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 19.5, 20.0, 21.0]
        """
        
        response = self.llm.predict(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            print("Erro ao decodificar JSON da resposta do LLM")
            return None

class AgenteTreinos(AgenteGarminBase):
    def __init__(self, llm):
        super().__init__(llm)
        self.system_prompt = """Você é um treinador especialista em corrida.
        Sua função é criar treinos específicos baseados no nível atual do corredor.
        
        Regras importantes:
        1. Treinos longos são SEMPRE aos sábados
        2. Domingos são SEMPRE dias de descanso
        3. SEMPRE especificar aquecimento e desaquecimento:
           - Treinos normais: 10 min aquecimento, 5 min desaquecimento
           - Treinos longos: 15 min aquecimento, 10 min desaquecimento
        
        Tipos de Treino:
        1. Base/Contínuo (terças ou quintas)
        2. Intervalado (terças ou quintas)
        3. Ritmo (quartas ou sextas)
        4. Longo (APENAS sábados)
        5. Fartlek (quartas ou sextas)
        """
    
    def gerar_treino(self, tipo: str, metricas: Dict, data: str = None, distancia: float = None) -> Dict:
        # Verifica se é semana de taper (26/05 a 01/06)
        is_taper = data and datetime.strptime(data, "%d/%m/%Y") >= datetime(2025, 5, 26)
        
        # Verifica se é treino de descanso
        if tipo == "Descanso":
            return {
                "tipo": "Descanso",
                "data": data if data else '',
                "justificativa": "Dia dedicado à recuperação muscular e mental"
            }
        
        # Define durações de aquecimento/desaquecimento
        is_longo = tipo == "Longo" or tipo == "MEIA MARATONA"
        aquec_duracao = 15 if is_longo else 10
        desaq_duracao = 10 if is_longo else 5
        
        # Calcula ritmo base (pace médio + ajuste baseado no tipo)
        ritmo_base = metricas['pace_medio']
        ajustes_ritmo = {
            "Base": 0,
            "Longo": 0.5,
            "Intervalado": -1.0,
            "Ritmo": -0.5,
            "Fartlek": -0.3,
            "MEIA MARATONA": -0.5
        }
        
        ritmo_treino = max(5.0, ritmo_base + ajustes_ritmo.get(tipo, 0))
        
        # Formata o ritmo em min:seg
        min_ritmo = int(ritmo_treino)
        seg_ritmo = int((ritmo_treino - min_ritmo) * 60)
        ritmo_formatado = f"{min_ritmo}:{seg_ritmo:02d}"
        
        treino = {
            "tipo": tipo,
            "data": data if data else '',
            "aquecimento": {
                "duracao": aquec_duracao,
                "ritmo": f"{min_ritmo + 1}:{seg_ritmo:02d}",
                "descricao": "Aquecimento progressivo com alongamentos dinâmicos"
            },
            "parte_principal": {
                "distancia": distancia if distancia else (3.0 if is_taper else 5.0),
                "duracao": 20 if is_taper else 40,
                "ritmo": ritmo_formatado,
                "zonas_fc": "Zona 2-3" if tipo in ["Base", "Longo"] else "Zona 3-4",
                "descricao": self._gerar_descricao_treino(tipo, is_taper)
            },
            "desaquecimento": {
                "duracao": desaq_duracao,
                "ritmo": f"{min_ritmo + 1}:{seg_ritmo:02d}",
                "descricao": "Desaquecimento gradual com redução do ritmo"
            },
            "dicas": self._gerar_dicas_treino(tipo, is_taper)
        }
        
        return treino

    def _gerar_descricao_treino(self, tipo: str, is_taper: bool) -> str:
        descricoes = {
            "Base": "Corrida contínua em ritmo moderado para desenvolver resistência aeróbica",
            "Longo": "Treino longo para desenvolver resistência e adaptação à distância",
            "Intervalado": "Treino intervalado para melhorar velocidade e VO2max",
            "Ritmo": "Treino no ritmo-alvo da prova para desenvolver pace",
            "Fartlek": "Variações de ritmo para desenvolver diferentes sistemas energéticos",
            "MEIA MARATONA": "Prova de meia maratona - 21.1km"
        }
        
        desc = descricoes.get(tipo, "Treino base")
        if is_taper:
            desc += " (Volume reduzido - Semana de Taper)"
        return desc

    def _gerar_dicas_treino(self, tipo: str, is_taper: bool) -> str:
        dicas = {
            "Base": "Mantenha respiração controlada e ritmo constante",
            "Longo": "Hidrate-se a cada 20-30 minutos, considere levar gel energético",
            "Intervalado": "Foque na qualidade dos tiros, recupere bem entre as séries",
            "Ritmo": "Mantenha o ritmo constante, controle a respiração",
            "Fartlek": "Alterne os ritmos de forma progressiva, sem explosões",
            "MEIA MARATONA": "Siga sua estratégia de prova, hidratação e alimentação"
        }
        
        dica = dicas.get(tipo, "Mantenha ritmo constante")
        if is_taper:
            dica += ". Reduza volume mas mantenha qualidade"
        return dica

    def _calcular_ritmo_treino(self, tipo: str, metricas: Dict) -> str:
        """Calcula e formata o ritmo do treino"""
        pace_base = metricas.get('pace_medio', 7.0)
        
        ajustes = {
            "Base": 1.05,  # 5% mais lento
            "Longo": 1.10,  # 10% mais lento
            "Intervalado": 0.85,  # 15% mais rápido
            "Ritmo": 0.95,  # 5% mais rápido
            "Fartlek": 0.90,  # 10% mais rápido
            "MEIA MARATONA": 0.95  # 5% mais rápido
        }
        
        ritmo = pace_base * ajustes.get(tipo, 1.0)
        minutos = int(ritmo)
        segundos = int((ritmo - minutos) * 60)
        
        return f"{minutos}:{segundos:02d}"

class AgenteValidador(AgenteGarminBase):
    def __init__(self, llm):
        super().__init__(llm)
        self.system_prompt = """Você é um especialista em validação de planos de treino.
        Sua função é verificar inconsistências e garantir que o plano seja coerente.
        
        Regras de Validação:
        1. Verificar se Distância = Ritmo × Tempo
        2. Treinos longos APENAS aos sábados
        3. Domingos SEMPRE descanso
        4. Progressão gradual das distâncias
        5. Distribuição adequada dos tipos de treino na semana
        """
    
    def validar_treino(self, treino: Dict) -> Dict:
        try:
            if treino['tipo'] == "Descanso":
                return treino
            
            # Validar distância total (incluindo aquecimento/desaquecimento)
            if 'parte_principal' in treino:
                ritmo = self.converter_ritmo(treino['parte_principal']['ritmo'])
                tempo = treino['parte_principal']['duracao']
                distancia_calculada = tempo / ritmo
                
                if abs(distancia_calculada - treino['parte_principal']['distancia']) > 0.5:
                    treino['parte_principal']['duracao'] = int(treino['parte_principal']['distancia'] * ritmo)
            
            return treino
            
        except Exception as e:
            print(f"Erro na validação: {str(e)}")
            return self.criar_treino_padrao()
    
    def criar_treino_padrao(self) -> Dict:
        """Cria um treino padrão em caso de erro"""
        return {
            "tipo": "Base",
            "aquecimento": {
                "duracao": 10,
                "ritmo": "8:00",
                "descricao": "Aquecimento leve"
            },
            "parte_principal": {
                "distancia": 5.0,
                "duracao": 30,
                "ritmo": "7:00",
                "zonas_fc": "Zona 2",
                "descricao": "Corrida em ritmo constante"
            },
            "desaquecimento": {
                "duracao": 5,
                "ritmo": "8:00",
                "descricao": "Desaquecimento suave"
            },
            "dicas": "Mantenha um ritmo confortável"
        }
    
    def validar_plano_completo(self, plano: Dict) -> Dict:
        try:
            treinos_validados = []
            for treino in plano['treinos']:
                # Validar dia da semana
                if treino['tipo'] == 'Longo' and treino.get('dia_semana') != 'Sábado':
                    print(f"⚠️ Treino longo deve ser no sábado")
                    treino['dia_semana'] = 'Sábado'
                
                if treino.get('dia_semana') == 'Domingo' and treino['tipo'] != 'Descanso':
                    print(f"⚠️ Domingo deve ser dia de descanso")
                    treino['tipo'] = 'Descanso'
                
                # Validar progressão das distâncias
                if len(treinos_validados) > 0 and treino['tipo'] == 'Longo':
                    ultimo_longo = next((t for t in reversed(treinos_validados) 
                                      if t['tipo'] == 'Longo'), None)
                    if ultimo_longo:
                        aumento = (treino['parte_principal']['distancia'] - 
                                 ultimo_longo['parte_principal']['distancia'])
                        if aumento > ultimo_longo['parte_principal']['distancia'] * 0.1:
                            print(f"⚠️ Aumento muito grande na distância")
                            treino['parte_principal']['distancia'] = (
                                ultimo_longo['parte_principal']['distancia'] * 1.1
                            )
                
                treino = self.validar_treino(treino)
                treinos_validados.append(treino)
            
            plano['treinos'] = treinos_validados
            return plano
            
        except Exception as e:
            print(f"Erro na validação do plano: {str(e)}")
            return plano
    
    def converter_ritmo(self, ritmo: str) -> float:
        """Converte ritmo de string (min:seg/km) para float (min/km)"""
        try:
            if '-' in ritmo:
                ritmos = ritmo.split('-')
                return sum(self.converter_ritmo(r) for r in ritmos) / len(ritmos)
            
            minutos, segundos = ritmo.replace('min/km', '').strip().split(':')
            return float(minutos) + float(segundos)/60
        except:
            return 7.0  # Ritmo padrão em caso de erro

class AgentePlanoCompleto:
    def __init__(self):
        self.llm = ChatOpenAI(temperature=0.7)
        self.agente_dados = AgenteDados(self.llm)
        self.agente_progressao = AgenteProgressao(self.llm)
        self.agente_treinos = AgenteTreinos(self.llm)
        self.agente_validador = AgenteValidador(self.llm)
    
    def gerar_plano(self, arquivo_csv: str) -> str:
        try:
            print("🔍 Validando dados do Garmin...")
            df = pd.read_csv(arquivo_csv)
            metricas = self.agente_dados.validar_dados(df)
            
            if metricas is None:
                raise ValueError("Falha ao validar dados do Garmin")
            
            print("📅 Gerando calendário de treinos...")
            datas_treino = self.gerar_datas_treino()
            
            print("🏃 Gerando treinos específicos...")
            plano = {
                "metricas_base": metricas,
                "treinos": []
            }
            
            for data in datas_treino:
                treino = self.agente_treinos.gerar_treino(
                    tipo=data['tipo'], 
                    metricas=metricas,
                    data=data['data'],
                    distancia=data.get('distancia')
                )
                
                if treino:
                    treino['data'] = data['data']
                    treino['dia_semana'] = data['dia']
                    plano["treinos"].append(treino)
            
            print("🔍 Validando plano completo...")
            plano = self.agente_validador.validar_plano_completo(plano)
            
            return self.formatar_plano_final(plano)
            
        except Exception as e:
            print(f"❌ Erro ao gerar plano: {str(e)}")
            return None
    
    def formatar_plano_final(self, plano: Dict) -> str:
        # Formata o plano em markdown com detalhes de aquecimento/desaquecimento
        treinos_formatados = []
        for treino in plano['treinos']:
            treinos_formatados.append(f"""
            **{treino['tipo']}**
            
            1. Aquecimento:
               - Duração: {treino['aquecimento']['duracao']} minutos
               - Ritmo: {treino['aquecimento']['ritmo']}
               - Como fazer: {treino['aquecimento']['descricao']}
            
            2. Parte Principal:
               - Distância: {treino['parte_principal']['distancia']} km
               - Duração: {treino['parte_principal']['duracao']} minutos
               - Ritmo Alvo: {treino['parte_principal']['ritmo']}
               - Zonas FC: {treino['parte_principal']['zonas_fc']}
               - Descrição: {treino['parte_principal']['descricao']}
            
            3. Desaquecimento:
               - Duração: {treino['desaquecimento']['duracao']} minutos
               - Ritmo: {treino['desaquecimento']['ritmo']}
               - Como fazer: {treino['desaquecimento']['descricao']}
            
            Dicas: {treino['dicas']}
            """)
        
        return f"""# PLANO DE TREINAMENTO PARA MEIA MARATONA
        
        ## Métricas Base
        - Média de distância: {plano['metricas_base']['media_distancia']:.2f} km
        - Distância máxima: {plano['metricas_base']['max_distancia']:.2f} km
        - Volume semanal: {plano['metricas_base']['volume_semanal']:.2f} km
        - Pace médio: {plano['metricas_base']['pace_medio']:.2f} min/km
        - FC média: {plano['metricas_base']['fc_media']:.0f} bpm
        
        ## Treinos Detalhados
        {''.join(treinos_formatados)}
        
        ## Observações Importantes
        1. Treinos longos são SEMPRE aos sábados
        2. Domingos são SEMPRE dias de descanso
        3. Mantenha-se hidratado durante os treinos
        4. Faça os aquecimentos e desaquecimentos conforme indicado
        5. Ajuste os ritmos conforme sua percepção de esforço
        """

    def gerar_datas_treino(self) -> List[Dict]:
        """Gera as datas dos treinos até a meia maratona em 01/06"""
        return [
            # Semana 1
            {"data": "13/04/2025", "dia": "Sábado", "tipo": "Longo", "distancia": 14.0},
            {"data": "16/04/2025", "dia": "Terça", "tipo": "Intervalado"},
            {"data": "18/04/2025", "dia": "Quinta", "tipo": "Fartlek"},
            
            # Semana 2
            {"data": "20/04/2025", "dia": "Sábado", "tipo": "Longo", "distancia": 15.4},
            {"data": "23/04/2025", "dia": "Terça", "tipo": "Base"},
            {"data": "25/04/2025", "dia": "Quinta", "tipo": "Ritmo"},
            
            # Semana 3
            {"data": "27/04/2025", "dia": "Sábado", "tipo": "Longo", "distancia": 16.8},
            {"data": "30/04/2025", "dia": "Terça", "tipo": "Intervalado"},
            {"data": "02/05/2025", "dia": "Quinta", "tipo": "Fartlek"},
            
            # Semana 4
            {"data": "04/05/2025", "dia": "Sábado", "tipo": "Longo", "distancia": 18.0},
            {"data": "07/05/2025", "dia": "Terça", "tipo": "Base"},
            {"data": "09/05/2025", "dia": "Quinta", "tipo": "Ritmo"},
            
            # Semana 5
            {"data": "11/05/2025", "dia": "Sábado", "tipo": "Longo", "distancia": 19.0},
            {"data": "14/05/2025", "dia": "Terça", "tipo": "Intervalado"},
            {"data": "16/05/2025", "dia": "Quinta", "tipo": "Fartlek"},
            
            # Semana 6
            {"data": "18/05/2025", "dia": "Sábado", "tipo": "Longo", "distancia": 19.5},
            {"data": "21/05/2025", "dia": "Terça", "tipo": "Base"},
            {"data": "23/05/2025", "dia": "Quinta", "tipo": "Ritmo"},
            
            # Semana 7 (Taper)
            {"data": "25/05/2025", "dia": "Sábado", "tipo": "Longo", "distancia": 15.0},
            {"data": "28/05/2025", "dia": "Terça", "tipo": "Ritmo Leve"},
            {"data": "30/05/2025", "dia": "Quinta", "tipo": "Trote Suave"},
            
            # Dia da Prova
            {"data": "01/06/2025", "dia": "Domingo", "tipo": "MEIA MARATONA", "distancia": 21.1}
        ]

# Uso
if __name__ == "__main__":
    gerador = AgentePlanoCompleto()
    plano = gerador.gerar_plano("../atividades_garmin.csv")
    if plano:
        print(plano) 