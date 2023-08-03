from ma import ma
from models.Routine import RoutineModel
from schemas.RoutineChannel import RoutineChannelSchema

class RoutineSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = RoutineModel
        load_instance = True
        #load_only = ("store",)
        include_fk= True

    routine_channels = ma.List(ma.Nested(RoutineChannelSchema))