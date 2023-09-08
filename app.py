from flask import Flask
from flask_restx import Api, Resource, fields
from time import sleep, perf_counter
import RPi.GPIO as GPIO
import multiprocessing
import sqlite3


app = Flask(__name__)
api = Api(app,
          version='1.0',
          title='Shooter Pi',
          description='A RESTful API to control the GPIO pins of a Raspbery Pi',
          doc='/docs')

# DB
conn = sqlite3.connect('app.db')
# Initialize DB tables

conn.execute('''
CREATE TABLE IF NOT EXISTS routines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT
)''')
conn.execute('''
    CREATE TABLE IF NOT EXISTS pins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pin_num INTEGER,
        friendly_name TEXT,
        state TEXT,
        inverted INTEGER
    )
''')
conn.execute('''
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    routine_id INTEGER,
    pin_id INTEGER,
    FOREIGN KEY(routine_id) REFERENCES routines(id),
    FOREIGN KEY(pin_id) REFERENCES pins(id)
)''')
conn.execute('''
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER,
    operation TEXT,
    duration INTEGER,
    FOREIGN KEY(channel_id) REFERENCES channels(id)
)''')

conn.commit()

conn.close()


# Models
pin_model = api.model('pins', {
    'id': fields.Integer(readonly=True, description='The pin unique identifier'),
    'pin_num': fields.Integer(required=True, description='GPIO pin associated with this endpoint'),
    'friendly_name': fields.String(required=True, description='Friendly name'),
    'state': fields.String(required=True, description='Initial state on or off'),
    'inverted': fields.Integer(required=True, description= '0 = false 1 = true. To invert the pins operation')
})

task_model = api.model('task', {
    'id': fields.Integer(readonly=True, description='The task unique identifier'),
    'operation': fields.String(required=True, description='on, off or sleep'),
    'duration': fields.Integer(),
    'channel_id': fields.Integer(required=True, description='what channel it belongs to..'),
})

channel_model = api.model('channel', {
    'id': fields.Integer(readonly=True, description='The channel unique identifier'),
    'pin_id': fields.Integer(required=True, description='The pin that this channel will modify'),
    'tasks': fields.List(fields.Nested(task_model))
})
routine_model = api.model('routine', {
    'id': fields.Integer(readonly=True, description='The routine unique identifier'),
    'name': fields.String(required=True, description='Friendly name'),
    'channels': fields.List(fields.Nested(channel_model))
})

# Namespace
ns = api.namespace('pins', description='Pin related operations')
routine_ns = api.namespace('routine', description='Routines that can be executed')

# GPIO Setup
GPIO.setmode(GPIO.BCM)

