from pydantic import BaseModel

class OrderBase(BaseModel):
    
    product: str
    quantity: int

class OrderCreate(OrderBase):
    pass

class OrderResponse(OrderBase):
    id: int
    user_id:int
    status: str

    class Config:
        from_attributes = True