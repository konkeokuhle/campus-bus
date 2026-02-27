# models/user.py
# models/user.py
from flask import session, g
from werkzeug.security import generate_password_hash, check_password_hash

class User:
    @staticmethod
    def get_by_id(user_id):
        cursor = g.db.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        return user
    
    @staticmethod
    def get_by_email(email):
        cursor = g.db.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        return user
    
    @staticmethod
    def create(email, password, full_name, phone_number, user_type='student'):
        password_hash = generate_password_hash(password)
        cursor = g.db.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (email, password_hash, full_name, phone_number, user_type)
                VALUES (%s, %s, %s, %s, %s)
            """, (email, password_hash, full_name, phone_number, user_type))
            g.db.commit()
            user_id = cursor.lastrowid
            return user_id
        except Exception as e:
            g.db.rollback()
            raise e
        finally:
            cursor.close()
    
    @staticmethod
    def authenticate(email, password):
        user = User.get_by_email(email)
        if user and check_password_hash(user['password_hash'], password):
            return user
        return None
    
    @staticmethod
    def update_last_login(user_id):
        cursor = g.db.cursor()
        cursor.execute("UPDATE users SET last_login = NOW() WHERE user_id = %s", (user_id,))
        g.db.commit()
        cursor.close()
    
    @staticmethod
    def is_logged_in():
        return 'user_id' in session
    
    @staticmethod
    def current_user():
        if 'user_id' in session:
            return User.get_by_id(session['user_id'])
        return None