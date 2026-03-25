from fastapi import FastAPI, Query
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

# ✅ INCLUDE WORKING STATUS
TRACKING_STATUSES = [
    "WORKING",
    "READY_TO_SHIP",
    "SHIPPED",
    "IN_TRANSIT",
    "DELIVERED",
    "RECEIVING",
    "CLOSED"
]


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


# 🔐 AUTH
def get_auth():
    return AWSRequestsAuth(
        aws_access_key=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        aws_host=HOST,
        aws_region=REGION,
        aws_service=SERVICE,
    )


# 🔐 HEADERS
def get_headers(access_token):
    return {
        "x-amz-access-token": access_token,
        "Content-Type": "application/json",
        "x-amz-date": datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    }


# 🧠 ENRICH SHIPMENT DATA
def enrich_shipment(shipment):
    status = shipment.get("ShipmentStatus")

    return {
        "shipmentId": shipment.get("ShipmentId"),
        "shipmentName": shipment.get("ShipmentName"),
        "status": status,
        "labelPrepType": shipment.get("LabelPrepType"),
        "destinationFC": shipment.get("DestinationFulfillmentCenterId"),
        "areCasesRequired": shipment.get("AreCasesRequired"),
        "shipmentType": shipment.get("ShipmentType"),
        # ✅ fallback fix
        "lastUpdated": shipment.get("LastUpdatedDate") or shipment.get("CreatedDate"),
        "isMoving": status in ["SHIPPED", "IN_TRANSIT"],
        "isCompleted": status in ["DELIVERED", "CLOSED"]
    }


# 🚀 MAIN REALTIME ENDPOINT
@app.get("/getShipmentsRealtime")
def get_shipments_realtime(
    last_updated_after: str = Query(None),
    max_pages: int = 2,
    include_items: bool = False
):
    try:
        access_token = get_access_token()
        auth = get_auth()
        headers = get_headers(access_token)

        url = f"https://{HOST}/fba/inbound/v0/shipments"

        base_params = [
            *[("ShipmentStatusList", s) for s in TRACKING_STATUSES],
            ("MarketplaceId", "ATVPDKIKX0DER")
        ]

        if last_updated_after:
            base_params.append(("LastUpdatedAfter", last_updated_after))

        all_shipments = []
        seen_shipments = set()

        next_token = None
        pages_fetched = 0

        while pages_fetched < max_pages:
            params = base_params + ([("NextToken", next_token)] if next_token else [])

            # 🔁 RATE LIMIT HANDLING
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

            for shipment in shipments:
                shipment_id = shipment.get("ShipmentId")

                # ✅ DEDUPLICATION
                if shipment_id in seen_shipments:
                    continue

                seen_shipments.add(shipment_id)

                enriched = enrich_shipment(shipment)

                # 📦 OPTIONAL ITEMS
                if include_items:
                    enriched["items"] = get_shipment_items(
                        shipment_id,
                        auth,
                        headers
                    )

                all_shipments.append(enriched)

            next_token = payload.get("NextToken")
            pages_fetched += 1

            if not next_token:
                break

            time.sleep(0.5)

        return {
            "count": len(all_shipments),
            "shipments": all_shipments
        }

    except Exception as e:
        return {"error": str(e)}


# 📦 GET SHIPMENT ITEMS
def get_shipment_items(shipment_id, auth, headers):
    try:
        url = f"https://{HOST}/fba/inbound/v0/shipments/{shipment_id}/items"

        response = requests.get(url, auth=auth, headers=headers)
        response.raise_for_status()

        payload = response.json().get("payload", {})
        items = payload.get("ItemData", [])

        return [
            {
                "sku": item.get("FulfillmentNetworkSKU"),
                "quantityShipped": item.get("QuantityShipped"),
                "quantityReceived": item.get("QuantityReceived"),
                "difference": (
                    item.get("QuantityShipped", 0)
                    - item.get("QuantityReceived", 0)
                )
            }
            for item in items
        ]

    except Exception as e:
        return [{"error": str(e)}]


# 🏠 ROOT
@app.get("/")
def root():
    return {"message": "SP-API realtime service running"}


# ▶️ RUN SERVER
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
