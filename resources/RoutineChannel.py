import imp
from flask import request
from flask_restx import Resource, fields, Namespace

from schemas.RoutineChannel import RoutineChannelSchema
from models.RoutineChannel import RoutineChannelModel

ROUTINE_CHANNEL_NOT_FOUND = "Routine channel not found."

routine_channel_ns = Namespace('routine_channel', description='Routine channel related operations')

routine_channel_schema = RoutineChannelSchema()
routine_channel_list_schema = RoutineChannelSchema(many=True)

routine_channel = routine_channel_ns.model('RoutineChannel', {
    'id': fields.Integer(readonly=True, description='The routine unique identifier'),
    'name': fields.String(required=True, description='Friendly name'),
    #'routine_channels': fields.Nested(RoutineChannelSchema)
})

class RoutineChannel(Resource):
    def get(self, id):
        routine_data = RoutineChannelModel.find_by_id(id)
        if routine_data:
            return routine_channel_schema.dump(routine_data)
        return {'message': ROUTINE_CHANNEL_NOT_FOUND}, 404

    def delete(self,id):
        routine_data = RoutineChannelModel.find_by_id(id)
        if routine_data:
            routine_data.delete_from_db()
            return {'message': "Routine Channel Deleted successfully"}, 200
        return {'message': ROUTINE_CHANNEL_NOT_FOUND}, 404

    @routine_channel_ns.expect(routine_channel)
    def put(self, id):
        item_data = RoutineChannelModel.find_by_id(id)
        item_json = request.get_json();

        if item_data:
            item_data.name = item_json['name']
        else:
            item_data = routine_channel_schema.load(item_json)

        item_data.save_to_db()
        return routine_channel_schema.dump(item_data), 200

class RoutineChannelList(Resource):
    @routine_channel_ns.doc('Get all Routine channels')
    def get(self):
        return routine_channel_list_schema.dump(RoutineChannelModel.find_all()), 200

    @routine_channel_ns.expect(routine_channel)
    @routine_channel_ns.doc('Create a Routine channel')
    def post(self):
        item_json = request.get_json()
        item_data = routine_channel_schema.load(item_json)
        item_data.save_to_db()

        return routine_channel_schema.dump(item_data), 201
            