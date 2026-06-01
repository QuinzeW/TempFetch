"""
Dyson Temperature Logger → Google Sheets
Récupère la température du ventilateur Dyson toutes les 30 minutes
et l'écrit dans Google Sheets avec horodatage.
"""

from libpurecool.dyson import DysonAccount
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timezone
import os
import json
import time


# --- Configuration Dyson (via secrets GitHub) ---
DYSON_EMAIL = os.environ["DYSON_EMAIL"]
DYSON_PASSWORD = os.environ["DYSON_PASSWORD"]
DYSON_LANGUAGE = "FR"  # Code langue: FR, EN, ES, etc.


# --- Configuration Google Sheets (via secrets GitHub) ---
GOOGLE_SHEET_NAME = os.environ["GOOGLE_SHEET_NAME"]
WORKSHEET_NAME = os.environ.get("GOOGLE_WORKSHEET_NAME", "Feuille1")
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]


def get_dyson_temperature():
    """
    Se connecter au compte Dyson et récupérer la température intérieure en °C.
    Retourne la température en Celsius (float) ou lève une exception en cas d'erreur.
    """
    print("Connexion au compte Dyson...")
    account = DysonAccount(DYSON_EMAIL, DYSON_PASSWORD, DYSON_LANGUAGE)
    
    if not account.login():
        raise RuntimeError("Connexion au compte Dyson impossible")
    
    devices = account.devices()
    
    if not devices:
        account.logout()
        raise RuntimeError("Aucun appareil Dyson trouvé sur ce compte")
    
    print(f"{len(devices)} appareil(s) Dyson trouvé(s)")
    
    device = devices[0]  # Premier appareil (adaptez si besoin)
    
    if not device.auto_connect():
        account.logout()
        raise RuntimeError("Connexion à l'appareil Dyson impossible")
    
    # Attendre que les données des capteurs soient disponibles
    time.sleep(3)
    
    try:
        # La température est en Kelvin dans environmental_state
        temp_kelvin = getattr(device.environmental_state, "temperature", None)
        
        if temp_kelvin is None:
            device.disconnect()
            account.logout()
            raise RuntimeError("Température non disponible")
        
        # Conversion Kelvin → Celsius
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
    """
    Écrire la température horodatée dans Google Sheets.
    """
    print("Connexion à Google Sheets...")
    
    # Charger les credentials du compte de service
    creds_info = json.loads(GOOGLE_CREDENTIALS_JSON)
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    
    # Créer les credentials pour le compte de service
    credentials = Credentials.from_service_account_info(creds_info, scopes=scopes)
    
    # Authentifier avec gspread
    client = gspread.authorize(credentials)
    
    # Ouvrir la feuille
    sheet = client.open(GOOGLE_SHEET_NAME)
    worksheet = sheet.worksheet(WORKSHEET_NAME)
    
    # Créer le timestamp UTC
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Écrire la ligne: [timestamp, température]
    worksheet.append_row([timestamp, temperature], value_input_option="USER_ENTERED")
    
    print(f"Donnée insérée: {timestamp} | {temperature} °C")


def main():
    """Fonction principale: récupérer la température et l'écrire dans Sheets."""
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