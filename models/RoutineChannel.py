from db import db
from typing import List
from models.RoutineChannelTask import RoutineChannelTaskModel

class RoutineChannelModel(db.Model):
    __tablename__ = "routine_channel"

    id = db.Column(db.Integer, primary_key=True)
    #channel_id = db.Column(db.Integer, db.ForeignKey("channel.id"))
    parent_id = db.Column(db.Integer, db.ForeignKey("routine.id"))
    tasks = db.relationship(RoutineChannelTaskModel)
    

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'RoutineChannelModel(name=%s)' % (self.name)

    def json(self):
        return {'name': self.name}

    @classmethod
    def find_by_name(cls, name) -> "RoutineChannelModel":
        return cls.query.filter_by(name=name).first()

    @classmethod
    def find_by_id(cls, _id) -> "RoutineChannelModel":
        return cls.query.filter_by(id=_id).first()

    @classmethod
    def find_all(cls) -> List["RoutineChannelModel"]:
        return cls.query.all()

    def save_to_db(self) -> None:
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self) -> None:
        db.session.delete(self)
        db.session.commit()