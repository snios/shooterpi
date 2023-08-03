from db import db

class ChannelModel(db.Model):
    __tablename__ = "channel"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    pin_id = db.Column(db.Integer, nullbale=False)