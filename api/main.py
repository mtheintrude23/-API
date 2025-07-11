import asyncio
import re
import json
from collections import defaultdict
from contextlib import asynccontextmanager

import websockets
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def combine_items_by_name(items):
    combined = defaultdict(int)
    for item in items:
        combined[item["name"]] += item.get("quantity", 0)
    return [{"name": name, "quantity": qty, "item_id": normalize_name(name)} for name, qty in combined.items()]


def clean_items(items, keys_to_keep={"name", "quantity"}):
    return [add_item_id({k: item[k] for k in keys_to_keep if k in item}) for item in items]


def normalize_name(name):
    return re.sub(r'\s+', '_', re.sub(r"[^\w\s]", "", name.strip().lower()))


def add_item_id(item):
    item["item_id"] = normalize_name(item.get("name", ""))
    return item

# ----------------------------
# Global Data Store
# ----------------------------

latest_data = {
    "weather": {},
    "gearStock": [],
    "seedsStock": [],
    "eggStock": [],
    "eventStock": [],
    "cosmeticsStock": [],
    "lastGlobalUpdate": "",
}

# ----------------------------
# WebSocket Listener
# ----------------------------

async def websocket_listener():
    uri = "wss://ws.growagardenpro.com/"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print("✅ API WebSocket Connected.")
                async for message in websocket:
                    data = json.loads(message)
                    if data.get("type"):
                        raw_data = data["data"]

                        if "weather" in raw_data:
                            latest_data["weather"] = raw_data["weather"]
                        if "gear" in raw_data:
                            latest_data["gearStock"] = clean_items(raw_data["gear"])
                        if "seeds" in raw_data:
                            latest_data["seedsStock"] = clean_items(raw_data["seeds"])
                        if "cosmetics" in raw_data:
                            latest_data["cosmeticsStock"] = clean_items(raw_data["cosmetics"])
                        if "honey" in raw_data:
                            latest_data["eventStock"] = clean_items(raw_data["honey"])
                        if "eggs" in raw_data:
                            latest_data["eggStock"] = clean_items(raw_data["eggs"])
                        if "lastGlobalUpdate" in raw_data:
                            latest_data["lastGlobalUpdate"] = raw_data["lastGlobalUpdate"]
                            
        except Exception as e:
            print(f"❌ WebSocket error: {e}. Retrying in 5s...")
            await asyncio.sleep(5)
                            
        except Exception as e:
            print(f"❌ WebSocket error: {e}. Retrying in 5s...")
            await asyncio.sleep(5)
                            
        except Exception as e:
            print(f"❌ WebSocket error: {e}. Retrying in 5s...")
            await asyncio.sleep(5)

# ----------------------------
# App Initialization
# ----------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(websocket_listener())
    yield

app = FastAPI(
    title="Grow a Garden API",
    description="Một API cung cấp dữ liệu Seeds, Gear, Egg và Weather từ Grow a Garden Roblox.",
    version="3.5.9",
    lifespan=lifespan,
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    docs_url=None,
)

# Static & CORS
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/static", StaticFiles(directory="static"), name="static")  # optional for style.css/scripts

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ----------------------------
# Custom HTML Routes (no .html in URL)
# ----------------------------

@app.get("/stocks", include_in_schema=False)
async def serve_stocks():
    return FileResponse("stock.html", media_type="text/html")

@app.get("/docs", include_in_schema=False)
async def serve_docs():
    return FileResponse("index.html", media_type="text/html")

@app.get("/api", summary="Kiểm tra sức khỏe", description="Trả về trạng thái đơn giản để xác minh API đang trực tuyến.")
@limiter.limit("5/minute")
async def root(request: Request):
    return {"status": "200"}

# ----------------------------
# API Routes
# ----------------------------

@app.get("/api/stock")
@limiter.limit("5/minute")
async def alldata(request: Request):
    return latest_data

@app.get("/api/gear")
@limiter.limit("5/minute")
async def get_gear(request: Request):
    return latest_data.get("gearStock", [])

@app.get("/api/seeds")
@limiter.limit("5/minute")
async def get_seeds(request: Request):
    return latest_data.get("seedsStock", [])

@app.get("/api/cosmetics")
@limiter.limit("5/minute")
async def get_cosmetics(request: Request):
    return latest_data.get("cosmeticsStock", [])

@app.get("/api/eventshop")
@limiter.limit("5/minute")
async def get_eventshop(request: Request):
    return latest_data.get("eventStock", [])

@app.get("/api/eggs")
@limiter.limit("5/minute")
async def get_eggs(request: Request):
    return latest_data.get("eggStock", [])

@app.get("/api/weather")
@limiter.limit("5/minute")
async def get_weather(request: Request):
    return latest_data.get("weather", {})
