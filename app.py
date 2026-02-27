# app.py
# app.py
from flask import Flask, render_template, request, session, g
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_session import Session
import os
import pymysql
import pymysql.cursors
from datetime import datetime
from config import Config

# Initialize extensions
socketio = SocketIO(cors_allowed_origins="*", manage_session=False)
session_ext = Session()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # CRITICAL: Ensure secret key is set
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = 'emergency-fallback-key-123!@#$%'
        print("⚠️  WARNING: Using emergency fallback secret key!")
    
    # Print debug info
    print("=" * 50)
    print("APP CONFIGURATION:")
    print(f"SECRET_KEY set: {'YES' if app.config.get('SECRET_KEY') else 'NO'}")
    if app.config.get('SECRET_KEY'):
        print(f"SECRET_KEY (first 10 chars): {app.config['SECRET_KEY'][:10]}...")
    print(f"SESSION_TYPE: {app.config.get('SESSION_TYPE', 'Not set')}")
    print(f"Database: {app.config.get('MYSQL_USER')}@{app.config.get('MYSQL_HOST')}/{app.config.get('MYSQL_DB')}")
    print("=" * 50)
    
    # Initialize extensions with app
    socketio.init_app(app)
    session_ext.init_app(app)
    
    # Create upload folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Database connection function - defined inside create_app to access app.config directly
    def get_db():
        """Get database connection"""
        if 'db' not in g:
            try:
                g.db = pymysql.connect(
                    host=app.config['MYSQL_HOST'],
                    user=app.config['MYSQL_USER'],
                    password=app.config['MYSQL_PASSWORD'],
                    database=app.config['MYSQL_DB'],
                    port=app.config['MYSQL_PORT'],
                    cursorclass=pymysql.cursors.DictCursor,
                    charset='utf8mb4',
                    autocommit=True
                )
                print(f"✅ Database connected successfully to {app.config['MYSQL_DB']}")
            except Exception as e:
                print(f"❌ Database connection error: {e}")
                raise e
        return g.db
    
    # Before request handler - ensures database connection is available
    @app.before_request
    def before_request():
        """Establish database connection before each request"""
        try:
            g.db = get_db()
        except Exception as e:
            print(f"Error establishing database connection: {e}")
            # Return a 500 error or handle gracefully
            return "Database connection error", 500
    
    @app.teardown_appcontext
    def close_db(error):
        """Close database connection after each request"""
        db = g.pop('db', None)
        if db is not None:
            db.close()
            print("Database connection closed")
    
    # Make get_db available to blueprints and socket handlers
    app.get_db = get_db
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.student import student_bp
    from routes.driver import driver_bp
    from routes.admin import admin_bp
    from routes.api import api_bp
    from routes import main_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(driver_bp, url_prefix='/driver')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(main_bp)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register context processors
    register_context_processors(app)
    
    return app

def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500

def register_context_processors(app):
    @app.context_processor
    def utility_processor():
        return {
            'now': datetime.utcnow,
            'app_name': 'Campus Bus'
        }

# ======================================================
# SOCKET.IO EVENT HANDLERS
# ======================================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    emit('connected', {'data': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")

@socketio.on('join_driver')
def handle_driver_join(data):
    """Driver joins their personal room"""
    driver_id = data.get('driver_id')
    if driver_id:
        room = f'driver_{driver_id}'
        join_room(room)
        join_room('drivers')  # Also join general drivers room
        print(f"Driver {driver_id} joined room: {room}")
        emit('joined', {'room': room, 'role': 'driver'})

@socketio.on('join_student')
def handle_student_join(data):
    """Student joins the general broadcast room"""
    user_id = data.get('user_id')
    if user_id:
        join_room('students')
        print(f"Student {user_id} joined students room")
        emit('joined', {'room': 'students', 'role': 'student'})

@socketio.on('join_admin')
def handle_admin_join(data):
    """Admin joins admin room"""
    admin_id = data.get('admin_id')
    if admin_id:
        join_room('admins')
        print(f"Admin {admin_id} joined admins room")
        emit('joined', {'room': 'admins', 'role': 'admin'})

@socketio.on('join_trip_room')
def handle_trip_room_join(data):
    """Join a specific trip room for targeted updates"""
    trip_id = data.get('trip_id')
    user_type = data.get('user_type', 'student')
    
    if trip_id:
        room = f'trip_{trip_id}'
        join_room(room)
        print(f"{user_type} joined trip room: {room}")
        emit('joined', {'room': room, 'trip_id': trip_id})

@socketio.on('leave_trip_room')
def handle_trip_room_leave(data):
    """Leave a specific trip room"""
    trip_id = data.get('trip_id')
    
    if trip_id:
        room = f'trip_{trip_id}'
        leave_room(room)
        print(f"Left trip room: {room}")

