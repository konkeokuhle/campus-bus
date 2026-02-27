# routes/driver.py
from flask import Blueprint, render_template, session, request, jsonify, redirect, url_for, g
from utils.decorators import driver_required
from models.trip import Trip, LiveLocation
from models.bus import Bus
from app import socketio
from datetime import datetime

driver_bp = Blueprint('driver', __name__)

@driver_bp.route('/dashboard')
@driver_required
def dashboard():
    """Driver dashboard with live trip management"""
    cursor = g.db.cursor()
    
    # Get driver's current active trip
    cursor.execute("""
        SELECT t.*, b.bus_number, b.capacity, b.bus_id, r.route_name,
               r.route_id,
               cs.stop_name as current_stop_name,
               ns.stop_name as next_stop_name,
               cs.stop_id as current_stop_id,
               ns.stop_id as next_stop_id,
               rs.stop_order as current_stop_order
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
    
    active_trip = cursor.fetchone()
    
    # Get upcoming stops if trip exists
    upcoming_stops = []
    if active_trip:
        cursor.execute("""
            SELECT s.*, rs.stop_order, rs.estimated_time_from_prev
            FROM stops s
            JOIN route_stops rs ON s.stop_id = rs.stop_id
            WHERE rs.route_id = %s
            AND rs.stop_order > %s
            ORDER BY rs.stop_order
            LIMIT 4
        """, (active_trip['route_id'], active_trip.get('current_stop_order', 0)))
        upcoming_stops = cursor.fetchall()
        
        # Get passenger count if available
        if 'passenger_count' not in active_trip:
            active_trip['passenger_count'] = 0
    
    cursor.close()
    
    return render_template('driver/dashboard.html', 
                         trip=active_trip,
                         upcoming_stops=upcoming_stops)

@driver_bp.route('/trip-management')
@driver_required
def trip_management():
    """View and manage scheduled trips"""
    cursor = g.db.cursor()
    
    # Get today's trips for this driver
    cursor.execute("""
        SELECT t.*, b.bus_number, r.route_name
        FROM trips t
        JOIN buses b ON t.bus_id = b.bus_id
        JOIN routes r ON t.route_id = r.route_id
        WHERE t.driver_id = %s 
        AND t.trip_date = CURDATE()
        ORDER BY t.scheduled_start_time
    """, (session['user_id'],))
    
    trips = cursor.fetchall()
    cursor.close()
    
    return render_template('driver/trip-management.html', trips=trips)

@driver_bp.route('/api/start-trip/<int:trip_id>', methods=['POST'])
@driver_required
def start_trip(trip_id):
    """Start a trip"""
    cursor = g.db.cursor()
    
    try:
        # Update trip status
        cursor.execute("""
            UPDATE trips 
            SET trip_status = 'in_progress', 
                actual_start_time = NOW() 
            WHERE trip_id = %s
        """, (trip_id,))
        
        # Get first stop for this route
        cursor.execute("""
            SELECT rs.stop_id, s.stop_name 
            FROM route_stops rs
            JOIN stops s ON rs.stop_id = s.stop_id
            WHERE rs.route_id = (SELECT route_id FROM trips WHERE trip_id = %s)
            ORDER BY rs.stop_order LIMIT 1
        """, (trip_id,))
        
        first_stop = cursor.fetchone()
        
        if first_stop:
            cursor.execute("""
                UPDATE trips 
                SET next_stop_id = %s,
                    current_stop_order = 0
                WHERE trip_id = %s
            """, (first_stop['stop_id'], trip_id))
        
        # Update bus status
        cursor.execute("""
            UPDATE buses b
            JOIN trips t ON b.bus_id = t.bus_id
            SET b.bus_status = 'active'
            WHERE t.trip_id = %s
        """, (trip_id,))
        
        g.db.commit()
        
        # Notify students via Socket.IO
        socketio.emit('trip_started', {
            'trip_id': trip_id,
            'message': 'Trip has started!'
        }, room='students')
        
        return jsonify({'success': True})
        
    except Exception as e:
        g.db.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        cursor.close()

@driver_bp.route('/api/complete-trip/<int:trip_id>', methods=['POST'])
@driver_required
def complete_trip(trip_id):
    """Complete a trip"""
    cursor = g.db.cursor()
    
    try:
        cursor.execute("""
            UPDATE trips 
            SET trip_status = 'completed', 
                actual_end_time = NOW() 
            WHERE trip_id = %s
        """, (trip_id,))
        
        # Update bus status
        cursor.execute("""
            UPDATE buses b
            JOIN trips t ON b.bus_id = t.bus_id
            SET b.bus_status = 'active'
            WHERE t.trip_id = %s
        """, (trip_id,))
        
        g.db.commit()
        
        socketio.emit('trip_completed', {
            'trip_id': trip_id,
            'message': 'Trip completed!'
        }, room='students')
        
        return jsonify({'success': True})
        
    except Exception as e:
        g.db.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        cursor.close()

@driver_bp.route('/api/update-location', methods=['POST'])
@driver_required
def update_location():
    """Update bus location (called from frontend JS)"""
    data = request.json
    trip_id = data['trip_id']
    latitude = data['latitude']
    longitude = data['longitude']
    speed = data.get('speed', 0)
    heading = data.get('heading', 0)
    
    # Save to database
    LiveLocation.update_location(trip_id, latitude, longitude, speed, heading)
    
    # Get bus and route info for the update
    cursor = g.db.cursor()
    cursor.execute("""
        SELECT t.trip_id, b.bus_number, r.route_name, t.next_stop_id,
               s.stop_name as next_stop_name, t.passenger_count, b.capacity
        FROM trips t
        JOIN buses b ON t.bus_id = b.bus_id
        JOIN routes r ON t.route_id = r.route_id
        LEFT JOIN stops s ON t.next_stop_id = s.stop_id
        WHERE t.trip_id = %s
    """, (trip_id,))
    
    trip_info = cursor.fetchone()
    cursor.close()
    
    # Broadcast to all connected clients
    socketio.emit('bus_location_updated', {
        'trip_id': trip_id,
        'bus_number': trip_info['bus_number'] if trip_info else 'Unknown',
        'route_name': trip_info['route_name'] if trip_info else 'Unknown',
        'next_stop': trip_info['next_stop_name'] if trip_info else 'Unknown',
        'latitude': latitude,
        'longitude': longitude,
        'speed': speed,
        'heading': heading,
        'occupancy': trip_info['passenger_count'] if trip_info else 0,
        'capacity': trip_info['capacity'] if trip_info else 40,
        'timestamp': datetime.utcnow().isoformat()
    }, room='students')
    
    return jsonify({'success': True})

@driver_bp.route('/api/arrived', methods=['POST'])
@driver_required
def mark_arrived():
    """Mark arrival at current stop"""
    data = request.json
    trip_id = data.get('trip_id')
    
    cursor = g.db.cursor()
    
    try:
        # Get current trip info
        cursor.execute("""
            SELECT t.*, rs.stop_order, rs.stop_id as current_stop_id,
                   rs.estimated_time_from_prev, s.stop_name
            FROM trips t
            JOIN route_stops rs ON t.route_id = rs.route_id
            JOIN stops s ON rs.stop_id = s.stop_id
            WHERE t.trip_id = %s 
            AND rs.stop_id = t.next_stop_id
        """, (trip_id,))
        
        trip = cursor.fetchone()
        
        if trip:
            # Mark current stop as completed
            cursor.execute("""
                UPDATE trips 
                SET current_stop_id = %s,
                    current_stop_order = %s,
                    last_stop_arrival = NOW()
                WHERE trip_id = %s
            """, (trip['current_stop_id'], trip['stop_order'], trip_id))
            
            # Get next stop
            cursor.execute("""
                SELECT rs.stop_id, s.stop_name 
                FROM route_stops rs
                JOIN stops s ON rs.stop_id = s.stop_id
                WHERE rs.route_id = %s AND rs.stop_order > %s
                ORDER BY rs.stop_order LIMIT 1
            """, (trip['route_id'], trip['stop_order']))
            
            next_stop = cursor.fetchone()
            
            if next_stop:
                cursor.execute("""
                    UPDATE trips 
                    SET next_stop_id = %s,
                        departure_time = DATE_ADD(NOW(), INTERVAL 2 MINUTE)
                    WHERE trip_id = %s
                """, (next_stop['stop_id'], trip_id))
                
                # Notify students about arrival
                socketio.emit('bus_arrived', {
                    'trip_id': trip_id,
                    'stop_id': trip['current_stop_id'],
                    'stop_name': trip['stop_name'],
                    'next_stop': next_stop['stop_name'],
                    'departure_in': 2
                }, room='students')
            else:
                # End of route - complete trip
                cursor.execute("""
                    UPDATE trips 
                    SET trip_status = 'completed',
                        actual_end_time = NOW() 
                    WHERE trip_id = %s
                """, (trip_id,))
                
                socketio.emit('trip_completed', {
                    'trip_id': trip_id,
                    'message': 'Trip completed!'
                }, room='students')
        
        g.db.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        g.db.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        cursor.close()

@driver_bp.route('/api/delay', methods=['POST'])
@driver_required
def report_delay():
    """Report delay"""
    data = request.json
    trip_id = data.get('trip_id')
    delay_minutes = data.get('delay_minutes', 5)
    
    cursor = g.db.cursor()
    
    try:
        cursor.execute("""
            UPDATE trips 
            SET delay_minutes = %s 
            WHERE trip_id = %s
        """, (delay_minutes, trip_id))
        
        g.db.commit()
        
        # Get trip info for notification
        cursor.execute("""
            SELECT t.trip_id, b.bus_number, r.route_name
            FROM trips t
            JOIN buses b ON t.bus_id = b.bus_id
            JOIN routes r ON t.route_id = r.route_id
            WHERE t.trip_id = %s
        """, (trip_id,))
        
        trip_info = cursor.fetchone()
        
        # Notify students about delay
        socketio.emit('bus_delayed', {
            'trip_id': trip_id,
            'bus_number': trip_info['bus_number'] if trip_info else 'Unknown',
            'route_name': trip_info['route_name'] if trip_info else 'Unknown',
            'delay': delay_minutes
        }, room='students')
        
        return jsonify({'success': True})
        
    except Exception as e:
        g.db.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        cursor.close()

@driver_bp.route('/api/emergency', methods=['POST'])
@driver_required
def emergency_alert():
    """Send emergency alert"""
    data = request.json
    trip_id = data.get('trip_id')
    
    cursor = g.db.cursor()
    
    try:
        # Get driver and trip info
        cursor.execute("""
            SELECT u.full_name, b.bus_number, r.route_name
            FROM trips t
            JOIN users u ON t.driver_id = u.user_id
            JOIN buses b ON t.bus_id = b.bus_id
            JOIN routes r ON t.route_id = r.route_id
            WHERE t.trip_id = %s
        """, (trip_id,))
        
        info = cursor.fetchone()
        
        # Log emergency (assuming system_logs table exists)
        try:
            cursor.execute("""
                INSERT INTO system_logs (log_type, user_id, action, description)
                VALUES ('emergency', %s, 'EMERGENCY_ALERT', %s)
            """, (session['user_id'], f'Emergency alert from trip {trip_id} on bus {info["bus_number"] if info else "Unknown"}'))
        except:
            # If system_logs table doesn't exist, just continue
            pass
        
        g.db.commit()
        
        # Broadcast to all students and admin
        socketio.emit('emergency_alert', {
            'trip_id': trip_id,
            'bus_number': info['bus_number'] if info else 'Unknown',
            'driver_name': info['full_name'] if info else 'Unknown',
            'route': info['route_name'] if info else 'Unknown',
            'message': '🚨 EMERGENCY ALERT: Please clear the area!',
            'timestamp': datetime.utcnow().isoformat()
        }, room='students')
        
        # Also notify admin room
        socketio.emit('admin_emergency', {
            'trip_id': trip_id,
            'bus_number': info['bus_number'] if info else 'Unknown',
            'driver_name': info['full_name'] if info else 'Unknown',
            'route': info['route_name'] if info else 'Unknown',
            'message': '🚨 Driver has triggered an emergency alert!'
        }, room='admins')
        
        return jsonify({'success': True})
        
    except Exception as e:
        g.db.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        cursor.close()

@driver_bp.route('/api/passenger-count', methods=['POST'])
@driver_required
def update_passenger_count():
    """Update passenger count"""
    data = request.json
    trip_id = data.get('trip_id')
    count = data.get('count')
    
    cursor = g.db.cursor()
    
    try:
        cursor.execute("""
            UPDATE trips 
            SET passenger_count = %s 
            WHERE trip_id = %s
        """, (count, trip_id))
        
        # Get bus capacity
        cursor.execute("""
            SELECT b.capacity
            FROM trips t
            JOIN buses b ON t.bus_id = b.bus_id
            WHERE t.trip_id = %s
        """, (trip_id,))
        
        capacity = cursor.fetchone()
        
        g.db.commit()
        
        # Update students with occupancy info
        socketio.emit('occupancy_updated', {
            'trip_id': trip_id,
            'count': count,
            'capacity': capacity['capacity'] if capacity else 40,
            'percentage': round((count / capacity['capacity']) * 100) if capacity else 0
        }, room='students')
        
        return jsonify({'success': True})
        
    except Exception as e:
        g.db.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        cursor.close()

@driver_bp.route('/api/next-stop/<int:trip_id>', methods=['GET'])
@driver_required
def get_next_stop(trip_id):
    """Get next stop information"""
    cursor = g.db.cursor()
    
    cursor.execute("""
        SELECT s.*, rs.stop_order, rs.estimated_time_from_prev
        FROM trips t
        JOIN route_stops rs ON t.route_id = rs.route_id
        JOIN stops s ON rs.stop_id = s.stop_id
        WHERE t.trip_id = %s
        AND rs.stop_id = t.next_stop_id
    """, (trip_id,))
    
    next_stop = cursor.fetchone()
    cursor.close()
    
    return jsonify(next_stop)