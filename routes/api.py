# routes/api.py
from flask import Blueprint, jsonify, request, session, g
from datetime import datetime
import math

api_bp = Blueprint('api', __name__)

@api_bp.route('/live-buses')
def get_live_buses():
    """Get all active buses with their latest locations"""
    residence_id = request.args.get('residence_id')
    route_id = request.args.get('route_id')
    
    cursor = g.db.cursor()
    
    query = """
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
            t.trip_status,
            t.passenger_count,
            b.capacity,
            res.residence_id,
            res.residence_name,
            u.full_name as driver_name,
            t.delay_minutes,
            t.actual_start_time,
            t.scheduled_start_time
        FROM trips t
        JOIN buses b ON t.bus_id = b.bus_id
        JOIN routes r ON t.route_id = r.route_id
        JOIN residences res ON b.residence_id = res.residence_id
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
        LEFT JOIN users u ON t.driver_id = u.user_id
        WHERE t.trip_status IN ('in_progress', 'scheduled')
        AND t.trip_date = CURDATE()
    """
    
    params = []
    if residence_id:
        query += " AND b.residence_id = %s"
        params.append(residence_id)
    
    if route_id:
        query += " AND t.route_id = %s"
        params.append(route_id)
    
    query += " ORDER BY t.scheduled_start_time"
    
    cursor.execute(query, params)
    buses = cursor.fetchall()
    
    # Get total counts by residence
    cursor.execute("""
        SELECT residence_id, residence_name, 
               (SELECT COUNT(*) FROM buses WHERE residence_id = r.residence_id) as total_buses,
               (SELECT COUNT(*) FROM trips t 
                JOIN buses b ON t.bus_id = b.bus_id 
                WHERE b.residence_id = r.residence_id 
                AND t.trip_status = 'in_progress') as active_buses
        FROM residences r
        WHERE is_active = TRUE
    """)
    
    residence_stats = cursor.fetchall()
    cursor.close()
    
    return jsonify({
        'buses': buses,
        'residence_stats': residence_stats
    })

@api_bp.route('/residences')
def get_residences():
    """Get all active residences"""
    cursor = g.db.cursor()
    cursor.execute("""
        SELECT r.*, 
               (SELECT COUNT(*) FROM buses WHERE residence_id = r.residence_id) as total_buses,
               (SELECT COUNT(*) FROM buses WHERE residence_id = r.residence_id AND bus_status = 'active') as active_buses
        FROM residences r
        WHERE r.is_active = TRUE
        ORDER BY r.residence_name
    """)
    residences = cursor.fetchall()
    cursor.close()
    return jsonify(residences)

@api_bp.route('/residence-buses/<int:residence_id>')
def get_residence_buses(residence_id):
    """Get all buses for a specific residence"""
    cursor = g.db.cursor()
    cursor.execute("""
        SELECT b.*, u.full_name as driver_name,
               (SELECT COUNT(*) FROM trips t 
                WHERE t.bus_id = b.bus_id 
                AND t.trip_status = 'in_progress') as has_active_trip
        FROM buses b
        LEFT JOIN users u ON b.current_driver_id = u.user_id
        WHERE b.residence_id = %s
        ORDER BY b.bus_number
    """, (residence_id,))
    buses = cursor.fetchall()
    cursor.close()
    return jsonify(buses)

@api_bp.route('/routes-list')
def get_routes_list():
    """Get all active routes"""
    cursor = g.db.cursor()
    cursor.execute("SELECT * FROM routes WHERE is_active = TRUE")
    routes = cursor.fetchall()
    cursor.close()
    return jsonify(routes)

@api_bp.route('/stops-list')
def get_stops_list():
    """Get all stops or stops for a specific route"""
    route_id = request.args.get('route_id')
    cursor = g.db.cursor()
    
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