class PinUtil(object):
    def __init__(self):
        self.counter = 0
        self.pins = []

    def get(self, id):
        for pin in self.pins:
            if pin['id'] == id:
                return pin
        api.abort(404, f"pin {id} doesn't exist.")

    def get2(self, id):
        conn = sqlite3.connect('app.db')
        conn.row_factory = sqlite3.Row   #  this makes the data a dict instead of a tuple
        cursor = conn.execute('SELECT * FROM pins WHERE id = ?', (id,))
        result = cursor.fetchone()

        # pin = {
        #         'id': result['id'],
        #         'pin_num': result['pin_num'],
        #         'friendly_name': result['friendly_name'],                       
        #         'state': result['state'],
        #         'inverted': result['inverted'],
        #         # Add more attributes as needed
        #     }
        conn.close()
        return result

    def get_all(self):
        conn = sqlite3.connect('app.db')
        conn.row_factory = sqlite3.Row   #  this makes the data a dict instead of a tuple
        query = "SELECT * FROM pins"
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        # pins = []
        # for row in rows:
        #     print(f'row {row}')
        #     pin = {}
        #     pin['id'] = row['id']
        #     pin['pin_num'] = row['pin_num']
        #     pin['friendly_name'] = row['friendly_name']
        #     pin['state'] = row['state']
        #     pin['inverted'] = row['inverted']
        #     # Add more attributes as needed
        #     pins.append(pin)

        return rows

    def create(self, data):
        pin = data
        pin['id'] = self.counter = self.counter + 1
        self.pins.append(pin)
        GPIO.setup(pin['pin_num'], GPIO.OUT)
        # Perhaps move initilatation of pins to when something is actuallty run for the first time?
        if(pin['inverted'] == 1):
            if pin['state'] == 'off':
                GPIO.output(pin['pin_num'], GPIO.HIGH)
            elif pin['state'] == 'on':
                GPIO.output(pin['pin_num'], GPIO.LOW)
        elif(pin['inverted'] == 0):
            if pin['state'] == 'off':
                GPIO.output(pin['pin_num'], GPIO.LOW)
            elif pin['state'] == 'on':
                GPIO.output(pin['pin_num'], GPIO.HIGH)

        return pin
    
    def create2 (self, data):
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO pins (pin_num, friendly_name, state, inverted) VALUES (?, ?, ?, ?)',
                       (data['pin_num'], data['friendly_name'], data['state'], data['inverted']))
        conn.commit()
        conn.close()
        return {
            'id': cursor.lastrowid,
            'pin_num': data['pin_num'],
            'friendly_name': data['friendly_name'],
            'state': data['state'],
            'inverted': data['inverted']
        }

    def update(self, id, data):
        pin = self.get(id)
        pin.update(data)  # this is the dict_object update method
        GPIO.setup(pin['pin_num'], GPIO.OUT)

        if pin['state'] == 'off':
            GPIO.output(pin['pin_num'], GPIO.LOW)
        elif pin['state'] == 'on':
            GPIO.output(pin['pin_num'], GPIO.HIGH)

        return pin

    def delete(self, id):
        pin = self.get(id)
        GPIO.output(pin['pin_num'], GPIO.LOW)
        self.pins.remove(pin)

