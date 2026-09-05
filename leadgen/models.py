# leadgen/models_db.py
from sqlalchemy import Column, Integer, String
from .database import Base

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    business_type = Column(String, nullable=True)
    service_needed = Column(String, nullable=True)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(String, nullable=True)
    image = Column(String, nullable=True)
    category = Column(String, nullable=True)