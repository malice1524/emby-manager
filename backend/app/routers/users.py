from fastapi import APIRouter, Query, HTTPException
from ..config import EMBY_URL, HEADERS
import httpx

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("")
async def get_users():
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{EMBY_URL}/Users/Public", headers=HEADERS)
        resp.raise_for_status()
        users_data = resp.json()

        users = []
        for u in users_data:
            user_id = u.get("Id")
            detail_resp = await client.get(f"{EMBY_URL}/Users/{user_id}", headers=HEADERS)
            if detail_resp.status_code == 200:
                detail = detail_resp.json()
                policy = detail.get("Policy", {})
                users.append({
                    "id": user_id,
                    "name": u.get("Name", "Unknown"),
                    "has_password": detail.get("HasPassword", False),
                    "is_admin": policy.get("IsAdministrator", False),
                    "is_disabled": policy.get("IsDisabled", False),
                    "last_login": detail.get("LastLoginDate", ""),
                    "last_active": detail.get("LastActivityDate", ""),
                    "created": detail.get("DateCreated", ""),
                })

        return {"users": users}


@router.post("")
async def create_user(name: str = Query(...)):
    """Create a new Emby user."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{EMBY_URL}/emby/Users/New",
            params={"Name": name},
            headers=HEADERS,
        )
        if resp.status_code not in (200, 204):
            raise HTTPException(status_code=resp.status_code, detail="Failed to create user")
        return {"status": "ok"}


@router.delete("/{user_id}")
async def delete_user(user_id: str):
    """Delete an Emby user."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.delete(
            f"{EMBY_URL}/emby/Users/{user_id}",
            headers=HEADERS,
        )
        if resp.status_code not in (200, 204):
            raise HTTPException(status_code=resp.status_code, detail="Failed to delete user")
        return {"status": "ok"}


@router.put("/{user_id}/password")
async def set_password(user_id: str, body: dict):
    """Set user password."""
    new_pw = body.get("new_pw", "")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{EMBY_URL}/emby/Users/{user_id}/Password",
            json={"NewPw": new_pw},
            headers=HEADERS,
        )
        if resp.status_code not in (200, 204):
            raise HTTPException(status_code=resp.status_code, detail="Failed to set password")
        return {"status": "ok"}


@router.put("/{user_id}/policy")
async def update_policy(user_id: str, body: dict):
    """Update user policy (e.g. IsDisabled)."""
    async with httpx.AsyncClient(timeout=15) as client:
        # First get current policy
        detail = await client.get(f"{EMBY_URL}/Users/{user_id}", headers=HEADERS)
        detail.raise_for_status()
        current = detail.json().get("Policy", {})

        # Merge with new values
        current.update(body)

        resp = await client.post(
            f"{EMBY_URL}/emby/Users/{user_id}/Policy",
            json=current,
            headers=HEADERS,
        )
        if resp.status_code not in (200, 204):
            raise HTTPException(status_code=resp.status_code, detail="Failed to update policy")
        return {"status": "ok"}
