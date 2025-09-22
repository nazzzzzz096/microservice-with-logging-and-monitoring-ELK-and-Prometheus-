import httpx
from fastapi import HTTPException



async def validate_current_user(token: str):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.post("http://user-service:8000/verify-token", headers=headers)

        print("DEBUG:", response.status_code, response.text) 
        response.raise_for_status()
        return response.json() 