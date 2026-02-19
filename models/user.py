# models/user.py
from flask import session
from werkzeug.security import generate_password_hash, check_password_hash
from app import mysql
import MySQLdb.cursors

class User:
    @staticmethod
    def get_by_id(user_id):
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        return user
    
    @staticmethod
    def get_by_email(email):
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        return user
    
    @staticmethod
    def create(email, password, full_name, phone_number, user_type='student'):
        password_hash = generate_password_hash(password)
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (email, password_hash, full_name, phone_number, user_type)
                VALUES (%s, %s, %s, %s, %s)
            """, (email, password_hash, full_name, phone_number, user_type))
            mysql.connection.commit()
            user_id = cursor.lastrowid
            return user_id
        except Exception as e:
            mysql.connection.rollback()
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
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE users SET last_login = NOW() WHERE user_id = %s", (user_id,))
        mysql.connection.commit()
        cursor.close()
    
    @staticmethod
    def is_logged_in():
        return 'user_id' in session
    
    @staticmethod
    def current_user():
        if 'user_id' in session:
            return User.get_by_id(session['user_id'])
        return None