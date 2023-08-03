from ma import ma
from models.Channel import ChannelModel

class ChannelSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ChannelModel
        load_instance = True
        #load_only = ("store",)
        include_fk= True