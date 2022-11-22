from typing import Generic, TypeVar, Optional, Callable, Any

from sqlalchemy import Column, String, create_engine, Integer, Float, Boolean, Text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from werkzeug.exceptions import BadRequest

from aisysprojserver.config import Config

# should be type[DeclarativeMeta], but mypy complains...
Base: Any = declarative_base()  # typing: ignore


class AgentAccountModel(Base):
    __tablename__ = 'accounts'

    identifier = Column(String, primary_key=True, index=True)  # environment/agentname

    environment = Column(String, index=True)
    password = Column(String)
    status = Column(Integer)


class AgentDataModel(Base):
    __tablename__ = 'agents'

    identifier = Column(String, primary_key=True, index=True)  # environment/agentname
    environment = Column(String, index=True)
    fully_evaluated = Column(Boolean, index=True)  # agent has performed enough runs to be properly evaluated

    total_runs = Column(Integer)
    recently_finished_runs = Column(Text)
    recent_results = Column(Text)  # necessary for computing the rating
    best_rating = Column(Float)
    current_rating = Column(Float)


class RunModel(Base):
    __tablename__ = 'runs'

    identifier = Column(Integer, primary_key=True, index=True)
    environment = Column(String, index=True)
    agent = Column(String, index=True)      # environment/agentname
    finished = Column(Boolean, index=True)

    # True if an action request has been sent and not replied to
    # (used to make it harder for agents to delay bad runs to improve their rating)
    outstanding_action = Column(Boolean)

    state = Column(Text)
    history = Column(Text)
    outcome = Column(String)


class ActiveEnvironmentModel(Base):
    __tablename__ = 'active_environments'

    identifier = Column(String, primary_key=True, index=True)

    env_class = Column(String)
    displayname = Column(String)
    displaygroup = Column(String)  # Will be grouped on the front page under this header
    config = Column(String)

    # to avoid changing the database layout later, let's add columns we might need in the future
    signup = Column(
        String)  # for future use (e.g. signup can be open to everyone), currently only "restricted" supported
    status = Column(String)  # for future use, currently only "active" supported


class KeyValModel(Base):
    __tablename__ = 'keyval'

    key = Column(String, index=True, primary_key=True)
    val = Column(Text)


class KeyValAccess:
    def __init__(self, session):
        self.session = session

    def __getitem__(self, item: str):
        kv = self.session.get(KeyValModel, item)
        return kv.val if kv is not None else None

    def __setitem__(self, key, value):
        entry = self.session.get(KeyValModel, key)
        if entry is not None:
            entry.val = value
            self.session.merge(entry)
        else:
            self.session.add(KeyValModel(key=key, val=value))


_M = TypeVar('_M', bound=Base)


class ModelMixin(Generic[_M]):
    """ Mixin for classes that are linked to a model """
    _model: Optional[_M] = None
    identifier: str | int

    def __init__(self, model_class: type[_M]):
        self.__model_class = model_class

    def _try_load_model(self):
        if self._model is None:
            with Session() as session:
                self._model = session.get(self.__model_class, self.identifier)

    def _require_model(self) -> _M:
        self._try_load_model()
        if self._model is None:
            raise Exception(f'{self.__model_class.__name__} {self.identifier!r} does not exist')
        return self._model

    def exists(self) -> bool:
        self._try_load_model()
        return self._model is not None

    def _change_model(self, modify: Callable[[_M], None]):
        with Session() as session:
            ac: Optional[_M] = session.get(self.__model_class, self.identifier)
            if not ac:
                raise BadRequest(f'{self.__model_class.__name__} {self.identifier!r} does not exist')
            modify(ac)
            session.merge(ac)
            session.commit()
        self._model = None


engine: Engine = None  # type: ignore
Session: sessionmaker = None  # type: ignore


def setup(config: Config):
    global engine, Session
    engine = create_engine(config.DATABASE_URI)
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine, expire_on_commit=False)