@api_bp.route('/trip-details/<int:trip_id>')
def get_trip_details(trip_id):
    """Get details for a specific trip"""
    cursor = g.db.cursor()
    
    cursor.execute("""
        SELECT 
            t.*,
            b.bus_number,
            b.capacity,
            r.route_name,
            cs.stop_name as current_stop_name,
            ns.stop_name as next_stop_name,
            u.full_name as driver_name,
            res.residence_name,
            res.residence_id
        FROM trips t
        JOIN buses b ON t.bus_id = b.bus_id
        JOIN routes r ON t.route_id = r.route_id
        JOIN residences res ON b.residence_id = res.residence_id
        LEFT JOIN stops cs ON t.current_stop_id = cs.stop_id
        LEFT JOIN stops ns ON t.next_stop_id = ns.stop_id
        LEFT JOIN users u ON t.driver_id = u.user_id
        WHERE t.trip_id = %s
    """, (trip_id,))
    
    trip = cursor.fetchone()
    
    # Get upcoming stops
    if trip:
        cursor.execute("""
            SELECT s.*, rs.stop_order, rs.estimated_time_from_prev
            FROM stops s
            JOIN route_stops rs ON s.stop_id = rs.stop_id
            WHERE rs.route_id = %s
            AND rs.stop_order > COALESCE(
                (SELECT stop_order FROM route_stops WHERE route_id = %s AND stop_id = %s),
                0
            )
            ORDER BY rs.stop_order
            LIMIT 5
        """, (trip['route_id'], trip['route_id'], trip.get('current_stop_id', 0)))
        
        upcoming_stops = cursor.fetchall()
        trip['upcoming_stops'] = upcoming_stops
    
    cursor.close()
    
    return jsonify(trip)

@api_bp.route('/eta/<int:trip_id>/<int:stop_id>')
def get_eta(trip_id, stop_id):
    """Calculate ETA for a specific trip to a stop"""
    cursor = g.db.cursor()
    
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
    
    # Get trip delay
    cursor.execute("SELECT delay_minutes FROM trips WHERE trip_id = %s", (trip_id,))
    trip = cursor.fetchone()
    
    cursor.close()
    
    if not location or not stop:
        return jsonify({'eta': None, 'error': 'Location or stop not found'})
    
    # Calculate distance using Haversine formula
    lat1, lon1 = float(location['latitude']), float(location['longitude'])
    lat2, lon2 = float(stop['latitude']), float(stop['longitude'])
    
    # Haversine formula for more accurate distance
    R = 6371  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    # Calculate ETA
    delay_minutes = trip['delay_minutes'] if trip else 0
    
    if location['speed'] and location['speed'] > 0:
        eta_minutes = (distance / float(location['speed'])) * 60
        eta_minutes += delay_minutes
    else:
        # Use average speed from route if bus is stationary
        cursor = g.db.cursor()
        cursor.execute("""
            SELECT AVG(speed) as avg_speed 
            FROM live_locations 
            WHERE trip_id = %s AND speed > 0
        """, (trip_id,))
        avg_speed_data = cursor.fetchone()
        cursor.close()
        
        avg_speed = avg_speed_data['avg_speed'] if avg_speed_data and avg_speed_data['avg_speed'] else 20
        eta_minutes = (distance / avg_speed) * 60
        eta_minutes += delay_minutes
    
    return jsonify({
        'trip_id': trip_id,
        'stop_id': stop_id,
        'eta': round(eta_minutes) if eta_minutes else None,
        'distance': round(distance, 2),
        'speed': location['speed'],
        'delay': delay_minutes
    })

@api_bp.route('/test-db')
def test_database():
    """Test database connection"""
    try:
        cursor = g.db.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        return jsonify({
            'status': 'success',
            'message': 'Database connected successfully!',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Database connection failed: {str(e)}'
        }), 500

@api_bp.route('/driver-trips/<int:driver_id>')
def get_driver_trips(driver_id):
    """Get trips for a specific driver"""
    cursor = g.db.cursor()
    
    cursor.execute("""
        SELECT t.*, b.bus_number, r.route_name, res.residence_name
        FROM trips t
        JOIN buses b ON t.bus_id = b.bus_id
        JOIN routes r ON t.route_id = r.route_id
        JOIN residences res ON b.residence_id = res.residence_id
        WHERE t.driver_id = %s
        AND t.trip_date = CURDATE()
        ORDER BY t.scheduled_start_time
    """, (driver_id,))
    
    trips = cursor.fetchall()
    cursor.close()
    
    return jsonify(trips)

@api_bp.route('/route-stops/<int:route_id>')
def get_route_stops(route_id):
    """Get all stops for a specific route with order"""
    cursor = g.db.cursor()
    
    cursor.execute("""
        SELECT s.*, rs.stop_order, rs.estimated_time_from_prev, rs.distance_from_prev
        FROM stops s
        JOIN route_stops rs ON s.stop_id = rs.stop_id
        WHERE rs.route_id = %s
        ORDER BY rs.stop_order
    """, (route_id,))
    
    stops = cursor.fetchall()
    cursor.close()
    
    return jsonify(stops)

