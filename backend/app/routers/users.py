from fastapi import APIRouter, HTTPException
from ..config import EMBY_URL, HEADERS
import httpx

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("")
async def get_users():
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{EMBY_URL}/Users/Public",
            headers=HEADERS
        )
        resp.raise_for_status()
        users_data = resp.json()

        users = []
        for u in users_data:
            user_id = u.get("Id")
            detail_resp = await client.get(
                f"{EMBY_URL}/Users/{user_id}",
                headers=HEADERS
            )
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
