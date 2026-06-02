"""
Dyson Temperature Logger → Google Sheets
Version avec libdyson (bibliothèque plus récente maintenue)
"""

import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timezone
import os
import json
import time
import requests


# --- Configuration Dyson ---
DYSON_EMAIL = os.environ["DYSON_EMAIL"]
DYSON_PASSWORD = os.environ["DYSON_PASSWORD"]
DYSON_COUNTRY = os.environ.get("DYSON_COUNTRY", "224")  # 224 = Rest of World, 86 = China
DYSON_REGION = os.environ.get("DYSON_REGION", "2")  # 1 = China, 2 = Rest of World


# --- Configuration Google Sheets ---
GOOGLE_SHEET_NAME = os.environ["GOOGLE_SHEET_NAME"]
WORKSHEET_NAME = os.environ.get("GOOGLE_WORKSHEET_NAME", "Feuille1")
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]


def dyson_cloud_login(email, password, country="224"):
    """
    Se connecter à l'API Dyson Cloud pour obtenir les credentials.
    Retourne (account, password) ou lève une exception.
    """
    url = f"https://appapi.cp.dyson.com/v1/userregistration/authenticate?country={country}"
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "DysonApp/4.20.0 (iOS 15.0; iPhone13,1)",
        "Accept": "application/json"
    }
    
    payload = {
        "Email": email,
        "Password": password
    }
    
    response = requests.post(url, headers=headers, json=payload, verify=False)
    
    if response.status_code != 200:
        raise RuntimeError(f"Login Dyson échoué: HTTP {response.status_code} - {response.text}")
    
    data = response.json()
    
    if "Account" not in data or "Password" not in data:
        raise RuntimeError(f"Réponse Dyson invalide: {data}")
    
    return data["Account"], data["Password"]


def get_dyson_devices(account, auth_password):
    """
    Récupérer la liste des appareils Dyson connectés.
    Retourne une liste de devices.
    """
    url = "https://appapi.cp.dyson.com/v1/provisioningservice/manifest/devices"
    
    headers = {
        "User-Agent": "DysonApp/4.20.0 (iOS 15.0; iPhone13,1)",
        "Accept": "application/json",
        "Authorization": f"Basic {account}:{auth_password}"
    }
    
    response = requests.get(url, headers=headers, verify=False)
    
    if response.status_code != 200:
        raise RuntimeError(f"Récupération appareils échouée: HTTP {response.status_code}")
    
    return response.json()


def get_dyson_temperature(account, auth_password, device_serial, product_type):
    """
    Récupérer la température d'un appareil Dyson via l'API cloud.
    Retourne la température en °C (float).
    """
    # L'API cloud ne donne pas directement la température en temps réel.
    # On utilise l'ID de l'appareil pour obtenir le statut.
    
    # Note: Pour les appareils Dyson, la température est souvent disponible
    # via l'API MQTT locale, mais pour le cloud, on utilise le statut last-known.
    
    # Pour simplifier, on utilise l'API REST pour obtenir le statut de l'appareil
    url = f"https://appapi.cp.dyson.com/v2/devices/{device_serial}/liveStatus"
    
    headers = {
        "User-Agent": "DysonApp/4.20.0 (iOS 15.0; iPhone13,1)",
        "Accept": "application/json",
        "Authorization": f"Basic {account}:{auth_password}"
    }
    
    response = requests.get(url, headers=headers, verify=False)
    
    if response.status_code != 200:
        raise RuntimeError(f"Récupération température échouée: HTTP {response.status_code}")
    
    data = response.json()
    
    try:
        # La température est dans StatusEnv.Tmp (en Kelvin)
        temp_kelvin = data["StatusEnv"]["Tmp"]
        temp_celsius = round(temp_kelvin - 273.15, 2)
        return temp_celsius
    except (KeyError, TypeError) as e:
        # Fallback: essayer d'autres chemins
        try:
            temp_kelvin = data["environmental"]["temperature"]
            temp_celsius = round(temp_kelvin - 273.15, 2)
            return temp_celsius
        except (KeyError, TypeError):
            raise RuntimeError(f"Température non trouvée dans la réponse: {data}")


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
    
    # 1. Se connecter à l'API Dyson Cloud
    print("Connexion au compte Dyson...")
    account, auth_password = dyson_cloud_login(DYSON_EMAIL, DYSON_PASSWORD, DYSON_COUNTRY)
    print("Connexion réussie !")
    
    # 2. Récupérer la liste des appareils
    print("Récupération des appareils...")
    devices = get_dyson_devices(account, auth_password)
    
    if not devices:
        raise RuntimeError("Aucun appareil Dyson trouvé")
    
    print(f"{len(devices)} appareil(s) Dyson trouvé(s)")
    
    # 3. Utiliser le premier appareil (adaptez si besoin)
    device = devices[0]
    device_serial = device["Serial"]
    product_type = device["ProductType"]
    
    print(f"Appareil: {device['Name']} (Serial: {device_serial}, Type: {product_type})")
    
    # 4. Récupérer la température
    print("Récupération de la température...")
    temp = get_dyson_temperature(account, auth_password, device_serial, product_type)
    print(f"Température: {temp} °C")
    
    # 5. Écrire dans Google Sheets
    write_to_sheet(temp)
    
    print("=" * 50)
    print("Exécution terminée avec succès")
    print("=" * 50)


if __name__ == "__main__":
    main()