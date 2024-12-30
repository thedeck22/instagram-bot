import requests
import json
import time
import os
import openai
import logging
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração do logging
logger = logging.getLogger('bot_instagram')
logger.setLevel(logging.INFO)

# Criar um formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Configurar arquivo de log
file_handler = logging.FileHandler('bot_instagram.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Configurar saída para o console
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(formatter)
logger.addHandler(stdout_handler)

# Configurações do Instagram
INSTAGRAM_ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')

# Configuração do OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Configuração do Facebook App
APP_ID = os.getenv('APP_ID')
APP_SECRET = os.getenv('APP_SECRET')

class InstagramBot:
    def __init__(self):
        """Inicializa o bot"""
        self.comentarios_respondidos = set()
        self.carregar_comentarios_respondidos()
        openai.api_key = OPENAI_API_KEY

    def carregar_comentarios_respondidos(self):
        """Carrega os IDs dos comentários já respondidos"""
        try:
            with open('comentarios_respondidos.txt', 'r') as file:
                self.comentarios_respondidos = set(file.read().splitlines())
        except FileNotFoundError:
            self.comentarios_respondidos = set()

    def salvar_comentario_respondido(self, comment_id):
        """Salva o ID do comentário respondido"""
        self.comentarios_respondidos.add(comment_id)
        with open('comentarios_respondidos.txt', 'a') as file:
            file.write(f"{comment_id}\n")

    def gerar_resposta(self, comentario):
        """Gera uma resposta para o comentário usando GPT"""
        try:
            prompt = f"Por favor, gere uma resposta amigável e profissional para este comentário do Instagram: '{comentario}'. A resposta deve ser curta (máximo 200 caracteres) e incluir emojis apropriados."
            
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um assistente que gera respostas amigáveis e profissionais para comentários do Instagram."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Erro ao gerar resposta: {e}")
            return None

    def responder_comentario(self, comment_id, resposta):
        """Responde a um comentário no Instagram"""
        url = f"https://graph.facebook.com/v18.0/{comment_id}/replies"
        
        params = {
            'message': resposta,
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        
        try:
            response = requests.post(url, params=params)
            if response.status_code == 200:
                logger.info(f"Resposta enviada com sucesso: {resposta}")
                self.salvar_comentario_respondido(comment_id)
                return True
            else:
                logger.error(f"Erro ao enviar resposta: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Erro ao responder comentário: {e}")
            return False

    def obter_comentarios(self):
        """Obtém os comentários mais recentes"""
        url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
        
        # Primeiro, obtém os posts mais recentes
        params = {
            'fields': 'id,comments{id,text,timestamp}',
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                posts = data.get('data', [])
                
                for post in posts:
                    comments = post.get('comments', {}).get('data', [])
                    for comment in comments:
                        if comment['id'] not in self.comentarios_respondidos:
                            yield comment
            else:
                logger.error(f"Erro ao obter comentários: {response.text}")
        except Exception as e:
            logger.error(f"Erro ao obter comentários: {e}")

    def renovar_token(self):
        """Verifica e renova o token se necessário"""
        try:
            # Verifica se o token atual é válido
            url = f"https://graph.facebook.com/v18.0/me"
            params = {'access_token': INSTAGRAM_ACCESS_TOKEN}
            
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                logger.warning("Token expirado ou inválido. Tentando obter novo Long-Lived Token...")
                
                # Obtém novo Long-Lived Token
                url = "https://graph.facebook.com/v18.0/oauth/access_token"
                params = {
                    "grant_type": "fb_exchange_token",
                    "client_id": APP_ID,
                    "client_secret": APP_SECRET,
                    "fb_exchange_token": INSTAGRAM_ACCESS_TOKEN
                }
                
                logger.info("Obtendo Long-Lived Access Token...")
                response = requests.get(url, params=params)
                
                logger.info(f"Status da obtenção do Long-Lived Token: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    novo_token = data.get("access_token")
                    
                    if novo_token:
                        # Atualiza o token no arquivo .env
                        with open('.env', 'r') as file:
                            lines = file.readlines()
                        
                        with open('.env', 'w') as file:
                            for line in lines:
                                if line.startswith('INSTAGRAM_ACCESS_TOKEN='):
                                    file.write(f'INSTAGRAM_ACCESS_TOKEN={novo_token}\n')
                                else:
                                    file.write(line)
                        
                        logger.info("Token renovado com sucesso!")
                        return True
                    else:
                        logger.error("Token não encontrado na resposta")
                        return False
                else:
                    logger.error(f"Erro ao obter Long-Lived Token: {response.text}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao renovar token: {e}")
            return False

    def responder_mensagens(self):
        """Verifica e responde aos comentários não respondidos"""
        logger.info("Verificando novos comentários...")
        
        for comment in self.obter_comentarios():
            comment_id = comment['id']
            texto_comentario = comment['text']
            
            logger.info(f"Novo comentário encontrado: {texto_comentario}")
            
            # Gera uma resposta para o comentário
            resposta = self.gerar_resposta(texto_comentario)
            
            if resposta:
                # Responde ao comentário
                if self.responder_comentario(comment_id, resposta):
                    logger.info(f"Respondido ao comentário: {texto_comentario}")
                    logger.info(f"Resposta: {resposta}")
                else:
                    logger.error(f"Falha ao responder ao comentário: {texto_comentario}")
            else:
                logger.error("Não foi possível gerar uma resposta")

    def executar(self):
        """Executa o bot"""
        logger.info("Bot iniciado! Monitorando comentários...")
        logger.info(f"ID da conta: {INSTAGRAM_BUSINESS_ACCOUNT_ID}")
        
        # Verifica se as credenciais estão configuradas
        if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_BUSINESS_ACCOUNT_ID or not OPENAI_API_KEY:
            logger.error("Erro: Credenciais não configuradas corretamente!")
            return
            
        # Mostra parte do token por segurança
        token_preview = INSTAGRAM_ACCESS_TOKEN[:20]
        logger.info(f"Token: {token_preview}...")

        # Tempo de execução (23 horas e 45 minutos em segundos)
        MAX_EXECUTION_TIME = 23 * 60 * 60 + 45 * 60  # 23h45m
        start_time = time.time()

        try:
            # Testa a conexão inicial e renova o token
            if not self.renovar_token():
                logger.error("Erro ao renovar token inicial.")
                return

            # Loop principal - executa até próximo do limite de 24h
            while (time.time() - start_time) < MAX_EXECUTION_TIME:
                try:
                    logger.info("\n--- Nova verificação ---")
                    
                    # Verifica e renova o token a cada 2 horas
                    if (time.time() - start_time) % 7200 < 300:  # A cada 2 horas
                        self.renovar_token()
                    
                    # Obtém e responde aos comentários
                    self.responder_mensagens()
                    
                    # Calcula tempo restante
                    tempo_restante = MAX_EXECUTION_TIME - (time.time() - start_time)
                    horas_restantes = tempo_restante // 3600
                    minutos_restantes = (tempo_restante % 3600) // 60
                    
                    logger.info(f"\nTempo restante até próximo reinício: {int(horas_restantes)}h {int(minutos_restantes)}m")
                    logger.info("Aguardando 5 minutos antes da próxima verificação...")
                    
                    # Se faltam menos de 6 minutos, encerra o loop
                    if tempo_restante < 360:
                        logger.info("Próximo do limite diário. Encerrando execução...")
                        break
                        
                    # Ajusta o intervalo baseado no horário
                    hora_atual = time.localtime().tm_hour
                    if 1 <= hora_atual <= 5:  # Madrugada: verifica a cada 15 minutos
                        time.sleep(900)
                    else:  # Resto do dia: verifica a cada 5 minutos
                        time.sleep(300)
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"Erro de conexão: {e}")
                    time.sleep(60)
                except Exception as e:
                    logger.error(f"Erro durante a execução: {e}")
                    time.sleep(60)
                    
        except KeyboardInterrupt:
            logger.info("\nBot encerrado pelo usuário")
        except Exception as e:
            logger.error(f"Erro crítico: {e}")
        finally:
            logger.info("\nExecução diária finalizada. Aguardando próximo ciclo...")

if __name__ == "__main__":
    # Configura codificação UTF-8 para o terminal
    import sys
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    
    # Inicia o bot
    bot = InstagramBot()
    bot.executar()
