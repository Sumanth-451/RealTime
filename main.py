from fastapi import FastAPI
import requests
import os
from dotenv import load_dotenv
from aws_requests_auth.aws_auth import AWSRequestsAuth
from datetime import datetime

# Load environment variables

load_dotenv()

app = FastAPI()

# 🔐 Environment Variables

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")

# ✅ US Region

REGION = "us-east-1"
HOST = "sellingpartnerapi-na.amazon.com"
SERVICE = "execute-api"

MARKETPLACE_ID = "ATVPDKIKX0DER"

# ✅ Step 1: Get LWA Access Token

def get_access_token():
url = "https://api.amazon.com/auth/o2/token"

```
data = {
    "grant_type": "refresh_token",
    "refresh_token": REFRESH_TOKEN,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
}

try:
    response = requests.post(url, data=data)
    response.raise_for_status()

    token = response.json().get("access_token")

    if not token:
        raise Exception("No access token received")

    return token

except Exception as e:
    print("❌ Token Error:", str(e))
    raise
```

# ✅ Health Check

@app.get("/")
def root():
return {"message": "SP-API service is running 🚀"}

# ✅ Step 2: Get Shipments

@app.get("/getShipments")
def get_shipments():
try:
access_token = get_access_token()

```
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
        "x-amz-date": datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    }

    params = {
        "ShipmentStatusList": "WORKING,SHIPPED,IN_TRANSIT",
        "MarketplaceId": MARKETPLACE_ID
    }

    response = requests.get(url, auth=auth, headers=headers, params=params)

    print("📦 Shipments Response:", response.text)

    response.raise_for_status()
    return response.json()

except requests.exceptions.HTTPError:
    return {
        "error": "Failed to fetch shipments",
        "status_code": response.status_code,
        "details": response.text
    }
except Exception as e:
    return {"error": str(e)}
```

# ✅ Step 3: Get Shipment by ID

@app.get("/getShipment/{shipment_id}")
def get_shipment(shipment_id: str):
try:
access_token = get_access_token()

```
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

    params = {
        "MarketplaceId": MARKETPLACE_ID
    }

    response = requests.get(url, auth=auth, headers=headers, params=params)

    print(f"📦 Shipment {shipment_id} Response:", response.text)

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
```
