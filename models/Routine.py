from db import db
from typing import List
from models.RoutineChannel import RoutineChannelModel

class RoutineModel(db.Model):
    __tablename__ = "routine"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    routine_channels: db.relationship(RoutineChannelModel)

    def __init__(self, name, routine_channels):
        self.name = name
        self.routine_channels = routine_channels

    def __repr__(self):
        return 'RoutineModel(name=%s)' % (self.name)

    def json(self):
        return {'name': self.name}

    @classmethod
    def find_by_name(cls, name) -> "RoutineModel":
        return cls.query.filter_by(name=name).first()

    @classmethod
    def find_by_id(cls, _id) -> "RoutineModel":
        return cls.query.filter_by(id=_id).first()

    @classmethod
    def find_all(cls) -> List["RoutineModel"]:
        return cls.query.all()

    def save_to_db(self) -> None:
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self) -> None:
        db.session.delete(self)
        db.session.commit()