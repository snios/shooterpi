from flask import request
from flask_restx import Resource, fields, Namespace

from models.Routine import RoutineModel
from schemas.Routine import RoutineSchema
from resources.RoutineChannel import routine_channel

ROUTINE_NOT_FOUND = "Routine not found."

routine_ns = Namespace('routine', description='Routine related operations')
#routines_ns = Namespace('routines', description='Routines related operations')

routine_schema = RoutineSchema()
routine_list_schema = RoutineSchema(many=True)

routine = routine_ns.model('Routine', {
    'id': fields.Integer(readonly=True, description='The routine unique identifier'),
    'name': fields.String(required=True, description='Friendly name'),
    'routine_channels': fields.Nested(routine_channel)
})

class Routine(Resource):
    def get(self, id):
        routine_data = RoutineModel.find_by_id(id)
        if routine_data:
            return routine_schema.dump(routine_data)
        return {'message': ROUTINE_NOT_FOUND}, 404

    def delete(self,id):
        routine_data = RoutineModel.find_by_id(id)
        if routine_data:
            routine_data.delete_from_db()
            return {'message': "Routine Deleted successfully"}, 200
        return {'message': ROUTINE_NOT_FOUND}, 404

    @routine_ns.expect(routine)
    def put(self, id):
        item_data = RoutineModel.find_by_id(id)
        item_json = request.get_json();

        if item_data:
            item_data.name = item_json['name']
        else:
            item_data = routine_schema.load(item_json)

        item_data.save_to_db()
        return routine_schema.dump(item_data), 200

class RoutineList(Resource):
    @routine_ns.doc('Get all Routines')
    def get(self):
        return routine_list_schema.dump(RoutineModel.find_all()), 200

    @routine_ns.expect(routine)
    @routine_ns.doc('Create a Routine')
    def post(self):
        item_json = request.get_json()
        item_data = routine_schema.load(item_json)
        item_data.save_to_db()

        return routine_schema.dump(item_data), 201
            