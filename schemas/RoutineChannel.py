from ma import ma
from models.RoutineChannel import RoutineChannelModel

class RoutineChannelSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = RoutineChannelModel
        load_instance = True
        #load_only = ("store",)
        include_fk= True