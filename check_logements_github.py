#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import json
import os
import sys
from datetime import datetime

# Configuration
URL = "https://trouverunlogement.lescrous.fr/tools/47/search?bounds=0.3240886_46.6797029_0.3878991_46.6154534&locationName=Chasseneuil-du-Poitou+%2886360%29"
TELEGRAM_BOT_TOKEN = "8781405009:AAEEoV0ZG9UGisTIYim6EPYqv94_D3sQ320"
TELEGRAM_CHAT_ID = "7657754976"
DATA_FILE = "logements_chasseneuil.json"

# Ville ciblée
VILLE_CIBLE = "chasseneuil"

# Mots qui indiquent une colocation (à EXCLURE)
MOTS_COLOCATION = [
    "colocation",
    "coloc",
    "chambre en collectif",
    "logement partage",
    "logement partagé"
]

def get_page_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Erreur recuperation: {e}")
        return None

def is_target_city(text):
    return VILLE_CIBLE in text.lower()

def is_colocation(text):
    text_lower = text.lower()
    for mot in MOTS_COLOCATION:
        if mot in text_lower:
            return True
    return False

def extract_target_logements(content):
    soup = BeautifulSoup(content, 'html.parser')
    logements_cibles = []

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
            print(f"Analyse de {len(items)} elements ({selector})")
            for item in items:
                text = item.get_text(strip=True)

                if is_target_city(text) and not is_colocation(text):
                    logement_info = {
                        'text': text[:200],
                        'selector': selector,
                        'timestamp': datetime.now().isoformat()
                    }
                    link = item.find('a', href=True)
                    if link:
                        logement_info['url'] = link['href']
                    elif item.name == 'a':
                        logement_info['url'] = item.get('href', '')
                    logements_cibles.append(logement_info)
                    print(f"Trouve (non-coloc): {text[:80]}...")
                elif is_target_city(text) and is_colocation(text):
                    print(f"Ignore (colocation): {text[:80]}...")

            if logements_cibles:
                break

    if not logements_cibles:
        print("Recherche dans tout le contenu...")
        all_text = soup.get_text()
        if is_target_city(all_text) and not is_colocation(all_text):
            logements_cibles.append({
                'text': 'Logement Chasseneuil trouve mais structure HTML non reconnue',
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
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def send_telegram_notification(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        response = requests.post(url, data=data, timeout=10)
        result = response.json()
        if result.get('ok'):
            print("Notification envoyee")
            return True
        else:
            print(f"Erreur Telegram: {result.get('description')}")
            return False
    except Exception as e:
        print(f"Erreur notification: {e}")
        return False

def format_logement_message(logement):
    text = logement.get('text', 'Details non disponibles')[:150]
    url = logement.get('url', '')
    msg = f"📍 {text}"
    if url:
        if not url.startswith('http'):
            url = 'https://trouverunlogement.lescrous.fr' + url
        msg += f"\n🔗 <a href='{url}'>Voir l'annonce</a>"
    return msg

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Verification Chasseneuil-du-Poitou (hors coloc)...")

    content = get_page_content(URL)
    if content is None:
        sys.exit(1)

    current_data = extract_target_logements(content)
    print(f"Logements Chasseneuil (non-coloc) trouves: {current_data['count']}")

    previous_data = load_previous_data()

    if previous_data is None:
        print("Premiere surveillance - etat initial enregistre")
        save_data(current_data)
        if current_data['count'] > 0:
            message = f"🏠 Surveillance Chasseneuil-du-Poitou activee !\n\n{current_data['count']} logement(s) actuellement disponible(s) (hors colocation)"
            for logement in current_data['logements']:
                message += "\n\n" + format_logement_message(logement)
            send_telegram_notification(message)
        sys.exit(0)

    prev_count = previous_data.get('count', 0)
    curr_count = current_data['count']
    print(f"Avant: {prev_count} | Maintenant: {curr_count}")

    if curr_count > prev_count:
        diff = curr_count - prev_count
        print(f"NOUVEAU(X) LOGEMENT(S) CHASSENEUIL ! (+{diff})")
        message = f"🚨 NOUVEAU LOGEMENT CHASSENEUIL-DU-POITOU !\n\n+{diff} logement(s) disponible(s) (hors colocation) !\n\nTotal: {curr_count}"
        for logement in current_data['logements']:
            message += "\n\n" + format_logement_message(logement)
        message += f"\n\n👉 <a href='{URL}'>Voir sur le site CROUS</a>"
        send_telegram_notification(message)
        save_data(current_data)
    elif curr_count < prev_count:
        diff = prev_count - curr_count
        print(f"Logement(s) retire(s) (-{diff})")
        save_data(current_data)
    else:
        print("Aucun changement")
        save_data(current_data)

    print("Verification terminee")

if __name__ == "__main__":
    main()
