from fastapi import FastAPI
import requests
import os
from dotenv import load_dotenv
from aws_requests_auth.aws_auth import AWSRequestsAuth
from datetime import datetime
import uvicorn
import time

load_dotenv()

app = FastAPI()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")

REGION = "us-east-1"
HOST = "sellingpartnerapi-na.amazon.com"
SERVICE = "execute-api"


# 🔐 GET ACCESS TOKEN
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

    token = response.json().get("access_token")
    if not token:
        raise Exception("No access token received")

    return token


# 🔐 AUTH + HEADERS
def get_auth():
    return AWSRequestsAuth(
        aws_access_key=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        aws_host=HOST,
        aws_region=REGION,
        aws_service=SERVICE,
    )


def get_headers(access_token):
    return {
        "x-amz-access-token": access_token,
        "Content-Type": "application/json",
        "x-amz-date": datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    }


# 🏠 ROOT
@app.get("/")
def root():
    return {"message": "SP-API service is running"}


# 🚚 GET SINGLE PAGE (OPTIONAL)
@app.get("/getShipments")
def get_shipments(next_token: str = None):
    try:
        access_token = get_access_token()
        auth = get_auth()
        headers = get_headers(access_token)

        url = f"https://{HOST}/fba/inbound/v0/shipments"

        base_params = [
            ("ShipmentStatusList", "READY_TO_SHIP"),
            ("ShipmentStatusList", "SHIPPED"),
            ("ShipmentStatusList", "IN_TRANSIT"),
            ("ShipmentStatusList", "DELIVERED"),
            ("ShipmentStatusList", "CHECKED_IN"),
            ("ShipmentStatusList", "RECEIVING"),
            ("ShipmentStatusList", "CLOSED"),
            ("ShipmentStatusList", "CANCELLED"),
            ("ShipmentStatusList", "DELETED"),
            ("MarketplaceId", "ATVPDKIKX0DER")
        ]

        params = base_params + ([("NextToken", next_token)] if next_token else [])

        response = requests.get(url, auth=auth, headers=headers, params=params)
        response.raise_for_status()

        payload = response.json().get("payload", {})

        return {
            "shipments": payload.get("ShipmentData", []),
            "nextToken": payload.get("NextToken")
        }

    except Exception as e:
        return {"error": str(e)}


# 🚀 FINAL: BATCH PAGINATION (NO TIMEOUT)
@app.get("/getShipmentsBatch")
def get_shipments_batch(max_pages: int = 3, next_token: str = None):
    try:
        access_token = get_access_token()
        auth = get_auth()
        headers = get_headers(access_token)

        url = f"https://{HOST}/fba/inbound/v0/shipments"

        base_params = [
            ("ShipmentStatusList", "WORKING"),
            ("ShipmentStatusList", "READY_TO_SHIP"),
            ("ShipmentStatusList", "SHIPPED"),
            ("ShipmentStatusList", "IN_TRANSIT"),
            ("ShipmentStatusList", "DELIVERED"),
            ("ShipmentStatusList", "CHECKED_IN"),
            ("ShipmentStatusList", "RECEIVING"),
            ("ShipmentStatusList", "CLOSED"),
            ("ShipmentStatusList", "CANCELLED"),
            ("ShipmentStatusList", "DELETED"),
            ("MarketplaceId", "ATVPDKIKX0DER")
        ]

        all_shipments = []
        pages_fetched = 0

        while pages_fetched < max_pages:
            params = base_params + ([("NextToken", next_token)] if next_token else [])

            # 🔁 HANDLE RATE LIMIT
            for attempt in range(5):
                response = requests.get(url, auth=auth, headers=headers, params=params)

                if response.status_code == 429:
                    wait_time = 2 ** attempt
                    print(f"Rate limited. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()
                break

            payload = response.json().get("payload", {})

            shipments = payload.get("ShipmentData", [])
            all_shipments.extend(shipments)

            next_token = payload.get("NextToken")
            pages_fetched += 1

            if not next_token:
                break

            # ✅ SAFE DELAY BETWEEN CALLS
            time.sleep(0.6)

        return {
            "shipments": all_shipments,
            "nextToken": next_token
        }

    except Exception as e:
        return {"error": str(e)}


# 🔍 GET SINGLE SHIPMENT
@app.get("/getShipment/{shipment_id}")
def get_shipment(shipment_id: str):
    try:
        access_token = get_access_token()
        auth = get_auth()
        headers = get_headers(access_token)

        url = f"https://{HOST}/fba/inbound/v0/shipments/{shipment_id}"

        response = requests.get(url, auth=auth, headers=headers)
        response.raise_for_status()

        return response.json()

    except Exception as e:
        return {"error": str(e)}


# ▶️ RUN SERVER
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
