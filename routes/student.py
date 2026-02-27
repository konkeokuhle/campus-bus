# routes/student.py
from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify, request, g
from utils.decorators import student_required
from models.trip import Trip
from models.route import Route
from models.lost_item import LostItem
from datetime import datetime

student_bp = Blueprint('student', __name__)

@student_bp.route('/dashboard')
@student_required
def dashboard():
    """Student dashboard with live bus tracking"""
    print(f"Student dashboard accessed - User ID: {session.get('user_id')}, Name: {session.get('full_name')}")
    return render_template('student/dashboard.html')

@student_bp.route('/lost-found')
@student_required
def lost_found():
    """Lost and found page"""
    try:
        # Get user's reported items
        items = LostItem.search(reported_by=session['user_id'])
        return render_template('student/lost-found.html', items=items)
    except Exception as e:
        print(f"Error in lost_found: {e}")
        flash('Error loading lost items', 'danger')
        return render_template('student/lost-found.html', items=[])

@student_bp.route('/lost-found/report', methods=['GET', 'POST'])
@student_required
def report_lost_item():
    """Report a lost item"""
    if request.method == 'POST':
        try:
            item_name = request.form['item_name']
            description = request.form['description']
            category = request.form['category']
            lost_date = request.form['lost_date']
            bus_id = request.form.get('bus_id')
            contact_info = request.form.get('contact_info', session.get('email', ''))
            
            item_id = LostItem.create(
                reported_by=session['user_id'],
                item_name=item_name,
                description=description,
                category=category,
                lost_date=lost_date,
                bus_id=bus_id,
                contact_info=contact_info
            )
            
            flash('Lost item reported successfully!', 'success')
            return redirect(url_for('student.lost_found'))
            
        except Exception as e:
            print(f"Error reporting lost item: {e}")
            flash(f'Error reporting item: {str(e)}', 'danger')
    
    # Get active trips for bus selection
    try:
        active_trips = Trip.get_active_trips()
    except:
        active_trips = []
    
    return render_template('student/report-lost.html', trips=active_trips)

@student_bp.route('/profile')
@student_required
def profile():
    """Student profile page"""
    cursor = g.db.cursor()
    
    # Get student details
    cursor.execute("""
        SELECT user_id, email, full_name, phone_number, 
               DATE_FORMAT(created_at, '%d %b %Y') as joined_date
        FROM users 
        WHERE user_id = %s
    """, (session['user_id'],))
    
    user = cursor.fetchone()
    
    # Get statistics
    cursor.execute("""
        SELECT 
            (SELECT COUNT(*) FROM favorite_routes WHERE student_id = %s) as favorite_count,
            (SELECT COUNT(*) FROM qr_checkins WHERE student_id = %s) as trip_count
    """, (session['user_id'], session['user_id']))
    
    stats = cursor.fetchone()
    cursor.close()
    
    return render_template('student/profile.html', user=user, stats=stats)

@student_bp.route('/favorites')
@student_required
def favorites():
    """Student favorite routes"""
    cursor = g.db.cursor()
    
    cursor.execute("""
        SELECT r.*, 
               (SELECT COUNT(*) FROM trips t WHERE t.route_id = r.route_id AND t.trip_date = CURDATE()) as today_trips
        FROM favorite_routes fr
        JOIN routes r ON fr.route_id = r.route_id
        WHERE fr.student_id = %s
    """, (session['user_id'],))
    
    favorites = cursor.fetchall()
    cursor.close()
    
    return render_template('student/favorites.html', favorites=favorites)

@student_bp.route('/favorites/add/<int:route_id>', methods=['POST'])
@student_required
def add_favorite(route_id):
    """Add a route to favorites"""
    cursor = g.db.cursor()
    try:
        cursor.execute("""
            INSERT INTO favorite_routes (student_id, route_id)
            VALUES (%s, %s)
        """, (session['user_id'], route_id))
        g.db.commit()
        return jsonify({'success': True, 'message': 'Route added to favorites'})
    except Exception as e:
        g.db.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        cursor.close()

@student_bp.route('/favorites/remove/<int:route_id>', methods=['POST'])
@student_required
def remove_favorite(route_id):
    """Remove a route from favorites"""
    cursor = g.db.cursor()
    try:
        cursor.execute("""
            DELETE FROM favorite_routes 
            WHERE student_id = %s AND route_id = %s
        """, (session['user_id'], route_id))
        g.db.commit()
        return jsonify({'success': True, 'message': 'Route removed from favorites'})
    except Exception as e:
        g.db.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        cursor.close()

@student_bp.route('/api/recent-trips')
@student_required
def api_recent_trips():
    """API endpoint for recent trips"""
    cursor = g.db.cursor()
    
    cursor.execute("""
        SELECT 
            q.checkin_id,
            DATE_FORMAT(q.checkin_time, '%%H:%%i %%d %%b') as time,
            b.bus_number,
            r.route_name,
            s.stop_name as boarded_at
        FROM qr_checkins q
        JOIN trips t ON q.trip_id = t.trip_id
        JOIN buses b ON q.bus_id = b.bus_id
        JOIN routes r ON t.route_id = r.route_id
        JOIN stops s ON q.stop_id = s.stop_id
        WHERE q.student_id = %s
        ORDER BY q.checkin_time DESC
        LIMIT 5
    """, (session['user_id'],))
    
    trips = cursor.fetchall()
    cursor.close()
    
    return jsonify(trips)

@student_bp.route('/api/stats')
@student_required
def api_stats():
    """API endpoint for student statistics"""
    cursor = g.db.cursor()
    
    cursor.execute("""
        SELECT 
            (SELECT COUNT(*) FROM favorite_routes WHERE student_id = %s) as favorite_count,
            (SELECT COUNT(*) FROM qr_checkins WHERE student_id = %s) as total_trips,
            (SELECT COUNT(*) FROM lost_items WHERE reported_by = %s) as lost_items_count
    """, (session['user_id'], session['user_id'], session['user_id']))
    
    stats = cursor.fetchone()
    cursor.close()
    
    return jsonify(stats)

@student_bp.route('/api/favorite-routes')
@student_required
def api_favorite_routes():
    """API endpoint for favorite routes"""
    cursor = g.db.cursor()
    
    cursor.execute("""
        SELECT r.*
        FROM favorite_routes fr
        JOIN routes r ON fr.route_id = r.route_id
        WHERE fr.student_id = %s
        ORDER BY r.route_name
    """, (session['user_id'],))
    
    routes = cursor.fetchall()
    cursor.close()
    
    return jsonify(routes)