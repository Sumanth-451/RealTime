from fastapi import FastAPI
import requests
import os
from dotenv import load_dotenv
from aws_requests_auth.aws_auth import AWSRequestsAuth
from datetime import datetime
import uvicorn

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


# 🔐 GET LWA ACCESS TOKEN
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


# 🏠 ROOT
@app.get("/")
def root():
    return {"message": "SP-API service is running"}


# 🚚 GET SHIPMENTS (REAL-TIME API)
@app.get("/getShipments")
def get_shipments(next_token: str = None):
    try:
        access_token = get_access_token()

        auth = AWSRequestsAuth(
            aws_access_key=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            aws_host=HOST,
            aws_region=REGION,
            aws_service=SERVICE,
        )

        headers = {
            "x-amz-access-token": access_token,
            "Content-Type": "application/json",
            "x-amz-date": datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        }

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

        if next_token:
            params = base_params + [("NextToken", next_token)]
        else:
            params = base_params

        response = requests.get(url, auth=auth, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        payload = data.get("payload", {})

        return {
            "shipments": payload.get("ShipmentData", []),
            "nextToken": payload.get("NextToken")
        }

    except requests.exceptions.HTTPError:
        return {
            "error": "Failed to fetch shipments",
            "status_code": response.status_code,
            "details": response.text
        }

    except Exception as e:
        return {"error": str(e)}


# 🔍 GET SINGLE SHIPMENT
@app.get("/getShipment/{shipment_id}")
def get_shipment(shipment_id: str):
    try:
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
            "x-amz-date": datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        }

        response = requests.get(url, auth=auth, headers=headers)
        response.raise_for_status()

        return response.json()

    except requests.exceptions.HTTPError:
        return {
            "error": "Failed to fetch shipment",
            "status_code": response.status_code,
            "details": response.text
        }

    except Exception as e:
        return {"error": str(e)}


# 📊 CREATE REPORT (YOUR NEW ENDPOINT)
@app.get("/createInboundShipmentReport")
def create_inbound_report():
    try:
        access_token = get_access_token()

        auth = AWSRequestsAuth(
            aws_access_key=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            aws_host=HOST,
            aws_region=REGION,
            aws_service=SERVICE,
        )

        url = f"https://{HOST}/reports/2021-06-30/reports"

        headers = {
            "x-amz-access-token": access_token,
            "Content-Type": "application/json"
        }

        body = {
            "reportType": "GET_FBA_FULFILLMENT_INBOUND_SHIPMENT",
            "marketplaceIds": ["ATVPDKIKX0DER"] 
        }

        response = requests.post(url, auth=auth, headers=headers, json=body)
        response.raise_for_status()

        return response.json()

    except requests.exceptions.HTTPError:
        return {
            "error": "Failed to create report",
            "status_code": response.status_code,
            "details": response.text
        }

    except Exception as e:
        return {"error": str(e)}


# 📊 GET REPORT STATUS
@app.get("/getReport/{report_id}")
def get_report(report_id: str):
    try:
        access_token = get_access_token()

        auth = AWSRequestsAuth(
            aws_access_key=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            aws_host=HOST,
            aws_region=REGION,
            aws_service=SERVICE,
        )

        url = f"https://{HOST}/reports/2021-06-30/reports/{report_id}"

        headers = {
            "x-amz-access-token": access_token
        }

        response = requests.get(url, auth=auth, headers=headers)
        response.raise_for_status()

        return response.json()

    except Exception as e:
        return {"error": str(e)}


# 📊 GET REPORT DOCUMENT
@app.get("/getDocument/{document_id}")
def get_document(document_id: str):
    try:
        access_token = get_access_token()

        auth = AWSRequestsAuth(
            aws_access_key=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            aws_host=HOST,
            aws_region=REGION,
            aws_service=SERVICE,
        )

        url = f"https://{HOST}/reports/2021-06-30/documents/{document_id}"

        headers = {
            "x-amz-access-token": access_token
        }

        response = requests.get(url, auth=auth, headers=headers)
        response.raise_for_status()

        return response.json()

    except Exception as e:
        return {"error": str(e)}


# ▶️ RUN SERVER
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
