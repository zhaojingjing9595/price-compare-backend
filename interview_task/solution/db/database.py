import os
from dotenv import load_dotenv
from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase
from typing import Annotated
load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]


engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
db_dependency = Annotated[Session, Depends(get_db)]