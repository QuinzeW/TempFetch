"""
Script pour récupérer la température du ventilateur Dyson 
et l'écrire dans Google Sheets toutes les 30 minutes.
"""

from libpurecool.dyson import DysonAccount
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import time
import json

# --- Configuration Dyson ---
DYSON_EMAIL = os.environ['DYSON_EMAIL']
DYSON_PASSWORD = os.environ['DYSON_PASSWORD']
DYSON_LANGUAGE = 'FR'  # Code langue à ajuster (FR, EN, ES, etc.)

# --- Configuration Google Sheets ---
GOOGLE_SHEET_NAME = os.environ['1JGJI3FPOjseIvI-_pu9mnEWi1en0nHcl1npmr74h-tw']
WORKSHEET_NAME = 'test'  # Nom de l'onglet (par défaut 'Feuille1')


def get_dyson_temperature():
    """Se connecter au Dyson et récupérer la température intérieure en °C."""
    print("Connexion au compte Dyson...")
    dyson_account = DysonAccount(DYSON_EMAIL, DYSON_PASSWORD, DYSON_LANGUAGE)
    logged = dyson_account.login()
    
    if not logged:
        print("Erreur: Impossible de se connecter au compte Dyson")
        return None
    
    devices = dyson_account.devices()
    
    if not devices:
        print("Erreur: Aucun appareil Dyson trouvé sur ce compte")
        dyson_account.logout()
        return None
    
    print(f"{len(devices)} appareil(s) Dyson trouvé(s)")
    
    device = devices[0]
    connected = device.auto_connect()
    
    if not connected:
        print("Erreur: Impossible de se connecter au dispositif Dyson")
        dyson_account.logout()
        return None
    
    time.sleep(3)  # Attendre les données des capteurs
    
    try:
        temperature_kelvin = device.environmental_state.temperature
        
        if temperature_kelvin is None:
            print("Erreur: Température non disponible")
            dyson_account.logout()
            return None
        
        temperature_celsius = round(temperature_kelvin - 273.15, 2)
        print(f"Température récupérée: {temperature_celsius} °C")
        
        device.disconnect()
        dyson_account.logout()
        return temperature_celsius
    
    except Exception as e:
        print(f"Erreur lors de la récupération de la température: {e}")
        device.disconnect()
        dyson_account.logout()
        return None


def write_to_google_sheet(temperature):
    """Écrire la température horodatée dans Google Sheets."""
    print("Connexion à Google Sheets...")
    
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    
    credentials_dict = os.environ['GOOGLE_CREDENTIALS_JSON']
    creds_dict = json.loads(credentials_dict)
    
    with open('credentials.json', 'w') as f:
        json.dump(creds_dict, f)
    
    credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(credentials)
    
    sheet = client.open(GOOGLE_SHEET_NAME)
    worksheet = sheet.worksheet(WORKSHEET_NAME)
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    worksheet.append_row([timestamp, temperature])
    
    print(f"Donnée insérée: {timestamp} | {temperature} °C")
    os.remove('credentials.json')


def main():
    """Fonction principale."""
    print("=" * 50)
    print("Dyson Temperature Logger - Début de l'exécution")
    print("=" * 50)
    
    temperature = get_dyson_temperature()
    
    if temperature is None:
        print("Abandon: Température non disponible")
        return
    
    try:
        write_to_google_sheet(temperature)
        print("Succès: Donnée insérée avec succès")
    except Exception as e:
        print(f"Erreur lors de l'inscription dans Google Sheets: {e}")
        return
    
    print("=" * 50)
    print("Exécution terminée avec succès")
    print("=" * 50)


if __name__ == '__main__':
    main()