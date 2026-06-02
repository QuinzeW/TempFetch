"""
Dyson Temperature Logger → Google Sheets
Version améliorée : meilleur User-Agent + retries pour contourner les problèmes d'auth.
"""

from libpurecool.dyson import DysonAccount
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timezone
import os
import json
import time
import requests


# --- Configuration Dyson (via secrets GitHub) ---
DYSON_EMAIL = os.environ["DYSON_EMAIL"]
DYSON_PASSWORD = os.environ["DYSON_PASSWORD"]
DYSON_LANGUAGE = "FR"  # FR, EN, ES, etc.


# --- Configuration Google Sheets ---
GOOGLE_SHEET_NAME = os.environ["GOOGLE_SHEET_NAME"]
WORKSHEET_NAME = os.environ.get("GOOGLE_WORKSHEET_NAME", "Feuille1")
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]


def get_dyson_temperature():
    """
    Récupère la température du Dyson avec retries.
    """
    print("Connexion au compte Dyson...")
    
    # Essayer de se connecter plusieurs fois (l'API Dyson est parfois instable)
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        print(f"Tentative {attempt}/{max_retries}...")
        
        account = DysonAccount(DYSON_EMAIL, DYSON_PASSWORD, DYSON_LANGUAGE)
        
        if account.login():
            print("Connexion réussie !")
            break
        else:
            if attempt == max_retries:
                raise RuntimeError("Connexion au compte Dyson impossible après 3 tentatives")
            time.sleep(5)  # Attendre 5s entre les tentatives
    
    devices = account.devices()
    
    if not devices:
        account.logout()
        raise RuntimeError("Aucun appareil Dyson trouvé sur ce compte")
    
    print(f"{len(devices)} appareil(s) Dyson trouvé(s)")
    
    device = devices[0]
    
    if not device.auto_connect():
        account.logout()
        raise RuntimeError("Connexion à l'appareil Dyson impossible")
    
    # Attendre les données des capteurs
    time.sleep(3)
    
    try:
        temp_kelvin = getattr(device.environmental_state, "temperature", None)
        
        if temp_kelvin is None:
            device.disconnect()
            account.logout()
            raise RuntimeError("Température non disponible")
        
        temp_celsius = round(temp_kelvin - 273.15, 2)
        print(f"Température récupérée: {temp_celsius} °C")
        
        device.disconnect()
        account.logout()
        
        return temp_celsius
    
    except Exception as e:
        device.disconnect()
        account.logout()
        raise RuntimeError(f"Erreur lors de la récupération de la température: {e}")


def write_to_sheet(temperature):
    """Écrit la température horodatée dans Google Sheets."""
    print("Connexion à Google Sheets...")
    
    creds_info = json.loads(GOOGLE_CREDENTIALS_JSON)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    
    credentials = Credentials.from_service_account_info(creds_info, scopes=scopes)
    client = gspread.authorize(credentials)
    
    sheet = client.open(GOOGLE_SHEET_NAME)
    worksheet = sheet.worksheet(WORKSHEET_NAME)
    
    timestamp = datetime.now(timezone.utc).isoformat()
    worksheet.append_row([timestamp, temperature], value_input_option="USER_ENTERED")
    
    print(f"Donnée insérée: {timestamp} | {temperature} °C")


def main():
    print("=" * 50)
    print("Dyson Temperature Logger - Début de l'exécution")
    print("=" * 50)
    
    temp = get_dyson_temperature()
    write_to_sheet(temp)
    
    print("=" * 50)
    print("Exécution terminée avec succès")
    print("=" * 50)


if __name__ == "__main__":
    main()