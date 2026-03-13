#!/usr/bin/env python3
"""
Script de surveillance - UNIQUEMENT résidences Rabelais et Descartes
Ignore tous les autres logements
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import sys
from datetime import datetime

# Configuration
URL = "https://trouverunlogement.lescrous.fr/tools/42/search?bounds=0.2911332_46.6270136_0.4516769_46.5422279"
TELEGRAM_BOT_TOKEN = "8781405009:AAEEoV0ZG9UGisTIYim6EPYqv94_D3sQ320"
TELEGRAM_CHAT_ID = "7657754976"
DATA_FILE = "logements_rabelais_descartes.json"

# 🎯 RÉSIDENCES CIBLÉES (ajoutez des variantes possibles)
RESIDENCES_CIBLES = [
    "rabelais",
    "descartes",
    "rene descartes",
    "rené descartes",
    "francois rabelais",
    "françois rabelais"
]

def get_page_content(url):
    """Récupère le contenu de la page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"❌ Erreur récupération: {e}")
        return None

def is_target_residence(text):
    """
    Vérifie si le texte contient une résidence ciblée
    """
    text_lower = text.lower()
    for residence in RESIDENCES_CIBLES:
        if residence in text_lower:
            return True
    return False

def extract_target_logements(content):
    """
    Extrait UNIQUEMENT les logements Rabelais ou Descartes
    """
    soup = BeautifulSoup(content, 'html.parser')
    
    logements_cibles = []
    
    # Stratégie 1 : Chercher tous les liens et divs qui pourraient être des logements
    # On essaie différents sélecteurs
    possible_selectors = [
        'div.residence-item',
        'div.logement-item',
        'article',
        'div[class*="residence"]',
        'div[class*="logement"]',
        'li[class*="result"]',
        'a[href*="residence"]',
        'div.card'
    ]
    
    for selector in possible_selectors:
        items = soup.select(selector)
        if items:
            print(f"🔍 Analyse de {len(items)} éléments ({selector})")
            for item in items:
                text = item.get_text(strip=True)
                
                # Vérifier si c'est une résidence ciblée
                if is_target_residence(text):
                    # Extraire infos
                    logement_info = {
                        'text': text[:200],  # Premiers 200 caractères
                        'selector': selector,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Essayer d'extraire le lien
                    link = item.find('a', href=True)
                    if link:
                        logement_info['url'] = link['href']
                    elif item.name == 'a':
                        logement_info['url'] = item.get('href', '')
                    
                    logements_cibles.append(logement_info)
                    print(f"  ✅ Trouvé: {text[:80]}...")
            
            if logements_cibles:
                break  # On a trouvé avec ce sélecteur, on arrête
    
    # Si rien trouvé avec les sélecteurs, chercher dans tout le texte
    if not logements_cibles:
        print("⚠️ Recherche dans tout le contenu...")
        all_text = soup.get_text()
        if is_target_residence(all_text):
            # La page contient les résidences mais on n'arrive pas à les isoler
            logements_cibles.append({
                'text': 'Résidence trouvée mais structure HTML non reconnue',
                'selector': 'full-page',
                'timestamp': datetime.now().isoformat(),
                'needs_manual_check': True
            })
    
    return {
        'count': len(logements_cibles),
        'logements': logements_cibles,
        'timestamp': datetime.now().isoformat()
    }

def load_previous_data():
    """Charge les données précédentes"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_data(data):
    """Sauvegarde les données"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def send_telegram_notification(message):
    """Envoie une notification Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data, timeout=10)
        result = response.json()
        if result.get('ok'):
            print("✅ Notification envoyée")
            return True
        else:
            print(f"❌ Erreur Telegram: {result.get('description')}")
            return False
    except Exception as e:
        print(f"❌ Erreur notification: {e}")
        return False

def format_logement_message(logement):
    """Formate un logement pour le message"""
    text = logement.get('text', 'Détails non disponibles')[:150]
    url = logement.get('url', '')
    
    msg = f"📍 {text}"
    if url:
        if not url.startswith('http'):
            url = 'https://trouverunlogement.lescrous.fr' + url
        msg += f"\n🔗 <a href='{url}'>Voir l'annonce</a>"
    
    return msg

def main():
    """Fonction principale"""
    print(f"🔍 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Vérification Rabelais/Descartes...")
    
    # Récupérer la page
    content = get_page_content(URL)
    if content is None:
        sys.exit(1)
    
    # Extraire les logements ciblés
    current_data = extract_target_logements(content)
    
    print(f"🎯 Logements Rabelais/Descartes trouvés: {current_data['count']}")
    
    # Charger données précédentes
    previous_data = load_previous_data()
    
    # Première exécution
    if previous_data is None:
        print("✅ Première surveillance - état initial enregistré")
        save_data(current_data)
        
        # Si déjà des logements présents, notifier
        if current_data['count'] > 0:
            message = f"""🏠 <b>Surveillance Rabelais/Descartes activée !</b>

📊 {current_data['count']} logement(s) actuellement disponible(s):

"""
            for logement in current_data['logements']:
                message += format_logement_message(logement) + "\n\n"
            
            message += f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            message += "🔔 Vous serez alerté des nouveaux logements !"
            
            send_telegram_notification(message)
        
        sys.exit(0)
    
    # Comparer
    prev_count = previous_data.get('count', 0)
    curr_count = current_data['count']
    
    print(f"📊 Avant: {prev_count} | Maintenant: {curr_count}")
    
    # Nouveau logement détecté
    if curr_count > prev_count:
        diff = curr_count - prev_count
        print(f"🚨 NOUVEAU(X) LOGEMENT(S) RABELAIS/DESCARTES ! (+{diff})")
        
        message = f"""🚨 <b>NOUVEAU LOGEMENT RABELAIS/DESCARTES !</b>

🎯 +{diff} logement(s) disponible(s) !

📊 Total maintenant: {curr_count} logement(s)

"""
        
        # Lister tous les logements actuels
        for logement in current_data['logements']:
            message += format_logement_message(logement) + "\n\n"
        
        message += f"👉 <a href='{URL}'>Voir sur le site CROUS</a>\n\n"
        message += f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        message += "💨 <b>DÉPÊCHEZ-VOUS !</b>"
        
        send_telegram_notification(message)
        save_data(current_data)
        
    elif curr_count < prev_count:
        diff = prev_count - curr_count
        print(f"⚠️ Logement(s) retiré(s) (-{diff})")
        
        message = f"""⚠️ <b>Logement Rabelais/Descartes retiré</b>

📊 -{diff} logement(s)
📊 Reste: {curr_count} logement(s)

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
        
        send_telegram_notification(message)
        save_data(current_data)
        
    else:
        print("✅ Aucun changement")
        # On met à jour quand même les timestamps
        save_data(current_data)
    
    print("✅ Vérification terminée")

if __name__ == "__main__":
    main()
