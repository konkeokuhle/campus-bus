# routes/driver.py
from flask import Blueprint, render_template, session, request, jsonify, redirect, url_for
from utils.decorators import driver_required
from models.trip import Trip, LiveLocation
from models.bus import Bus
from app import socketio

driver_bp = Blueprint('driver', __name__)

@driver_bp.route('/dashboard')
@driver_required
def dashboard():
    # Get driver's trips for today
    trips = Trip.get_by_driver(session['user_id'])
    return render_template('driver/dashboard.html', trips=trips)

@driver_bp.route('/trip/<int:trip_id>')
@driver_required
def manage_trip(trip_id):
    return render_template('driver/trip-management.html', trip_id=trip_id)

@driver_bp.route('/api/update-location', methods=['POST'])
@driver_required
def update_location():
    data = request.json
    trip_id = data['trip_id']
    latitude = data['latitude']
    longitude = data['longitude']
    speed = data.get('speed', 0)
    heading = data.get('heading', 0)
    
    # Save to database
    LiveLocation.update_location(trip_id, latitude, longitude, speed, heading)
    
    # Broadcast to all connected clients
    socketio.emit('bus_location_updated', {
        'trip_id': trip_id,
        'latitude': latitude,
        'longitude': longitude,
        'speed': speed,
        'heading': heading
    })
    
    return jsonify({'success': True})

@driver_bp.route('/api/start-trip/<int:trip_id>', methods=['POST'])
@driver_required
def start_trip(trip_id):
    Trip.start_trip(trip_id)
    return jsonify({'success': True})

@driver_bp.route('/api/complete-trip/<int:trip_id>', methods=['POST'])
@driver_required
def complete_trip(trip_id):
    Trip.complete_trip(trip_id)
    return jsonify({'success': True})