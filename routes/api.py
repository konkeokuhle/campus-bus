# routes/api.py
from flask import Blueprint, jsonify, request
from models.trip import Trip, LiveLocation
from models.bus import Bus
from models.route import Route
from app import mysql
import MySQLdb.cursors

api_bp = Blueprint('api', __name__)

@api_bp.route('/live-buses')
def get_live_buses():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get all active trips with their latest locations
    cursor.execute("""
        SELECT 
            t.trip_id,
            b.bus_id,
            b.bus_number,
            r.route_name,
            r.route_id,
            l.latitude,
            l.longitude,
            l.speed,
            l.heading,
            l.timestamp,
            s.stop_name as next_stop,
            t.trip_status
        FROM trips t
        JOIN buses b ON t.bus_id = b.bus_id
        JOIN routes r ON t.route_id = r.route_id
        LEFT JOIN (
            SELECT trip_id, latitude, longitude, speed, heading, timestamp
            FROM live_locations l1
            WHERE timestamp = (
                SELECT MAX(timestamp)
                FROM live_locations l2
                WHERE l2.trip_id = l1.trip_id
            )
        ) l ON t.trip_id = l.trip_id
        LEFT JOIN stops s ON t.next_stop_id = s.stop_id
        WHERE t.trip_status IN ('in_progress', 'scheduled')
        AND t.trip_date = CURDATE()
        ORDER BY t.scheduled_start_time
    """)
    
    buses = cursor.fetchall()
    cursor.close()
    
    return jsonify(buses)

@api_bp.route('/routes')
def get_routes():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM routes WHERE is_active = TRUE")
    routes = cursor.fetchall()
    cursor.close()
    return jsonify(routes)

@api_bp.route('/stops')
def get_stops():
    route_id = request.args.get('route_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if route_id:
        cursor.execute("""
            SELECT s.*, rs.stop_order 
            FROM stops s
            JOIN route_stops rs ON s.stop_id = rs.stop_id
            WHERE rs.route_id = %s
            ORDER BY rs.stop_order
        """, (route_id,))
    else:
        cursor.execute("SELECT * FROM stops WHERE is_active = TRUE")
    
    stops = cursor.fetchall()
    cursor.close()
    return jsonify(stops)

@api_bp.route('/eta/<int:trip_id>/<int:stop_id>')
def get_eta(trip_id, stop_id):
    # Calculate ETA based on current location and speed
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get latest location
    cursor.execute("""
        SELECT latitude, longitude, speed 
        FROM live_locations 
        WHERE trip_id = %s 
        ORDER BY timestamp DESC 
        LIMIT 1
    """, (trip_id,))
    
    location = cursor.fetchone()
    
    # Get stop location
    cursor.execute("SELECT latitude, longitude FROM stops WHERE stop_id = %s", (stop_id,))
    stop = cursor.fetchone()
    
    cursor.close()
    
    if not location or not stop:
        return jsonify({'eta': None})
    
    # Calculate distance (simplified - you'd use proper distance calculation)
    import math
    lat1, lon1 = location['latitude'], location['longitude']
    lat2, lon2 = stop['latitude'], stop['longitude']
    
    # Simple distance calculation (in km)
    distance = math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2) * 111  # rough conversion
    
    if location['speed'] > 0:
        eta_minutes = (distance / location['speed']) * 60
    else:
        eta_minutes = None
    
    return jsonify({
        'eta': round(eta_minutes) if eta_minutes else None,
        'distance': round(distance, 2),
        'speed': location['speed']
    })