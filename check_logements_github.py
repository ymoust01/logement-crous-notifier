#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import hashlib
import os
import sys
from datetime import datetime

# Configuration
URL = "https://trouverunlogement.lescrous.fr/tools/42/search?bounds=0.2911332_46.6270136_0.4516769_46.5422279"
TELEGRAM_BOT_TOKEN = "8781405009:AAEEoV0ZG9UGisTIYim6EPYqv94_D3sQ320"
TELEGRAM_CHAT_ID = "7657754976"
HASH_FILE = "page_hash.txt"

def get_page_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        content = ' '.join(soup.get_text().split())
        return content
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

def calculate_hash(content):
    if content is None:
        return None
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def load_previous_hash():
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, 'r') as f:
            return f.read().strip()
    return None

def save_hash(hash_value):
    with open(HASH_FILE, 'w') as f:
        f.write(hash_value)

def send_telegram_notification(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        response = requests.post(url, data=data, timeout=10)
        result = response.json()
        if result.get('ok'):
            print("✅ Notification envoyée")
            return True
        else:
            print(f"❌ Erreur Telegram: {result.get('description')}")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def main():
    print(f"🔍 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Vérification...")
    
    content = get_page_content(URL)
    if content is None:
        sys.exit(1)
    
    current_hash = calculate_hash(content)
    print(f"📊 Hash: {current_hash[:16]}...")
    
    previous_hash = load_previous_hash()
    
    if previous_hash is None:
        print("✅ Première surveillance")
        save_hash(current_hash)
        sys.exit(0)
    
    if current_hash != previous_hash:
        print("🚨 CHANGEMENT DÉTECTÉ !")
        
        message = f"""🔔 <b>NOUVEAU LOGEMENT DÉTECTÉ !</b>

🏠 La page des logements CROUS a changé !

👉 <a href="{URL}">Voir maintenant</a>

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}

💡 Dépêchez-vous !"""
        
        send_telegram_notification(message)
        save_hash(current_hash)
        print("✅ Hash mis à jour")
    else:
        print("✅ Aucun changement")
    
    print("✅ Terminé")

if __name__ == "__main__":
    main()