@api_bp.route('/validate-bus-number')
def validate_bus_number():
    """Validate if a bus number belongs to a residence"""
    bus_number = request.args.get('bus_number')
    
    if not bus_number:
        return jsonify({'valid': False, 'message': 'Bus number required'})
    
    from models.residence import Residence
    result = Residence.get_residence_by_bus_number(bus_number)
    
    if result:
        return jsonify({
            'valid': True,
            'residence_id': result['residence_id'],
            'residence_name': result['residence_name'],
            'bus_number_start': result.get('bus_number_start'),
            'bus_number_end': result.get('bus_number_end'),
            'message': f'Valid bus number for {result["residence_name"]}'
        })
    else:
        return jsonify({
            'valid': False,
            'message': 'Invalid bus number. Please check with your residence administrator.'
        })

@api_bp.route('/driver-residence-info')
def driver_residence_info():
    """Get residence info for the logged-in driver"""
    if 'user_id' not in session or session.get('user_type') != 'driver':
        return jsonify({'error': 'Unauthorized'}), 401
    
    cursor = g.db.cursor()
    
    # Get driver's bus and residence
    cursor.execute("""
        SELECT r.*, 
               b.bus_id, b.bus_number, b.bus_model,
               (SELECT COUNT(*) FROM buses WHERE residence_id = r.residence_id) as total_buses,
               (SELECT COUNT(*) FROM buses WHERE residence_id = r.residence_id AND bus_status = 'active') as active_buses,
               (SELECT COUNT(*) FROM trips t 
                JOIN buses b2 ON t.bus_id = b2.bus_id 
                WHERE b2.residence_id = r.residence_id 
                AND t.trip_status = 'in_progress') as active_trips
        FROM buses b
        JOIN residences r ON b.residence_id = r.residence_id
        WHERE b.current_driver_id = %s
    """, (session['user_id'],))
    
    info = cursor.fetchone()
    
    # Get other drivers in same residence
    if info:
        cursor.execute("""
            SELECT u.full_name, u.user_id, b.bus_number, b.bus_status
            FROM users u
            JOIN buses b ON u.user_id = b.current_driver_id
            WHERE b.residence_id = %s AND u.user_id != %s
            LIMIT 5
        """, (info['residence_id'], session['user_id']))
        
        other_drivers = cursor.fetchall()
        info['other_drivers'] = other_drivers
    
    cursor.close()
    
    if info:
        return jsonify(info)
    else:
        return jsonify({'error': 'No residence assigned'}), 404

@api_bp.route('/student/stats/<int:student_id>')
def get_student_stats(student_id):
    """Get statistics for student dashboard"""
    cursor = g.db.cursor()
    
    # Get favorite routes
    cursor.execute("""
        SELECT r.* 
        FROM favorite_routes fr
        JOIN routes r ON fr.route_id = r.route_id
        WHERE fr.student_id = %s
    """, (student_id,))
    
    favorite_routes = cursor.fetchall()
    
    # Get recent trips (check-ins)
    cursor.execute("""
        SELECT q.*, b.bus_number, r.route_name, s.stop_name
        FROM qr_checkins q
        JOIN trips t ON q.trip_id = t.trip_id
        JOIN buses b ON q.bus_id = b.bus_id
        JOIN routes r ON t.route_id = r.route_id
        JOIN stops s ON q.stop_id = s.stop_id
        WHERE q.student_id = %s
        ORDER BY q.checkin_time DESC
        LIMIT 5
    """, (student_id,))
    
    recent_trips = cursor.fetchall()
    
    cursor.close()
    
    return jsonify({
        'favorite_routes': favorite_routes,
        'recent_trips': recent_trips
    })

@api_bp.route('/residence-stats')
def get_residence_stats():
    """Get statistics for all residences"""
    cursor = g.db.cursor()
    
    cursor.execute("""
        SELECT 
            r.residence_id,
            r.residence_name,
            COUNT(DISTINCT b.bus_id) as total_buses,
            SUM(CASE WHEN b.bus_status = 'active' THEN 1 ELSE 0 END) as active_buses,
            COUNT(DISTINCT t.trip_id) as total_trips,
            SUM(CASE WHEN t.trip_status = 'in_progress' THEN 1 ELSE 0 END) as active_trips,
            AVG(t.passenger_count) as avg_passengers
        FROM residences r
        LEFT JOIN buses b ON r.residence_id = b.residence_id
        LEFT JOIN trips t ON b.bus_id = t.bus_id AND t.trip_date = CURDATE()
        WHERE r.is_active = TRUE
        GROUP BY r.residence_id, r.residence_name
    """)
    
    stats = cursor.fetchall()
    cursor.close()
    
    return jsonify(stats)