class RoutineUtil(object):
    def __init__(self):
        self.counter = 0
        self.routines = []
        self.processes = []

    # def get(self, id):
    #     for routine in self.routines:
    #         if routine['id'] == id:
    #             return routine
    #     api.abort(404, f"routine {id} doesn't exist.")
    def get(self, id):
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        routine = c.execute('SELECT * FROM routines WHERE id=?', (id,)).fetchone()
        if not routine:
            api.abort(404, f"Routine {id} doesn't exist.")

        # Construct the returned routine object
        routine_dict = {
            'id': routine[0],
            'name': routine[1],
            'channels': []
        }

        # Fetch and append channels for the given routine
        channels = c.execute('SELECT * FROM channels WHERE routine_id=?', (id,)).fetchall()
        for channel in channels:
            channel_dict = {
                'id': channel[0],
                'routine_id': channel[1],
                'pin_id': channel[2],
                'tasks': []
            }

            # Fetch and append tasks for the given channel
            tasks = c.execute('SELECT * FROM tasks WHERE channel_id=?', (channel[0],)).fetchall()
            for task in tasks:
                task_dict = {
                    'id': task[0],
                    'channel_id': task[1],
                    'operation': task[2],
                    'duration': task[3]
                }
                channel_dict['tasks'].append(task_dict)

            # Fetch and append pin information for the given channel
            pin = c.execute('SELECT * FROM pins WHERE id=?', (channel[2],)).fetchone()
            if pin:
                pin_dict = {
                    'id': pin[0],
                    'pin_num': pin[1],
                    'friendly_name': pin[2],
                    'state': pin[3],
                    'inverted': pin[4]
                }
                channel_dict['pin'] = pin_dict

            routine_dict['channels'].append(channel_dict)

        return routine_dict
    def get_all(self):
        conn = sqlite3.connect('app.db')  # Assuming you open a new connection
        c = conn.cursor()
        all_routines = []        
        # Fetch all routines' id and name
        routines = c.execute('SELECT id, name FROM routines').fetchall()
        for routine in routines:
            routine_dict = {
                'id': routine[0],
                'name': routine[1]
            }
            all_routines.append(routine_dict)

        conn.close()  # Close the connection
        return all_routines

    # def create(self, data):
    #     routine = data
    #     routine['id'] = self.counter = self.counter + 1
    #     self.routines.append(routine)

    #     return routine
    def create(self, data):
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute('INSERT INTO routines (name) VALUES (?)', (data['name'],))
        routine_id = c.lastrowid

        for channel in data['channels']:
            c.execute('INSERT INTO channels (routine_id, pin_id) VALUES (?, ?)', (routine_id, channel['pin_id']))
            channel_id = c.lastrowid
            for task in channel['tasks']:
                c.execute('INSERT INTO tasks (channel_id, operation, duration) VALUES (?, ?, ?)', (channel_id, task['operation'], task['duration']))

        conn.commit()

        return self.get(routine_id)
    
    def update(self, id, data):
            conn = sqlite3.connect('app.db')
            c = conn.cursor()

            try:
                # Update the basic fields of the routine like 'name'
                c.execute("""
                    UPDATE routines 
                    SET name = ? 
                    WHERE id = ?;
                """, (data['name'], id))

                # Delete existing channels and tasks for the routine
                c.execute("DELETE FROM channels WHERE routine_id = ?", (id,))
                c.execute("DELETE FROM tasks WHERE channel_id IN (SELECT id FROM channels WHERE routine_id = ?);", (id,))

                # Add new channels and tasks from the updated data
                for channel in data['channels']:
                    c.execute("""
                        INSERT INTO channels (pin_id, routine_id)
                        VALUES (?, ?);
                    """, (channel['pin_id'], id))

                    channel_id = c.lastrowid
                    
                    for task in channel['tasks']:
                        c.execute("""
                            INSERT INTO tasks (operation, duration, channel_id)
                            VALUES (?, ?, ?);
                        """, (task['operation'], task['duration'], channel_id))

                # Commit the transaction
                conn.commit()
                return self.get(id)

            except sqlite3.Error as e:
                print("Database error: ", e)
                # If any error occurs, rollback the transaction
                c.execute("ROLLBACK;")

    # def run(self, id):
    #     start = perf_counter()

    #     total_processes = 0  # Variable to count the total number of processes
    #     for routine in self.routines:
    #         if routine['id'] == id:
    #             for channel in routine['channels']:
    #                 total_processes += 1  # Increment the count for each channel
    #     barrier = multiprocessing.Barrier(total_processes) # to be used later as a barrier to start all processes almost simeltaneiosly

    #     for routine in self.routines:
    #         if routine['id'] == id:
    #             for channel in routine['channels']:
    #                 p = multiprocessing.Process(target=run_channel, args=(channel,barrier))
    #                 self.processes.append(p)
    #                 p.start()                
    #             for process in self.processes:
    #                 process.join()
    #     finish = perf_counter()
    #     print(f'Finished program in {round(finish-start, 2)}')

    #     print(f'Resetting pins in 5 seconds')
    #     sleep(5)
    #     reset_pins()
    def run(self, id):
        # Fetch the routine by its ID using the get method
        routine = self.get(id)

        # Check if routine exists
        if routine is None:
            print(f"Routine with ID {id} not found.")
            return

        # Your existing logic for running the routine
        start = perf_counter()

        total_processes = 0  # Variable to count the total number of processes
        for channel in routine['channels']:
            total_processes += 1  # Increment the count for each channel

        barrier = multiprocessing.Barrier(total_processes)

        for channel in routine['channels']:
            p = multiprocessing.Process(target=run_channel, args=(channel, barrier))
            self.processes.append(p)
            p.start()

        for process in self.processes:
            process.join()

        finish = perf_counter()
        print(f'Finished program in {round(finish - start, 2)}')

        # print(f'Resetting pins in 5 seconds')
        reset_pins()
    
    def kill_all(self):
        for process in self.processes:
            process.terminate()

def run_channel(channel, barrier):
    print(f"Worker {channel['pin_id']} waiting...")
    barrier.wait()  # Wait for all processes to reach the barrier
    print(f"Worker {channel['pin_id']} started.")
    for task in channel['tasks']:
        run_task(task, channel['pin_id'])

