from db import db
from typing import List

class RoutineChannelTaskModel(db.Model):
    __tablename__ = "routine_channel_task"

    id = db.Column(db.Integer, primary_key=True)
    operation = db.Column(db.String, nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("routine_channel.id"))
    

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'RoutineChannelTaskModel(operation=%s)' % (self.operation)

    def json(self):
        return {'operation': self.operation, 'duration': self.duration}


    @classmethod
    def find_by_id(cls, _id) -> "RoutineChannelTaskModel":
        return cls.query.filter_by(id=_id).first()

    @classmethod
    def find_all(cls) -> List["RoutineChannelTaskModel"]:
        return cls.query.all()

    def save_to_db(self) -> None:
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self) -> None:
        db.session.delete(self)
        db.session.commit()