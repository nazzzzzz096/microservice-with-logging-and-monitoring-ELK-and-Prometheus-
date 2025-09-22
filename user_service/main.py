from fastapi import FastAPI,Request
#from . import models, database, routes
import models
import database
import routes
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials,HTTPBearer
from jose import jwt, JWTError,ExpiredSignatureError
from sqlalchemy.orm import Session
#from . import database, models
from dotenv import load_dotenv
import os
from contextlib import asynccontextmanager
from logging_config import setup_logger

from prometheus_fastapi_instrumentator import Instrumentator



import time

logger = setup_logger("user_service")   

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Service starting up...")
    

    logger.info("Monitoring instrumentator started")

    yield

    # Shutdown
    logger.info("Service shutting down")


app = FastAPI(title="User Service",lifespan=lifespan)
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

POD_NAME = os.getenv("HOSTNAME")  

@app.get("/users/test")
def users_test():
    logger.info("Users test endpoint called")
    return {"pod": POD_NAME}

@app.get("/health")
def health_check():
    logger.info("Health check called")
    return {"status": "ok"}

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    logger.info(f"Incoming request: {request.method} {request.url}")

    response = await call_next(request)

    duration = time.time() - start_time
    logger.info(
        f"Completed {request.method} {request.url} "
        f"status={response.status_code} duration={duration:.2f}s"
    )

    return response

# Create tables
models.Base.metadata.create_all(bind=database.engine)

# Include routes
app.include_router(routes.router, prefix="/users", tags=["Users"])


load_dotenv()





SECRET_KEY = os.getenv("SECRET_KEY", "mysecret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

oauth2_scheme = HTTPBearer(auto_error=True)

@app.post("/verify-token")
def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db)
):
    token = credentials.credentials  

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Token missing 'sub' claim")

        user = db.query(models.User).filter(models.User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return {"id": user.id, "email": user.email}

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}") 
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000,reload=True)