def run_task(task, pin_id):
    print(f'run task on pin {pin_id}')
    if task['operation'] == 'on':
        pin = pin_util.get(pin_id)
        if(pin['inverted'] == 1):
            GPIO.output(pin['pin_num'], GPIO.LOW)
        elif(pin['inverted'] == 0):
            GPIO.output(pin['pin_num'], GPIO.HIGH)
        sleep(task['duration'])
    elif task['operation'] == 'off':
        pin = pin_util.get(pin_id)
        if(pin['inverted'] == 1):
            GPIO.output(pin['pin_num'], GPIO.HIGH)
        elif(pin['inverted'] == 0):
            GPIO.output(pin['pin_num'], GPIO.LOW)
        sleep(task['duration'])
    elif task['operation'] == 'sleep':
        sleep(task['duration'])

def reset_pins():
    for pin in pin_util.pins:
        print(f'resetting pin {pin["id"]}')
        if(pin['inverted'] == 1):
            GPIO.output(pin['pin_num'], GPIO.HIGH)
        elif(pin['inverted'] == 0):
            GPIO.output(pin['pin_num'], GPIO.LOW)


@routine_ns.route('/')
class RoutineList(Resource):
    @routine_ns.marshal_list_with(routine_model)
    def get(self):
        """List all routines"""
        return routine_util.get_all()

    @routine_ns.expect(routine_model)
    @routine_ns.marshal_with(routine_model, code=201)
    def post(self):
        """Create a new routine"""
        return routine_util.create(api.payload)
    
@routine_ns.route('/<int:id>')
@routine_ns.response(404, 'Routine not found')
@routine_ns.param('id', 'The routine identifier')
class RoutineResource(Resource):
    @routine_ns.marshal_with(routine_model)
    def get(self, id):
        """Fetch a routine given its resource identifier"""
        return routine_util.get(id)

    @routine_ns.expect(routine_model)
    @routine_ns.marshal_with(routine_model, code=200)
    def put(self, id):
        """Update a routine given its resource identifier"""
        return routine_util.update(id, api.payload) 
    
@routine_ns.route('/<int:id>/run')
@routine_ns.response(404, 'routine not found')
@routine_ns.param('id', 'The routine identifier')
class RoutineRun(Resource):
    def get(self, id):
        """Fetch a pin given its resource identifier"""
        return routine_util.run(id)




@ns.route('/')  # keep in mind this our ns-namespace (pins/)
class PinList(Resource):
    """Shows a list of all pins, and lets you POST to add new pins"""

    @ns.marshal_list_with(pin_model)
    def get(self):
        """List all pins"""
        res = pin_util.get_all()
        resOld = pin_util.pins
        print(f'return pins {res}')
        return resOld

    @ns.expect(pin_model)
    @ns.marshal_with(pin_model, code=201)
    def post(self):
        """Create a new pin"""
        return pin_util.create2(api.payload)


@ns.route('/<int:id>')
@ns.response(404, 'pin not found')
@ns.param('id', 'The pin identifier')
class Pin(Resource):
    """Show a single pin item and lets you update/delete them"""

    @ns.marshal_with(pin_model)
    def get(self, id):
        """Fetch a pin given its resource identifier"""
        return pin_util.get2(id)

    @ns.response(204, 'pin deleted')
    def delete(self, id):
        """Delete a pin given its identifier"""
        pin_util.delete(id)
        return '', 204

    @ns.expect(pin_model, validate=True)
    @ns.marshal_with(pin_model)
    def put(self, id):
        """Update a pin given its identifier"""
        return pin_util.update(id, api.payload)
    
    @ns.expect(pin_model)
    @ns.marshal_with(pin_model)
    def patch(self, id):
        """Partially update a pin given its identifier"""
        return pin_util.update(id, api.payload)

