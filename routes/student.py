# routes/student.py
from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify, request
from utils.decorators import student_required
from models.trip import Trip
from models.route import Route
from models.lost_item import LostItem

student_bp = Blueprint('student', __name__)

@student_bp.route('/dashboard')
@student_required
def dashboard():
    return render_template('student/dashboard.html')

@student_bp.route('/lost-found')
@student_required
def lost_found():
    # Get user's reported items
    items = LostItem.search(reported_by=session['user_id'])
    return render_template('student/lost-found.html', items=items)

@student_bp.route('/lost-found/report', methods=['GET', 'POST'])
@student_required
def report_lost_item():
    if request.method == 'POST':
        item_name = request.form['item_name']
        description = request.form['description']
        category = request.form['category']
        lost_date = request.form['lost_date']
        bus_id = request.form.get('bus_id')
        contact_info = request.form.get('contact_info')
        
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
    
    # Get active trips for bus selection
    active_trips = Trip.get_active_trips()
    return render_template('student/report-lost.html', trips=active_trips)

@student_bp.route('/profile')
@student_required
def profile():
    return render_template('student/profile.html')