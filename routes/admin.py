# routes/admin.py
# routes/admin.py
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify, g
from utils.decorators import admin_required
from models.user import User
from models.bus import Bus
from models.route import Route, Stop, RouteStop
from models.trip import Trip

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    # Get statistics
    cursor = g.db.cursor()
    
    # User counts
    cursor.execute("SELECT user_type, COUNT(*) as count FROM users GROUP BY user_type")
    user_stats = cursor.fetchall()
    
    # Active trips
    cursor.execute("SELECT COUNT(*) as count FROM trips WHERE trip_status = 'in_progress'")
    active_trips = cursor.fetchone()
    
    # Active buses
    cursor.execute("SELECT COUNT(*) as count FROM buses WHERE bus_status = 'active'")
    active_buses = cursor.fetchone()
    
    # Total routes
    cursor.execute("SELECT COUNT(*) as count FROM routes WHERE is_active = TRUE")
    total_routes = cursor.fetchone()
    
    cursor.close()
    
    return render_template('admin/dashboard.html', 
                          user_stats=user_stats,
                          active_trips=active_trips['count'] if active_trips else 0,
                          active_buses=active_buses['count'] if active_buses else 0,
                          total_routes=total_routes['count'] if total_routes else 0)

@admin_bp.route('/users')
@admin_required
def users():
    cursor = g.db.cursor()
    cursor.execute("SELECT user_id, email, full_name, phone_number, user_type, is_active, last_login FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    cursor.close()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/toggle/<int:user_id>', methods=['POST'])
@admin_required
def toggle_user(user_id):
    cursor = g.db.cursor()
    cursor.execute("UPDATE users SET is_active = NOT is_active WHERE user_id = %s", (user_id,))
    g.db.commit()
    cursor.close()
    return jsonify({'success': True})

@admin_bp.route('/buses')
@admin_required
def buses():
    cursor = g.db.cursor()
    cursor.execute("""
        SELECT b.*, u.full_name as driver_name 
        FROM buses b
        LEFT JOIN users u ON b.current_driver_id = u.user_id
        ORDER BY b.bus_number
    """)
    buses = cursor.fetchall()
    cursor.close()
    return render_template('admin/buses.html', buses=buses)

@admin_bp.route('/buses/add', methods=['GET', 'POST'])
@admin_required
def add_bus():
    if request.method == 'POST':
        bus_number = request.form['bus_number']
        bus_model = request.form['bus_model']
        capacity = request.form['capacity']
        license_plate = request.form['license_plate']
        residence_id = request.form.get('residence_id')
        
        cursor = g.db.cursor()
        cursor.execute("""
            INSERT INTO buses (bus_number, bus_model, capacity, license_plate, residence_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (bus_number, bus_model, capacity, license_plate, residence_id))
        g.db.commit()
        cursor.close()
        
        flash('Bus added successfully!', 'success')
        return redirect(url_for('admin.buses'))
    
    # Get residences for dropdown
    cursor = g.db.cursor()
    cursor.execute("SELECT residence_id, residence_name FROM residences WHERE is_active = TRUE")
    residences = cursor.fetchall()
    cursor.close()
    
    return render_template('admin/add_bus.html', residences=residences)

@admin_bp.route('/routes')
@admin_required
def routes():
    routes = Route.get_all_active()
    return render_template('admin/routes.html', routes=routes)

@admin_bp.route('/routes/add', methods=['GET', 'POST'])
@admin_required
def add_route():
    if request.method == 'POST':
        route_name = request.form['route_name']
        route_code = request.form['route_code']
        route_description = request.form['route_description']
        total_distance = request.form['total_distance']
        estimated_duration = request.form['estimated_duration']
        route_type = request.form['route_type']
        
        # You'll need to add this method to your Route model
        cursor = g.db.cursor()
        cursor.execute("""
            INSERT INTO routes (route_name, route_code, route_description, total_distance, estimated_duration, route_type)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (route_name, route_code, route_description, total_distance, estimated_duration, route_type))
        g.db.commit()
        route_id = cursor.lastrowid
        cursor.close()
        
        flash('Route added successfully!', 'success')
        return redirect(url_for('admin.routes'))
    
    return render_template('admin/add_route.html')

@admin_bp.route('/stops')
@admin_required
def stops():
    stops = Stop.get_all()
    return render_template('admin/stops.html', stops=stops)

@admin_bp.route('/stops/add', methods=['GET', 'POST'])
@admin_required
def add_stop():
    if request.method == 'POST':
        stop_name = request.form['stop_name']
        stop_code = request.form['stop_code']
        latitude = request.form['latitude']
        longitude = request.form['longitude']
        address = request.form['address']
        landmark = request.form.get('landmark', '')
        
        stop_id = Stop.create(stop_name, stop_code, latitude, longitude, address, landmark)
        
        flash('Stop added successfully!', 'success')
        return redirect(url_for('admin.stops'))
    
    return render_template('admin/add_stop.html')

@admin_bp.route('/trips')
@admin_required
def trips():
    trips = Trip.get_active_trips()
    return render_template('admin/trips.html', trips=trips)

@admin_bp.route('/route-stops/<int:route_id>', methods=['GET'])
@admin_required
def get_route_stops(route_id):
    """Get stops for a specific route (for AJAX)"""
    stops = RouteStop.get_stops_for_route(route_id)
    return jsonify(stops)

@admin_bp.route('/assign-stop-to-route', methods=['POST'])
@admin_required
def assign_stop_to_route():
    """Assign a stop to a route"""
    data = request.json
    route_id = data.get('route_id')
    stop_id = data.get('stop_id')
    stop_order = data.get('stop_order')
    estimated_time = data.get('estimated_time')
    distance = data.get('distance')
    
    cursor = g.db.cursor()
    try:
        cursor.execute("""
            INSERT INTO route_stops (route_id, stop_id, stop_order, estimated_time_from_prev, distance_from_prev)
            VALUES (%s, %s, %s, %s, %s)
        """, (route_id, stop_id, stop_order, estimated_time, distance))
        g.db.commit()
        return jsonify({'success': True})
    except Exception as e:
        g.db.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        cursor.close()

@admin_bp.route('/remove-stop-from-route/<int:route_id>/<int:stop_id>', methods=['POST'])
@admin_required
def remove_stop_from_route(route_id, stop_id):
    """Remove a stop from a route"""
    RouteStop.remove_stop_from_route(route_id, stop_id)
    return jsonify({'success': True})