pin_util = PinUtil()
pin_util.create({'pin_num': 9, 'friendly_name': 'output 1', 'state': 'off', 'inverted': 1})
pin_util.create({'pin_num': 4, 'friendly_name': 'output 2', 'state': 'off', 'inverted': 1})
pin_util.create({'pin_num': 3, 'friendly_name': 'output 3', 'state': 'off', 'inverted': 1})
pin_util.create({'pin_num': 11, 'friendly_name': 'lamp', 'state': 'off', 'inverted': 0})
routine_util = RoutineUtil()

def insert_default_routines_if_empty():
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    # Check if the routines table is empty
    routine_count = c.execute('SELECT COUNT(*) FROM routines').fetchone()[0]

    if routine_count == 0:
        routine_util.create({'name': 'Testrutin', 'channels': [
            {'pin_id': 1, 'tasks': [
                {'operation': 'off', 'duration': 5}, 
                {'operation': 'on', 'duration': 3}, 
                {'operation': 'off', 'duration': 5}, 
                {'operation': 'on', 'duration': 3}, 
            ]},
            {'pin_id': 2, 'tasks': [
                {'operation': 'off', 'duration': 5}, 
                {'operation': 'on', 'duration': 3}, 
                {'operation': 'off', 'duration': 5}, 
                {'operation': 'on', 'duration': 3}, 
            ]},
            {'pin_id': 3, 'tasks': [
                {'operation': 'off', 'duration': 5}, 
                {'operation': 'on', 'duration': 3}, 
                {'operation': 'off', 'duration': 5}, 
                {'operation': 'on', 'duration': 3}, 
            ]},
            ]})
        routine_util.create({'name': 'Milsnabb 10sek', 'channels': [
            {'pin_id': 1, 'tasks': [
                {'operation': 'on', 'duration': 10},
                {'operation': 'off', 'duration': 10}, 
                {'operation': 'on', 'duration': 5},
                {'operation': 'off', 'duration': 0},
                ]},
            {'pin_id': 2, 'tasks': [
                {'operation': 'off', 'duration': 10},
                {'operation': 'on', 'duration': 10}, 
                {'operation': 'off', 'duration': 5},
                {'operation': 'on', 'duration': 0},
                ]}     
            ]})
        routine_util.create({'name': 'Milsnabb 8sek', 'channels': [
            {'pin_id': 1, 'tasks': [
                {'operation': 'off', 'duration': 10},
                {'operation': 'on', 'duration': 8}, 
                {'operation': 'off', 'duration': 5},
                {'operation': 'on', 'duration': 0},
                ]},
            {'pin_id': 2, 'tasks': [
                {'operation': 'off', 'duration': 10},
                {'operation': 'on', 'duration': 8}, 
                {'operation': 'off', 'duration': 5},
                {'operation': 'on', 'duration': 0},
                ]}     
            ]})
        routine_util.create({'name': 'Milsnabb 6sek', 'channels': [
            {'pin_id': 1, 'tasks': [
                {'operation': 'off', 'duration': 10},
                {'operation': 'on', 'duration': 6}, 
                {'operation': 'off', 'duration': 5},
                {'operation': 'on', 'duration': 0},
                ]},
            {'pin_id': 2, 'tasks': [
                {'operation': 'off', 'duration': 10},
                {'operation': 'on', 'duration': 6}, 
                {'operation': 'off', 'duration': 5},
                {'operation': 'on', 'duration': 0},
                ]}     
            ]})
        routine_util.create({'name': '25M 5x3', 'channels': [
            {'pin_id': 1, 'tasks': [
                {'operation': 'on', 'duration': 2}, 
                {'operation': 'off', 'duration': 2}, 
                {'operation': 'on', 'duration': 2}, 
                {'operation': 'off', 'duration': 2}, 
                ]},
                {'pin_id': 2, 'tasks': [
                {'operation': 'on', 'duration': 2}, 
                {'operation': 'off', 'duration': 2}, 
                {'operation': 'on', 'duration': 2}, 
                {'operation': 'off', 'duration': 2}, 
                ]},
            ]})

insert_default_routines_if_empty()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port='5000', debug=True)
    GPIO.cleanup()
