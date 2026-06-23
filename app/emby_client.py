import httpx
from .config import EMBY_URL, EMBY_API_KEY

def _headers():
    return {"X-MediaBrowser-Token": EMBY_API_KEY}

async def _get(path: str, params: dict = None):
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{EMBY_URL}{path}", headers=_headers(), params=params)
        r.raise_for_status()
        return r.json()

async def _post(path: str, data: dict = None):
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{EMBY_URL}{path}", headers=_headers(), json=data)
        r.raise_for_status()
        return r.json() if r.text else {}

async def _delete(path: str):
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.delete(f"{EMBY_URL}{path}", headers=_headers())
        r.raise_for_status()

# --- System ---
async def get_server_info():
    return await _get("/System/Info")

# --- Users ---
async def get_users():
    return await _get("/Users")

async def get_user(user_id: str):
    return await _get(f"/Users/{user_id}")

async def create_user(name: str):
    return await _post("/Users/New", {"Name": name})

async def delete_user(user_id: str):
    return await _delete(f"/Users/{user_id}")

async def set_user_password(user_id: str, current_pw: str, new_pw: str):
    return await _post(f"/Users/{user_id}/Password", {
        "Id": user_id,
        "CurrentPw": current_pw,
        "NewPw": new_pw,
    })

async def set_user_policy(user_id: str, policy: dict):
    return await _post(f"/Users/{user_id}/Policy", policy)

# --- Libraries ---
async def get_virtual_folders():
    return await _get("/Library/VirtualFolders")

async def get_items_counts():
    return await _get("/Items/Counts")

async def get_items(user_id: str, params: dict):
    return await _get(f"/Users/{user_id}/Items", params)

# --- Activity ---
async def get_sessions():
    return await _get("/Sessions")

async def get_scheduled_tasks():
    return await _get("/ScheduledTasks")

async def get_activities(limit: int = 20):
    return await _get("/System/ActivityLog/Entries", {"Limit": limit})
