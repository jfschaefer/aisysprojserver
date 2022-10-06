from sqlalchemy import Column, String, create_engine, Integer
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from aisysprojserver.config import Config

Base = declarative_base()


class AgentAccountModel(Base):
    __tablename__ = 'accounts'

    identifier = Column(String, primary_key=True, index=True)   # environment/agentname

    environment = Column(String, index=True)
    password = Column(String)
    status = Column(Integer)


engine: Engine = None           # type: ignore
Session: sessionmaker = None    # type: ignore


def setup(config: Config):
    global engine, Session
    engine = create_engine(config.DATABASE_URI)
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine, expire_on_commit=False)