@socketio.on('request_live_buses')
def handle_live_buses_request():
    """Student requests list of live buses"""
    # Get the app instance
    from flask import current_app
    with current_app.app_context():
        db = current_app.get_db()
        cursor = db.cursor()
        try:
            cursor.execute("""
                SELECT 
                    t.trip_id,
                    b.bus_number,
                    r.route_name,
                    l.latitude,
                    l.longitude,
                    l.speed,
                    s.stop_name as next_stop,
                    t.passenger_count,
                    b.capacity,
                    t.trip_status
                FROM trips t
                JOIN buses b ON t.bus_id = b.bus_id
                JOIN routes r ON t.route_id = r.route_id
                LEFT JOIN (
                    SELECT trip_id, latitude, longitude, speed
                    FROM live_locations l1
                    WHERE timestamp = (
                        SELECT MAX(timestamp)
                        FROM live_locations l2
                        WHERE l2.trip_id = l1.trip_id
                    )
                ) l ON t.trip_id = l.trip_id
                LEFT JOIN stops s ON t.next_stop_id = s.stop_id
                WHERE t.trip_status = 'in_progress'
                AND t.trip_date = CURDATE()
            """)
            
            buses = cursor.fetchall()
            emit('live_buses_response', {'buses': buses})
            
        except Exception as e:
            print(f"Error fetching live buses: {e}")
            emit('error', {'message': 'Failed to fetch live buses'})
        finally:
            cursor.close()

@socketio.on('get_trip_details')
def handle_trip_details(data):
    """Get details for a specific trip"""
    trip_id = data.get('trip_id')
    
    # Get the app instance
    from flask import current_app
    with current_app.app_context():
        db = current_app.get_db()
        cursor = db.cursor()
        try:
            cursor.execute("""
                SELECT 
                    t.*,
                    b.bus_number,
                    b.capacity,
                    r.route_name,
                    cs.stop_name as current_stop,
                    ns.stop_name as next_stop,
                    (
                        SELECT COUNT(*) 
                        FROM qr_checkins 
                        WHERE trip_id = t.trip_id 
                        AND DATE(checkin_time) = CURDATE()
                    ) as checkins_today
                FROM trips t
                JOIN buses b ON t.bus_id = b.bus_id
                JOIN routes r ON t.route_id = r.route_id
                LEFT JOIN stops cs ON t.current_stop_id = cs.stop_id
                LEFT JOIN stops ns ON t.next_stop_id = ns.stop_id
                WHERE t.trip_id = %s
            """, (trip_id,))
            
            trip = cursor.fetchone()
            emit('trip_details_response', {'trip': trip})
            
        except Exception as e:
            print(f"Error fetching trip details: {e}")
            emit('error', {'message': 'Failed to fetch trip details'})
        finally:
            cursor.close()

# ======================================================
# BROADCAST FUNCTIONS (can be called from routes)
# ======================================================

def broadcast_bus_location(trip_id, bus_number, route_name, latitude, longitude, speed, heading, occupancy, capacity):
    """Broadcast bus location to all students"""
    socketio.emit('bus_location_updated', {
        'trip_id': trip_id,
        'bus_number': bus_number,
        'route_name': route_name,
        'latitude': latitude,
        'longitude': longitude,
        'speed': speed,
        'heading': heading,
        'occupancy': occupancy,
        'capacity': capacity,
        'timestamp': datetime.utcnow().isoformat()
    }, room='students')

def broadcast_bus_arrival(trip_id, stop_name, next_stop, departure_in):
    """Broadcast bus arrival to students following this trip"""
    socketio.emit('bus_arrived', {
        'trip_id': trip_id,
        'stop_name': stop_name,
        'next_stop': next_stop,
        'departure_in': departure_in,
        'timestamp': datetime.utcnow().isoformat()
    }, room=f'trip_{trip_id}')

def broadcast_emergency(trip_id, bus_number, driver_name, route):
    """Broadcast emergency alert"""
    socketio.emit('emergency_alert', {
        'trip_id': trip_id,
        'bus_number': bus_number,
        'driver_name': driver_name,
        'route': route,
        'message': '🚨 EMERGENCY ALERT: Please clear the area!',
        'timestamp': datetime.utcnow().isoformat()
    }, room='students')
    
    # Also send to admins
    socketio.emit('admin_emergency', {
        'trip_id': trip_id,
        'bus_number': bus_number,
        'driver_name': driver_name,
        'route': route,
        'message': '🚨 Driver has triggered an emergency alert!'
    }, room='admins')

def broadcast_delay(trip_id, bus_number, route_name, delay_minutes):
    """Broadcast delay information"""
    socketio.emit('bus_delayed', {
        'trip_id': trip_id,
        'bus_number': bus_number,
        'route_name': route_name,
        'delay': delay_minutes,
        'message': f'Bus delayed by {delay_minutes} minutes',
        'timestamp': datetime.utcnow().isoformat()
    }, room='students')

def broadcast_occupancy_update(trip_id, count, capacity, percentage):
    """Broadcast occupancy updates"""
    socketio.emit('occupancy_updated', {
        'trip_id': trip_id,
        'count': count,
        'capacity': capacity,
        'percentage': percentage,
        'timestamp': datetime.utcnow().isoformat()
    }, room='students')

# For running directly
if __name__ == '__main__':
    app = create_app()
    if app:
        print("✅ App created successfully!")
        print("🚀 Starting server with Socket.IO support...")
        socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
    else:
        print("❌ Failed to create app!")