# routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.user import User
import MySQLdb
import traceback

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            full_name = request.form['full_name']
            phone = request.form['phone']
            user_type = request.form.get('user_type', 'student')
            
            print(f"Attempting to register: {email}, {full_name}, {user_type}")
            
            # Check if user exists
            existing_user = User.get_by_email(email)
            if existing_user:
                return "Email already registered", 400
            
            # Create user
            user_id = User.create(email, password, full_name, phone, user_type)
            print(f"User created with ID: {user_id}")
            
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            print(f"Error: {str(e)}")
            return f"Registration failed: {str(e)}", 500
    
    return render_template('auth/register.html')
@auth_bp.route('/test-session')
def test_session():
    from flask import session
    session['test'] = 'Session is working!'
    return f"""
    <h1>Session Test</h1>
    <p>Session value set: {session.get('test')}</p>
    <p><a href="{url_for('auth.test_session_check')}">Check Session</a></p>
    """

@auth_bp.route('/test-session-check')
def test_session_check():
    from flask import session
    return f"Session value retrieved: {session.get('test', 'Not found')}"
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            
            user = User.authenticate(email, password)
            
            if user:
                session['user_id'] = user['user_id']
                session['user_type'] = user['user_type']
                session['full_name'] = user['full_name']
                
                User.update_last_login(user['user_id'])
                
                # Redirect based on user type
                if user['user_type'] == 'student':
                    return redirect(url_for('student.dashboard'))
                elif user['user_type'] == 'driver':
                    return redirect(url_for('driver.dashboard'))
                elif user['user_type'] == 'admin':
                    return redirect(url_for('admin.dashboard'))
            else:
                return "Invalid email or password", 401
        except Exception as e:
            print(f"Login error: {str(e)}")
            return f"Login error: {str(e)}", 500
    
    return render_template('auth/login.html')
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))