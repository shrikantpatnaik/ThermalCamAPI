import secrets
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Annotated

from sqlalchemy.exc import IntegrityError

from fastapi import FastAPI, Depends, Query, HTTPException, status
from sqlmodel import SQLModel, create_engine, Session, select
import datetime

from config import Settings
from models import APIKeys, CamDataWithoutData, CamData


# noinspection PyArgumentList
@lru_cache
def get_settings() -> Settings:
    return Settings()

# String format: postgresql://user:password@host:5432/dbname
engine = create_engine(get_settings().postgres_string)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        if len(session.exec(select(APIKeys)).all()) < 1:
            a = APIKeys(name="admin", key=secrets.token_urlsafe(get_settings().API_key_size), disabled=False, admin=True)
            session.add(a)
            session.commit()
            session.refresh(a)
            print("##################################################")
            print("The Admin API Key is:", a.key)
            print("##################################################")


def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]


def check_api_key(api_key: str):
    with Session(engine) as session:
        # noinspection PyTypeChecker
        key = session.exec(select(APIKeys).where(APIKeys.key == api_key)).first()
        if not key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is invalid",
            )
        if key.disabled:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is disabled",
            )
        return key


# noinspection PyUnusedLocal
@asynccontextmanager
async def lifespan(api_app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/data", dependencies=[Depends(check_api_key)])
def read_datas(session: SessionDep, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100,
              start: float | None = None, end: float | None = None, ) -> list[CamDataWithoutData]:
    if start is None:
        start = datetime.datetime.now() - datetime.timedelta(days=30)
    else:
        start = datetime.datetime.fromtimestamp(start)
    if end is None:
        end = datetime.datetime.now()
    else:
        end = datetime.datetime.fromtimestamp(end)

    statement = (select(CamData).where(CamData.timestamp > start, CamData.timestamp < end)
                 .offset(offset).limit(limit))
    # noinspection PyTypeChecker
    datas = session.exec(statement).all()
    return datas
@app.get("/data/{data_id}", dependencies=[Depends(check_api_key)])
def read_data(data_id:int, session: SessionDep) -> type[CamData]:
    data = session.get(CamData, data_id)
    if not data:
        raise HTTPException(status_code=404, detail="Data not found")
    return data
@app.post("/data", dependencies=[Depends(check_api_key)])
def create_data(cam_data: CamData, session: SessionDep) -> CamData:
    print("Creating data")
    session.add(cam_data)
    session.commit()
    session.refresh(cam_data)
    return cam_data

@app.post('/api_key')
def create_api_key(api_key_data: APIKeys, session: SessionDep, api_key: Annotated[APIKeys, Depends(check_api_key)]) -> APIKeys:
    if not api_key.admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Need to be admin")
    api_key_data.key = secrets.token_urlsafe(get_settings().API_key_size)
    try:
        session.add(api_key_data)
        session.commit()
        session.refresh(api_key_data)
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error.args[0],
        )
    return api_key_data

@app.get("/api_keys/{key}")
def get_api_key(key: str, session: SessionDep, api_key: Annotated[APIKeys, Depends(check_api_key)]) -> APIKeys:
    if not api_key.admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Need to be admin")
    # noinspection PyTypeChecker
    found_api_key = session.exec(select(APIKeys).where(APIKeys.key == key)).first()
    if not found_api_key:
        raise HTTPException(status_code=404, detail="Key not found")
    return found_api_key

@app.delete("/api_keys/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(key: str, session: SessionDep, api_key: Annotated[APIKeys, Depends(check_api_key)]):
    if not api_key.admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Need to be admin")
    # noinspection PyTypeChecker
    found_api_key = session.exec(select(APIKeys).where(APIKeys.key == key)).first()
    if not found_api_key:
        raise HTTPException(status_code=404, detail="Key not found")
    session.delete(found_api_key)
    session.commit()
    return None

