from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
    GarminConnectAuthenticationError
)
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import os
import numpy as np

# Carrega as variáveis de ambiente
load_dotenv()

class GarminConnection:
    def __init__(self, email=None, password=None):
        self.email = email or os.getenv("GARMIN_EMAIL")
        self.password = password or os.getenv("GARMIN_PASSWORD")
        self.client = None
        
    def conectar(self):
        """Conecta à API do Garmin Connect"""
        try:
            self.client = Garmin(self.email, self.password)
            self.client.login()
            print("✅ Conectado ao Garmin Connect!")
            return True
            
        except GarminConnectAuthenticationError:
            print("❌ Erro de autenticação. Verifique email e senha.")
            return False
        except GarminConnectTooManyRequestsError:
            print("❌ Muitas requisições. Tente novamente mais tarde.")
            return False
        except Exception as e:
            print(f"❌ Erro ao conectar: {str(e)}")
            return False
    
    def obter_atividades(self, limite=10):
        """Obtém as últimas atividades do usuário"""
        if not self.client:
            raise Exception("Não conectado ao Garmin Connect")
            
        try:
            atividades = self.client.get_activities(0, limite)
            print(f"✅ {len(atividades)} atividades obtidas")
            return atividades
            
        except Exception as e:
            print(f"❌ Erro ao obter atividades: {str(e)}")
            return []

def calcular_pace(row):
    """Calcula o pace em min/km de forma segura"""
    try:
        if row['distancia_km'] > 0 and row['duracao_minutos'] > 0:
            pace = row['duracao_minutos'] / row['distancia_km']
            # Limita o pace entre 3 e 15 min/km (valores razoáveis)
            return min(max(pace, 3), 15)
    except:
        pass
    return None

def testar_garmin():
    conexao = GarminConnection()
    try:
        if conexao.conectar():
            # Obtém atividades
            atividades = conexao.obter_atividades(limite=20)
            
            if not atividades:
                print("Nenhuma atividade encontrada")
                return
            
            # Converte para DataFrame
            df = pd.DataFrame(atividades)
            
            # Formata as colunas de data
            df['startTimeLocal'] = pd.to_datetime(df['startTimeLocal'])
            
            # Seleciona colunas importantes
            colunas_importantes = [
                'activityName',
                'startTimeLocal',
                'distance',
                'duration',
                'averageSpeed',
                'averageHR',
                'maxHR',
                'calories'
            ]
            
            # Verifica colunas disponíveis
            colunas_disponiveis = [col for col in colunas_importantes if col in df.columns]
            df_formatado = df[colunas_disponiveis].copy()
            
            # Adiciona colunas calculadas com validação
            df_formatado['distancia_km'] = df_formatado['distance'].apply(
                lambda x: x/1000 if pd.notnull(x) and x > 0 else None
            )
            
            df_formatado['duracao_minutos'] = df_formatado['duration'].apply(
                lambda x: x/60 if pd.notnull(x) and x > 0 else None
            )
            
            # Calcula pace com validação
            df_formatado['pace_min_km'] = df_formatado.apply(calcular_pace, axis=1)
            
            # Remove linhas com valores inválidos
            df_formatado = df_formatado.dropna(subset=['distancia_km', 'duracao_minutos', 'pace_min_km'])
            
            # Remove outliers usando IQR
            Q1 = df_formatado['pace_min_km'].quantile(0.25)
            Q3 = df_formatado['pace_min_km'].quantile(0.75)
            IQR = Q3 - Q1
            df_formatado = df_formatado[
                (df_formatado['pace_min_km'] >= Q1 - 1.5 * IQR) &
                (df_formatado['pace_min_km'] <= Q3 + 1.5 * IQR)
            ]
            
            # Salva em CSV
            df_formatado.to_csv('atividades_garmin.csv', index=False)
            print("\n✅ Dados salvos em 'atividades_garmin.csv'")
            
            return df_formatado
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return None

if __name__ == "__main__":
    df = testar_garmin()