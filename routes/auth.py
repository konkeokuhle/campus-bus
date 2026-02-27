# routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from models.user import User
from models.bus import Bus
from models.residence import Residence
import traceback

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Get residences for the dropdown
    residences = Residence.get_all_active()
    
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
                flash('Email already registered', 'danger')
                return redirect(url_for('auth.register'))
            
            # Create user first
            user_id = User.create(email, password, full_name, phone, user_type)
            print(f"User created with ID: {user_id}")
            
            # If driver, handle bus assignment
            if user_type == 'driver':
                bus_number = request.form.get('bus_number')
                residence_id = request.form.get('residence_id')
                bus_model = request.form.get('bus_model', 'Standard Bus')
                
                # Validate bus number belongs to selected residence
                valid, result = Residence.validate_bus_number(bus_number, residence_id)
                
                if not valid:
                    flash(f'Invalid bus number: {result}', 'danger')
                    return redirect(url_for('auth.register'))
                
                # Check if bus already exists
                cursor = g.db.cursor()
                cursor.execute("SELECT * FROM buses WHERE bus_number = %s", (bus_number,))
                existing_bus = cursor.fetchone()
                
                if existing_bus:
                    # Assign existing bus to this driver
                    cursor.execute("""
                        UPDATE buses 
                        SET current_driver_id = %s, 
                            bus_status = 'active',
                            residence_id = %s
                        WHERE bus_id = %s
                    """, (user_id, residence_id, existing_bus['bus_id']))
                else:
                    # Create new bus
                    cursor.execute("""
                        INSERT INTO buses (bus_number, bus_model, capacity, license_plate, 
                                         current_driver_id, residence_id, qr_code_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        bus_number, 
                        bus_model, 
                        40,  # default capacity
                        f"TMP-{bus_number}",  # temporary license plate
                        user_id, 
                        residence_id,
                        f"QR-{bus_number}"
                    ))
                
                g.db.commit()
                cursor.close()
                
                flash('Driver registration successful! You can now login.', 'success')
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            print(f"Registration error: {str(e)}")
            traceback.print_exc()
            flash(f'Registration failed: {str(e)}', 'danger')
    
    return render_template('auth/register.html', residences=residences)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            
            print(f"Login attempt for: {email}")
            
            user = User.authenticate(email, password)
            
            if user:
                # Set session variables
                session['user_id'] = user['user_id']
                session['user_type'] = user['user_type']
                session['full_name'] = user['full_name']
                
                # Update last login
                User.update_last_login(user['user_id'])
                
                # Force session to save
                session.modified = True
                
                print(f"Login successful for: {email}, session: {dict(session)}")
                flash('Login successful!', 'success')
                
                # Redirect based on user type
                if user['user_type'] == 'student':
                    return redirect(url_for('student.dashboard'))
                elif user['user_type'] == 'driver':
                    return redirect(url_for('driver.dashboard'))
                elif user['user_type'] == 'admin':
                    return redirect(url_for('admin.dashboard'))
                else:
                    return redirect(url_for('main.index'))
            else:
                print(f"Login failed for: {email}")
                flash('Invalid email or password', 'danger')
                
        except Exception as e:
            print(f"Login error: {str(e)}")
            traceback.print_exc()
            flash(f'Login error: {str(e)}', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    """Log out the current user"""
    # Clear all session data
    session.clear()
    # Flash a success message
    flash('You have been logged out successfully', 'success')
    # Redirect to home page
    return redirect(url_for('main.index'))

# Test route for session debugging (optional)
@auth_bp.route('/test-session')
def test_session():
    """Test if session is working"""
    if 'user_id' in session:
        return f"Session is working! User ID: {session['user_id']}, Type: {session['user_type']}"
    else:
        return "No active session"