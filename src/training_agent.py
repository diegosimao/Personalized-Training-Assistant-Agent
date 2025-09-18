from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json
import xml.etree.ElementTree as ET
import csv
from fpdf import FPDF

# Carrega variáveis de ambiente
load_dotenv()

class TrainingAI:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Template do sistema
        system_template = """
        Você é um treinador expert em corrida, especializado em análise de dados e prescrição de treinos.
        
        DADOS DO ATLETA:
        {dados_resumidos}

        OBJETIVO DO ATLETA:
        {objetivo}

        PERFIL:
        - Nível: {nivel}
        - Dias disponíveis: {dias_treino} dias/semana

        DIRETRIZES PARA O PLANO:
        1. Baseie a progressão nos dados históricos
        2. Mantenha pelo menos 1 dia de recuperação entre treinos intensos
        3. Use o pace médio atual de {pace_medio} min/km como referência
        4. Use a FC média de {fc_media} bpm como referência
        5. Especifique SEMPRE ritmos em min/km como valores numéricos (exemplo: 5:30-6:00 min/km)
        6. NUNCA use 'inf' ou valores indefinidos para ritmos
        7. IMPORTANTE: Crie um plano COMPLETO para os próximos 60 dias (2 meses) com datas específicas
        8. Organize os treinos DIA A DIA com datas exatas (começando de hoje)
        9. Inclua pelo menos um treino longo por semana, aumentando gradualmente até chegar a 21 km no final do período

        TIPOS DE TREINO A INCLUIR (distribua ao longo da semana):
        1. Treino Regenerativo/Leve (recuperação ativa)
        2. Treino Base/Contínuo (volume)
        3. Treino Intervalado (velocidade)
        4. Treino Longo (resistência)
        5. Treino de Ritmo (pace específico)
        6. Fartlek (variações de ritmo)
        7. Subidas (quando apropriado)
        8. Dias de Descanso

        ESTRUTURA DO PLANO:
        Para cada treino, especifique:
        1. Data exata (DD/MM/AAAA)
        2. Dia da semana (Segunda, Terça, etc.)
        3. Tipo de treino (use a variedade acima)
        4. Distância e duração sugerida
        5. Ritmo alvo em min/km (use faixas de ritmo, exemplo: 5:30-6:00 min/km)
        6. Zonas de FC recomendadas
        7. Justificativa fisiológica
        8. Dicas específicas de execução

        DISTRIBUIÇÃO SEMANAL:
        - Alterne entre treinos intensos e leves
        - Inclua apenas {dias_treino} dias de treino por semana
        - Distribua os treinos considerando a recuperação adequada
        - Mantenha os outros dias como descanso estrategicamente posicionados

        IMPORTANTE:
        - Mostre a progressão dia a dia até atingir 21 km
        - O treino longo do último fim de semana deve ser de 21 km
        - Alterne intensidades
        - Inclua períodos de recuperação
        - SEMPRE especifique ritmos em min/km como valores numéricos
        - INCLUA TODOS OS 60 DIAS no plano, mesmo os dias de descanso
        
        Responda em português do Brasil, formatando o plano de forma clara e organizada.
        """
        
        self.prompt = ChatPromptTemplate.from_template(system_template)

    def analisar_dados(self, df):
        """Análise detalhada dos dados do Garmin"""
        try:
            # Remove valores inválidos de pace
            df = df[df['pace_min_km'].notna() & (df['pace_min_km'] > 0) & (df['pace_min_km'] < 15)]
            
            # Cálculos básicos
            media_distancia = df["distancia_km"].mean()
            max_distancia = df["distancia_km"].max()
            media_duracao = df["duracao_minutos"].mean()
            media_pace = df["pace_min_km"].mean()
            media_fc = df["averageHR"].mean() if "averageHR" in df.columns else 0
            
            # Análises adicionais
            volume_semanal = df.groupby(pd.Grouper(key='startTimeLocal', freq='W'))['distancia_km'].sum().mean()
            tendencia_pace = df.sort_values('startTimeLocal')['pace_min_km'].tolist()
            melhora_pace = tendencia_pace[0] - tendencia_pace[-1] if len(tendencia_pace) > 1 else 0
            
            # Cálculo de distância segura (máx histórico + 10%)
            max_dist_segura = round(max_distancia * 1.1, 1)
            
            resumo = {
                "media_distancia": round(media_distancia, 2),
                "max_distancia": round(max_distancia, 2),
                "media_duracao": round(media_duracao, 0),
                "media_pace": round(media_pace, 2),
                "media_fc": round(media_fc, 0),
                "volume_semanal": round(volume_semanal, 2),
                "melhora_pace": round(melhora_pace, 2),
                "max_dist_segura": max_dist_segura,
                "total_atividades": len(df),
                "periodo_dados": f"{df['startTimeLocal'].min().date()} a {df['startTimeLocal'].max().date()}"
            }
            return resumo
        except Exception as e:
            print(f"Erro ao analisar dados: {str(e)}")
            return None
    def gerar_plano(self, df, objetivo, nivel, dias_treino, feedback=None):
        """Gera um plano de treino personalizado"""
        try:
            resumo = self.analisar_dados(df)
            if not resumo:
                return "Erro ao analisar dados de treino. Por favor, tente novamente."

            dados_resumidos = f"""
            HISTÓRICO DE TREINO:
            - Média de distância: {resumo['media_distancia']:.2f} km por treino
            - Distância máxima: {resumo['max_distancia']:.2f} km
            - Volume semanal médio: {resumo['volume_semanal']:.2f} km
            - Duração média: {resumo['media_duracao']:.0f} min
            - Pace médio atual: {resumo['media_pace']:.2f} min/km
            - Evolução do pace: {resumo['melhora_pace']:.2f} min/km
            - FC média: {resumo['media_fc']:.0f} bpm
            - Total de atividades: {resumo['total_atividades']}
            - Período analisado: {resumo['periodo_dados']}
            """

            if feedback and isinstance(feedback, dict):
                dados_resumidos += f"""
                FEEDBACK DO USUÁRIO:
                - Tipo: {feedback.get('tipo', 'Não especificado')}
                - Nível de Impacto: {feedback.get('nivel', 'Não especificado')}
                - Detalhes: {feedback.get('detalhes', 'Não especificado')}
                - Preferências: {', '.join(feedback.get('preferencias', ['Não especificado']))}
                """
            
            # Gera datas para os próximos 60 dias
            hoje = datetime.now()
            datas = [(hoje + timedelta(days=i)).strftime("%d/%m/%Y") for i in range(60)]
            dias_semana = [(hoje + timedelta(days=i)).strftime("%A") for i in range(60)]
            dias_semana = [self.traduzir_dia(dia) for dia in dias_semana]
            
            # Adiciona as datas ao prompt
            datas_formatadas = ", ".join([f"{datas[i]} ({dias_semana[i]})" for i in range(60)])
            
            # Cria um prompt específico para plano completo de 60 dias
            prompt_completo = f"""
            Você é um treinador expert em corrida, especializado em análise de dados e prescrição de treinos.
            
            DADOS DO ATLETA:
            {dados_resumidos}

            OBJETIVO DO ATLETA:
            {objetivo}

            PERFIL:
            - Nível: {nivel}
            - Dias disponíveis: {dias_treino} dias/semana

            DIRETRIZES PARA O PLANO:
            1. Baseie a progressão nos dados históricos
            2. Mantenha pelo menos 1 dia de recuperação entre treinos intensos
            3. Use o pace médio atual de {resumo['media_pace']:.2f} min/km como referência
            4. Use a FC média de {resumo['media_fc']:.0f} bpm como referência
            5. Especifique SEMPRE ritmos em min/km como valores numéricos (exemplo: 5:30-6:00 min/km)
            6. NUNCA use 'inf' ou valores indefinidos para ritmos
            7. IMPORTANTE: Crie um plano COMPLETO para os próximos 60 dias (2 meses) com datas específicas
            8. Organize os treinos DIA A DIA com datas exatas
            9. Inclua pelo menos um treino longo por semana, aumentando gradualmente até chegar a 21 km no final do período

            TIPOS DE TREINO A INCLUIR (distribua ao longo da semana):
            1. Treino Regenerativo/Leve (recuperação ativa)
            2. Treino Base/Contínuo (volume)
            3. Treino Intervalado (velocidade)
            4. Treino Longo (resistência)
            5. Treino de Ritmo (pace específico)
            6. Fartlek (variações de ritmo)
            7. Subidas (quando apropriado)
            8. Dias de Descanso

            ESTRUTURA DO PLANO:
            Para cada dia, especifique:
            1. Data exata (DD/MM/AAAA)
            2. Dia da semana (Segunda, Terça, etc.)
            3. Tipo de treino (use a variedade acima) ou "Descanso"
            4. Para dias de treino: Distância, duração, ritmo alvo, zonas FC, justificativa e dicas
            5. Para dias de descanso: apenas indique "Descanso" e uma breve justificativa

            DISTRIBUIÇÃO SEMANAL:
            - Alterne entre treinos intensos e leves
            - Inclua apenas {dias_treino} dias de treino por semana
            - Distribua os treinos considerando a recuperação adequada
            - Mantenha os outros dias como descanso estrategicamente posicionados

            IMPORTANTE:
            - Mostre a progressão dia a dia até atingir 21 km
            - O treino longo do último fim de semana deve ser de 21 km com ritmo entre 6:00-6:30 min/km
            - Alterne intensidades
            - Inclua períodos de recuperação
            - SEMPRE especifique ritmos em min/km como valores numéricos
            - INCLUA TODOS OS 60 DIAS no plano, mesmo os dias de descanso
            - NÃO ABREVIE O PLANO! Mostre todos os dias de todas as semanas.
            - NÃO USE "..." ou "Semana 2-8" como abreviação. Detalhe cada dia de cada semana.
            
            DATAS PARA OS PRÓXIMOS 60 DIAS:
            {datas_formatadas}
            
            Responda em português do Brasil, formatando o plano de forma clara e organizada.
            """
            
            # Divide o prompt em partes para processar separadamente
            # Isso ajuda a evitar truncamento na resposta
            
            # Parte 1: Gerar plano para as primeiras 4 semanas
            prompt_parte1 = prompt_completo + "\n\nGere o plano detalhado para as primeiras 4 semanas (28 dias)."
            
            # Parte 2: Gerar plano para as últimas 4 semanas
            prompt_parte2 = prompt_completo + "\n\nGere o plano detalhado para as últimas 4 semanas (32 dias restantes)."
            
            # Usa a API diretamente para evitar truncamento
            import os
            import openai
            from dotenv import load_dotenv
            
            # Carrega variáveis de ambiente
            load_dotenv()
            
            # Configura a API da OpenAI
            openai.api_key = os.getenv("OPENAI_API_KEY")
            
            # Faz a chamada para a API - Parte 1
            print("Gerando plano para as primeiras 4 semanas...")
            response1 = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um treinador expert em corrida."},
                    {"role": "user", "content": prompt_parte1}
                ],
                max_tokens=4000,
                temperature=0.7
            )
            
            # Faz a chamada para a API - Parte 2
            print("Gerando plano para as últimas 4 semanas...")
            response2 = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um treinador expert em corrida."},
                    {"role": "user", "content": prompt_parte2}
                ],
                max_tokens=4000,
                temperature=0.7
            )
            
            # Extrai os planos
            plano_parte1 = response1.choices[0].message.content
            plano_parte2 = response2.choices[0].message.content
            
            # Combina os planos
            plano_texto = f"""**PLANO DE TREINAMENTO PARA MEIA MARATONA - 60 DIAS**

{plano_parte1}

{plano_parte2}
"""
            
            # Salva o plano em um arquivo
            with open("plano_completo_meia_maratona.txt", "w", encoding="utf-8") as f:
                f.write(plano_texto)
            
            print(f"✅ Plano salvo em 'plano_completo_meia_maratona.txt'")
            
            return self.formatar_plano(plano_texto)
            
        except Exception as e:
            print(f"Erro ao gerar plano: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None
    
    def traduzir_dia(self, dia_en):
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

    def formatar_plano(self, plano_texto):
        """Formata o plano de treino para melhor visualização"""
        try:
            # Remove caracteres especiais problemáticos
            plano_texto = plano_texto.replace('\u2028', '\n').replace('\u2029', '\n')
            
            # Verifica e corrige possíveis valores 'inf' no texto
            plano_texto = plano_texto.replace('inf min/km', '6:00 min/km')
            plano_texto = plano_texto.replace('inf', '6:00')
            
            plano_formatado = f"""
            # 🏃‍♂️ Seu Plano de Treino Personalizado

            {plano_texto}

            ## 📝 Observações Importantes
            - Sempre faça aquecimento antes e alongamento depois
            - Hidrate-se bem antes, durante e após os treinos
            - Escute seu corpo e ajuste as intensidades conforme necessário
            - Em caso de dor ou desconforto, interrompa o treino

            ## 🎯 Próximos Passos
            1. Salve este plano
            2. Comece os treinos gradualmente
            3. Monitore seu progresso
            4. Ajuste conforme necessário

            Boa sorte em seus treinos! 💪
            """
            return plano_formatado
        except Exception as e:
            print(f"Erro ao formatar plano: {str(e)}")
            return plano_texto

    def gerar_arquivo_treino(self, plano_texto, formato="pdf", sufixo=""):
        """Gera arquivos nos formatos solicitados"""
        try:
            data_atual = datetime.now().strftime("%Y%m%d")
            
            if formato == "txt":
                # Formato mais simples, só salva o texto
                filename = f'plano_treino{sufixo}_{data_atual}.txt'
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(plano_texto)
                return filename
            
            elif formato == "csv":
                # Formato para Sisrun
                filename = f'sisrun_treino{sufixo}_{data_atual}.csv'
                headers = ['Data', 'Tipo de Treino', 'Distância (km)', 'Duração (min)', 
                          'Ritmo Médio (min/km)', 'Zona FC', 'Percurso', 'Observações']
                
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    # Adiciona uma linha exemplo para o usuário preencher
                    writer.writerow([datetime.now().strftime('%d/%m/%Y'), 
                                   'Treino Contínuo', '5', '30', '6:00', 
                                   'Z2', 'Livre', 'Preencha conforme plano'])
                return filename
            
            elif formato == "tcx":
                # Formato para Garmin
                filename = f'garmin_treino{sufixo}_{data_atual}.tcx'
                tcx_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
    <Workouts>
        <Workout Sport="Running">
            <Name>Treino Exemplo</Name>
            <Step xsi:type="Step_t">
                <Name>Aquecimento</Name>
                <Duration xsi:type="Time_t">
                    <Seconds>600</Seconds>
                </Duration>
                <Intensity>WarmUp</Intensity>
            </Step>
            <Step xsi:type="Step_t">
                <Name>Treino Principal</Name>
                <Duration xsi:type="Time_t">
                    <Seconds>1800</Seconds>
                </Duration>
                <Intensity>Active</Intensity>
            </Step>
            <Step xsi:type="Step_t">
                <Name>Desaquecimento</Name>
                <Duration xsi:type="Time_t">
                    <Seconds>300</Seconds>
                </Duration>
                <Intensity>Cooldown</Intensity>
            </Step>
        </Workout>
    </Workouts>
</TrainingCenterDatabase>"""
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(tcx_template)
                return filename
            
            else:
                print(f"Formato {formato} não suportado")
                return None
            
        except Exception as e:
            print(f"Erro ao gerar arquivo {formato}: {str(e)}")
            return None

    def gerar_pdf(self, plano_texto, filename):
        """Gera arquivo PDF do plano"""
        try:
            pdf = FPDF()
            pdf.add_page()
            
            # Configura fonte e margens
            pdf.set_font('Arial', 'B', 16)
            pdf.set_margins(20, 20, 20)
            
            # Cabeçalho
            pdf.cell(0, 10, 'Plano de Treino Personalizado', 0, 1, 'C')
            pdf.ln(5)
            
            # Informações gerais
            pdf.set_font('Arial', '', 12)
            pdf.multi_cell(0, 10, 'Este plano foi gerado com base nos seus dados históricos de treino e objetivos.')
            pdf.ln(5)
            
            # Extrai os treinos estruturados
            treinos = self.extrair_treinos(plano_texto)
            
            # Sumário do plano
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, 'Visão Geral do Plano', 0, 1, 'L')
            pdf.ln(5)
            
            # Tabela de treinos
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(20, 10, 'Dia', 1)
            pdf.cell(40, 10, 'Tipo', 1)
            pdf.cell(30, 10, 'Distância', 1)
            pdf.cell(30, 10, 'Duração', 1)
            pdf.cell(30, 10, 'Ritmo', 1)
            pdf.ln()
            
            pdf.set_font('Arial', '', 10)
            for i, treino in enumerate(treinos, 1):
                pdf.cell(20, 10, f'Dia {i}', 1)
                pdf.cell(40, 10, treino.get('tipo', ''), 1)
                pdf.cell(30, 10, f"{treino.get('distancia', 0):.1f} km", 1)
                pdf.cell(30, 10, f"{treino.get('duracao', 0):.0f} min", 1)
                pdf.cell(30, 10, f"{treino.get('ritmo', 0):.2f} min/km", 1)
                pdf.ln()
            
            pdf.ln(10)
            
            # Detalhes dos treinos
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, 'Detalhes dos Treinos', 0, 1, 'L')
            pdf.ln(5)
            
            for i, treino in enumerate(treinos, 1):
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 10, f"Dia {i} - {treino.get('tipo', '')}", 0, 1, 'L')
                pdf.set_font('Arial', '', 10)
                pdf.multi_cell(0, 10, treino.get('observacoes', ''))
                pdf.ln(5)
            
            # Rodapé com data de geração
            pdf.set_font('Arial', 'I', 10)
            data_geracao = datetime.now().strftime("%d/%m/%Y %H:%M")
            pdf.cell(0, 10, f'Gerado em: {data_geracao}', 0, 1, 'R')
            
            # Salva o PDF
            pdf.output(filename, 'F')
            
            return filename if os.path.exists(filename) else None
            
        except Exception as e:
            print(f"Erro ao gerar PDF: {str(e)}")
            return None

    def gerar_csv_sisrun(self, plano_texto, filename):
        """Gera arquivo CSV para Sisrun"""
        try:
            treinos = self.extrair_treinos(plano_texto)
            
            if not treinos:
                print("Nenhum treino extraído para gerar CSV")
                return None
            
            # Cabeçalho padrão do Sisrun
            headers = [
                'Data',
                'Tipo de Treino',
                'Distância (km)',
                'Duração (min)',
                'Ritmo Médio (min/km)',
                'Zona FC',
                'Percurso',
                'Observações'
            ]
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                
                data = datetime.now()
                for treino in treinos:
                    # Trata dias de descanso
                    if treino.get('tipo', '').lower() == 'descanso':
                        row = [
                            data.strftime('%d/%m/%Y'),
                            'Descanso',
                            0,
                            0,
                            0,
                            'N/A',
                            'N/A',
                            'Dia de recuperação'
                        ]
                    else:
                        # Valida e formata valores numéricos
                        distancia = min(max(float(treino.get('distancia', 5)), 3), 42)
                        duracao = min(max(float(treino.get('duracao', 30)), 20), 240)
                        ritmo = min(max(float(treino.get('ritmo', 6)), 4), 8)
                        
                        row = [
                            data.strftime('%d/%m/%Y'),
                            treino.get('tipo', ''),
                            f"{distancia:.1f}",
                            f"{duracao:.0f}",
                            f"{ritmo:.2f}",
                            'Z1-Z3',  # Zona de FC padrão
                            'Livre',  # Percurso padrão
                            treino.get('observacoes', '')[:100]  # Limita tamanho das observações
                        ]
                    
                    writer.writerow(row)
                    data += timedelta(days=1)
                
            return filename if os.path.exists(filename) else None
            
        except Exception as e:
            print(f"Erro ao gerar CSV: {str(e)}")
            return None

    def gerar_tcx_garmin(self, plano_texto, filename):
        """Gera arquivo TCX para Garmin"""
        try:
            root = ET.Element('TrainingCenterDatabase')
            root.set('xmlns', 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2')
            
            workouts = ET.SubElement(root, 'Workouts')
            treinos = self.extrair_treinos(plano_texto)
            
            for i, treino in enumerate(treinos, 1):
                workout = ET.SubElement(workouts, 'Workout')
                workout.set('Sport', 'Running')
                
                name = ET.SubElement(workout, 'Name')
                name.text = f"Treino {i} - {treino.get('tipo', '')}"
                
                steps = ET.SubElement(workout, 'Steps')
                self.adicionar_passos_tcx(steps, treino)
            
            tree = ET.ElementTree(root)
            tree.write(filename, encoding='utf-8', xml_declaration=True)
            
            return filename
        except Exception as e:
            print(f"Erro ao gerar TCX: {str(e)}")
            return None

    def adicionar_passos_tcx(self, steps, treino):
        """Adiciona os passos do treino ao TCX"""
        try:
            # Garante valores válidos
            distancia = min(max(float(treino.get('distancia', 5)), 3), 42)
            ritmo = min(max(float(treino.get('ritmo', 6)), 4), 8)
            
            # Aquecimento
            step = ET.SubElement(steps, 'Step')
            step.set('Type', 'Warmup')
            duration = ET.SubElement(step, 'Duration')
            duration.set('Type', 'Time')
            duration.text = '600'  # 10 minutos em segundos
            
            # Treino principal
            step = ET.SubElement(steps, 'Step')
            step.set('Type', 'Run')
            duration = ET.SubElement(step, 'Duration')
            duration.set('Type', 'Distance')
            duration.text = str(int(distancia * 1000))  # Converte para metros
            
            target = ET.SubElement(step, 'Target')
            target.set('Type', 'Speed')
            zone = ET.SubElement(target, 'Zone')
            speed_high = ET.SubElement(zone, 'SpeedHigh')
            speed_high.text = str(1000 / (ritmo * 60))  # Converte min/km para m/s
            
            # Desaquecimento
            step = ET.SubElement(steps, 'Step')
            step.set('Type', 'Cooldown')
            duration = ET.SubElement(step, 'Duration')
            duration.set('Type', 'Time')
            duration.text = '300'  # 5 minutos em segundos
            
        except Exception as e:
            print(f"Erro ao adicionar passos TCX: {str(e)}")

if __name__ == "__main__":
    from garmin_connect import testar_garmin
    
    df = testar_garmin()
    if df is not None:
        treinador = TrainingAI()
        plano = treinador.gerar_plano(
            df,
            objetivo="Preparar para uma meia maratona de 21 km",
            nivel="Intermediário",
            dias_treino=6
        )
        print(plano)