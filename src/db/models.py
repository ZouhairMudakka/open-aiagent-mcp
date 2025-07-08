from sqlalchemy import Column, Integer, Text

from .session import Base


class Record(Base):
    __tablename__ = "records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    data = Column(Text, nullable=False) 