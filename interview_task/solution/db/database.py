import os
from dotenv import load_dotenv
from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import Session, DeclarativeBase
from typing import Annotated
load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]


engine = create_async_engine(DATABASE_URL)

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db

        
db_dependency = Annotated[AsyncSession, Depends(get_db)]