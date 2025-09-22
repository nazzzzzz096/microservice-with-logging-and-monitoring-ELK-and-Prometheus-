from sqlalchemy.orm import Session
#from . import models, schemas
import models
import schemas

def create_order(db: Session, order: schemas.OrderCreate,user_id:int):
    db_order = models.Order(
        user_id=user_id,
        product=order.product,
        quantity=order.quantity,
        status="pending"
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

def get_order(db: Session, order_id: int):
    return db.query(models.Order).filter(models.Order.id == order_id).first()

def get_orders_by_user(db: Session, user_id: int):
    return db.query(models.Order).filter(models.Order.user_id == user_id).all()

def update_order(db: Session, order_id: int, user_id: int, update_data: schemas.OrderCreate):
    order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.user_id == user_id
    ).first()
    if not order:
        return None

    order.product = update_data.product
    order.quantity = update_data.quantity
    db.commit()
    db.refresh(order)
    return order


def delete_order(db: Session, order_id: int, user_id: int):
    order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.user_id == user_id
    ).first()
    if not order:
        return None

    db.delete(order)
    db.commit()
    return order