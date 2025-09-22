from fastapi import FastAPI, Depends, HTTPException, status,Request,Header
from sqlalchemy.orm import Session
#from . import models, schemas, crud, database
import models
import schemas
import crud
import database
import requests
from jose import JWTError, jwt
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from datetime import datetime
from dotenv import load_dotenv
import os
from logging_config import setup_logger
from contextlib import asynccontextmanager
import time
from prometheus_fastapi_instrumentator import Instrumentator

from services import validate_current_user



logger = setup_logger("order_service")
models.Base.metadata.create_all(bind=database.engine)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

#logging       
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Service starting up...")
    
    # Instrument Prometheus metrics

    logger.info("Monitoring instrumentator started")

    yield

    # Shutdown
    logger.info("Service shutting down")



app = FastAPI(title="Order Service", lifespan=lifespan)
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)
#health check
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

# JWT CONFIG

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "mysecret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

oauth2_scheme = HTTPBearer(auto_error=True)



# UTILS

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"id": int(user_id)}   #  return a dict, not just string
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ROUTES
POD_NAME = os.getenv("HOSTNAME")
@app.get("/orders/test")
def orders_test():
    logger.info("Orders test endpoint called")
    return {"pod": POD_NAME}

oauth2_scheme = HTTPBearer(auto_error=True)
@app.get("/test-current-user")
async def test_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=401, detail="Token missing")
    
    try:
        user_data = await validate_current_user(token)
        return {"user_data": user_data}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/orders/", response_model=schemas.OrderResponse)
async def create_order(
    order: schemas.OrderCreate,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)
):
    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=401, detail="Token missing")

    # Validate user via User Service
    user_data = await validate_current_user(token)
    
    return crud.create_order(db, order, user_data["id"])



@app.get("/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.user_id == current_user["id"]  
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order




@app.get("/orders/me", response_model=list[schemas.OrderResponse])
def read_my_orders(
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)
):
    return crud.get_orders_by_user(db, current_user["id"])


@app.put("/orders/{order_id}", response_model=schemas.OrderResponse)
def update_order(
    order_id: int,
    update_data: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    updated_order = crud.update_order(db, order_id, current_user["id"], update_data)
    if not updated_order:
        raise HTTPException(status_code=404, detail="Order not found or not yours")
    return updated_order


@app.delete("/orders/{order_id}", response_model=schemas.OrderResponse)
def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    deleted_order = crud.delete_order(db, order_id, current_user["id"])
    if not deleted_order:
        raise HTTPException(status_code=404, detail="Order not found or not yours")
    return deleted_order


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001,reload=True)
