import requests
import json

def obter_token_acesso():
    """
    Obtém um Long-Lived Access Token usando as credenciais do app
    """
    print("\nIniciando processo de geração do Long-Lived Token...")
    
    # Credenciais do app
    app_id = "1488171585077001"
    app_secret = "0ad7a6c49f9b1fbd0468f2b6c9f4c9e4"
    
    # Primeiro, obtém o token de acesso do app
    url = "https://graph.facebook.com/oauth/access_token"
    params = {
        "client_id": app_id,
        "client_secret": app_secret,
        "grant_type": "client_credentials"
    }
    
    print("\nObtendo token de acesso do app...")
    response = requests.get(url, params=params)
    print(f"Status da resposta: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        app_token = data.get("access_token")
        print("Token do app obtido com sucesso!")
        
        # Agora, obtém o token de longa duração para o Instagram
        url = "https://graph.facebook.com/v18.0/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": app_token
        }
        
        print("\nObtendo token de longa duração...")
        response = requests.get(url, params=params)
        print(f"Status da resposta: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            long_lived_token = data.get("access_token")
            print("\nToken de longa duração obtido com sucesso!")
            return long_lived_token
        else:
            print("\nErro ao obter token de longa duração:")
            print(response.text)
            return None
    else:
        print("\nErro ao obter token do app:")
        print(response.text)
        return None

if __name__ == "__main__":
    # Obtém o novo token
    novo_token = obter_token_acesso()
    
    if novo_token:
        print("\nToken gerado com sucesso!")
        print("\nAtualize seu arquivo .env com o novo token:")
        print(f"INSTAGRAM_ACCESS_TOKEN={novo_token}")
        
        # Atualiza o arquivo .env
        try:
            with open('.env', 'r') as file:
                lines = file.readlines()
            
            with open('.env', 'w') as file:
                for line in lines:
                    if line.startswith('INSTAGRAM_ACCESS_TOKEN='):
                        file.write(f'INSTAGRAM_ACCESS_TOKEN={novo_token}\n')
                    else:
                        file.write(line)
            print("\nArquivo .env atualizado com sucesso!")
        except Exception as e:
            print(f"\nErro ao atualizar arquivo .env: {e}")
    else:
        print("\nFalha ao gerar novo token. Tente novamente.")