@api_bp.route('/driver-current-trip')
def get_driver_current_trip():
    """Get current active trip for the logged-in driver"""
    if 'user_id' not in session or session.get('user_type') != 'driver':
        return jsonify({'error': 'Unauthorized'}), 401
    
    cursor = g.db.cursor()
    
    cursor.execute("""
        SELECT 
            t.*,
            b.bus_number,
            b.capacity,
            r.route_name,
            cs.stop_name as current_stop_name,
            ns.stop_name as next_stop_name,
            rs.stop_order as current_stop_order,
            (SELECT AVG(speed) FROM live_locations WHERE trip_id = t.trip_id AND speed > 0) as avg_speed,
            TIMESTAMPDIFF(MINUTE, t.actual_start_time, NOW()) as duration_minutes
        FROM trips t
        JOIN buses b ON t.bus_id = b.bus_id
        JOIN routes r ON t.route_id = r.route_id
        LEFT JOIN stops cs ON t.current_stop_id = cs.stop_id
        LEFT JOIN stops ns ON t.next_stop_id = ns.stop_id
        LEFT JOIN route_stops rs ON (t.route_id = rs.route_id AND t.current_stop_id = rs.stop_id)
        WHERE t.driver_id = %s 
        AND t.trip_status = 'in_progress'
        AND t.trip_date = CURDATE()
        LIMIT 1
    """, (session['user_id'],))
    
    trip = cursor.fetchone()
    
    # Calculate ETA if trip exists
    if trip and trip.get('next_stop_id'):
        # Get latest location
        cursor.execute("""
            SELECT latitude, longitude 
            FROM live_locations 
            WHERE trip_id = %s 
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (trip['trip_id'],))
        
        location = cursor.fetchone()
        
        # Get next stop location
        cursor.execute("SELECT latitude, longitude FROM stops WHERE stop_id = %s", (trip['next_stop_id'],))
        next_stop = cursor.fetchone()
        
        if location and next_stop:
            # Calculate ETA (simplified)
            import math
            lat1, lon1 = float(location['latitude']), float(location['longitude'])
            lat2, lon2 = float(next_stop['latitude']), float(next_stop['longitude'])
            
            # Rough distance calculation
            distance = math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2) * 111
            
            if trip.get('avg_speed') and trip['avg_speed'] > 0:
                eta = (distance / float(trip['avg_speed'])) * 60
                eta += (trip['delay_minutes'] or 0)
                trip['eta'] = round(eta)
    
    cursor.close()
    
    return jsonify({'trip': trip})

@api_bp.route('/student/recent-trips/<int:student_id>')
def get_student_recent_trips(student_id):
    """Get recent trips for a student"""
    cursor = g.db.cursor()
    
    cursor.execute("""
        SELECT q.*, b.bus_number, r.route_name, s.stop_name,
               DATE_FORMAT(q.checkin_time, '%Y-%m-%d %H:%i') as checkin_time
        FROM qr_checkins q
        JOIN trips t ON q.trip_id = t.trip_id
        JOIN buses b ON q.bus_id = b.bus_id
        JOIN routes r ON t.route_id = r.route_id
        JOIN stops s ON q.stop_id = s.stop_id
        WHERE q.student_id = %s
        ORDER BY q.checkin_time DESC
        LIMIT 10
    """, (student_id,))
    
    trips = cursor.fetchall()
    cursor.close()
    
    return jsonify(trips)

@api_bp.route('/student/add-favorite', methods=['POST'])
def add_favorite_route():
    """Add a route to student's favorites"""
    data = request.json
    student_id = data.get('student_id')
    route_id = data.get('route_id')
    
    cursor = g.db.cursor()
    try:
        cursor.execute("""
            INSERT INTO favorite_routes (student_id, route_id)
            VALUES (%s, %s)
        """, (student_id, route_id))
        g.db.commit()
        return jsonify({'success': True})
    except Exception as e:
        g.db.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        cursor.close()

@api_bp.route('/student/remove-favorite', methods=['POST'])
def remove_favorite_route():
    """Remove a route from student's favorites"""
    data = request.json
    student_id = data.get('student_id')
    route_id = data.get('route_id')
    
    cursor = g.db.cursor()
    try:
        cursor.execute("""
            DELETE FROM favorite_routes 
            WHERE student_id = %s AND route_id = %s
        """, (student_id, route_id))
        g.db.commit()
        return jsonify({'success': True})
    except Exception as e:
        g.db.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        cursor.close()