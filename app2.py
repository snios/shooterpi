from flask import Flask, Blueprint, jsonify
from flask_restx import Api
from ma import ma
from db import db

from resources.Routine import Routine, RoutineList, routine_ns
from resources.RoutineChannel import RoutineChannel, RoutineChannelList, routine_channel_ns
from marshmallow import ValidationError

#import button_reader

app = Flask(__name__)
bluePrint = Blueprint('api', __name__, url_prefix='/api')
api = Api(bluePrint, doc='/doc', title='Shooter RESTful api')
app.register_blueprint(bluePrint)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PROPAGATE_EXCEPTIONS'] = True

api.add_namespace(routine_ns)
api.add_namespace(routine_channel_ns)

@app.before_first_request
def create_tables():
    db.create_all()

@api.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify(error.messages), 400

routine_ns.add_resource(Routine, '/<int:id>')
routine_ns.add_resource(RoutineList, "")

routine_channel_ns.add_resource(RoutineChannel,'/<int:id>')
routine_channel_ns.add_resource(RoutineChannelList,"")

db.init_app(app)
ma.init_app(app)
if __name__ == '__main__':    
    app.run(port=5001, debug=True)