# models/bus.py
from app import mysql
import MySQLdb.cursors

class Bus:
    @staticmethod
    def get_all_active():
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT b.*, u.full_name as driver_name 
            FROM buses b
            LEFT JOIN users u ON b.current_driver_id = u.user_id
            WHERE b.bus_status = 'active'
        """)
        buses = cursor.fetchall()
        cursor.close()
        return buses
    
    @staticmethod
    def get_by_id(bus_id):
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM buses WHERE bus_id = %s", (bus_id,))
        bus = cursor.fetchone()
        cursor.close()
        return bus
    
    @staticmethod
    def get_by_driver(driver_id):
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM buses WHERE current_driver_id = %s", (driver_id,))
        bus = cursor.fetchone()
        cursor.close()
        return bus
    
    @staticmethod
    def assign_driver(bus_id, driver_id):
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE buses SET current_driver_id = %s WHERE bus_id = %s", 
                      (driver_id, bus_id))
        mysql.connection.commit()
        cursor.close()
    
    @staticmethod
    def update_status(bus_id, status):
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE buses SET bus_status = %s WHERE bus_id = %s", 
                      (status, bus_id))
        mysql.connection.commit()
        cursor.close()