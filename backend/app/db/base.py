"""
Single declarative base shared by every ORM model in the project.
Kept in its own module (rather than in session.py) so that Alembic's
env.py can import Base.metadata without also importing the engine.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
