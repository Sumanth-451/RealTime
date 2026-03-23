from fastapi import FastAPI
import requests
import os
from dotenv import load_dotenv
from aws_requests_auth.aws_auth import AWSRequestsAuth

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# 🔐 Load credentials from environment variables
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")

REGION = "us-east-1"
HOST = "sellingpartnerapi-na.amazon.com"
SERVICE = "execute-api"

# ✅ Step 1: Get Access Token

def get_access_token():
    url = "https://api.amazon.com/auth/o2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json().get("access_token")

# ✅ Step 2: Get Shipments

@app.get("/")
def root():
    return {"message": "SP-API service is running. Use /getShipments or /getShipment/{shipment_id}."}

@app.get("/getShipments")
def get_shipments():
    access_token = get_access_token()
    auth = AWSRequestsAuth(
        aws_access_key=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        aws_host=HOST,
        aws_region=REGION,
        aws_service=SERVICE,
    )

    url = f"https://{HOST}/fba/inbound/v0/shipments"
    headers = {
        "x-amz-access-token": access_token,
        "Content-Type": "application/json",
    }
    params = {
        "ShipmentStatusList": "WORKING,SHIPPED,IN_TRANSIT",
    }

    response = requests.get(url, auth=auth, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

# ✅ Step 3: Get Shipment Details

@app.get("/getShipment/{shipment_id}")
def get_shipment(shipment_id: str):
    access_token = get_access_token()
    auth = AWSRequestsAuth(
        aws_access_key=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        aws_host=HOST,
        aws_region=REGION,
        aws_service=SERVICE,
    )

    url = f"https://{HOST}/fba/inbound/v0/shipments/{shipment_id}"
    headers = {
        "x-amz-access-token": access_token,
        "Content-Type": "application/json",
    }

    response = requests.get(url, auth=auth, headers=headers)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        return {"error": "shipment request failed", "status_code": response.status_code, "body": response.text}
    return response.json()
