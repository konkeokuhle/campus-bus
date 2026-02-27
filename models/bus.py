# models/bus.py
# models/bus.py
from flask import g

class Bus:
    @staticmethod
    def get_all_active():
        cursor = g.db.cursor()
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
        cursor = g.db.cursor()
        cursor.execute("SELECT * FROM buses WHERE bus_id = %s", (bus_id,))
        bus = cursor.fetchone()
        cursor.close()
        return bus
    
    @staticmethod
    def get_by_driver(driver_id):
        cursor = g.db.cursor()
        cursor.execute("SELECT * FROM buses WHERE current_driver_id = %s", (driver_id,))
        bus = cursor.fetchone()
        cursor.close()
        return bus
    
    @staticmethod
    def assign_driver(bus_id, driver_id):
        cursor = g.db.cursor()
        cursor.execute("UPDATE buses SET current_driver_id = %s WHERE bus_id = %s", 
                      (driver_id, bus_id))
        g.db.commit()
        cursor.close()
    
    @staticmethod
    def update_status(bus_id, status):
        cursor = g.db.cursor()
        cursor.execute("UPDATE buses SET bus_status = %s WHERE bus_id = %s", 
                      (status, bus_id))
        g.db.commit()
        cursor.close()
    
    @staticmethod
    def create(bus_number, bus_model, capacity, license_plate, residence_id=None, qr_code_id=None):
        cursor = g.db.cursor()
        cursor.execute("""
            INSERT INTO buses (bus_number, bus_model, capacity, license_plate, residence_id, qr_code_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (bus_number, bus_model, capacity, license_plate, residence_id, qr_code_id))
        g.db.commit()
        bus_id = cursor.lastrowid
        cursor.close()
        return bus_id
    
    @staticmethod
    def get_by_residence(residence_id):
        cursor = g.db.cursor()
        cursor.execute("""
            SELECT b.*, u.full_name as driver_name 
            FROM buses b
            LEFT JOIN users u ON b.current_driver_id = u.user_id
            WHERE b.residence_id = %s
        """, (residence_id,))
        buses = cursor.fetchall()
        cursor.close()
        return buses
    
    @staticmethod
    def get_available_buses():
        cursor = g.db.cursor()
        cursor.execute("""
            SELECT b.* 
            FROM buses b
            WHERE b.current_driver_id IS NULL 
            AND b.bus_status = 'active'
        """)
        buses = cursor.fetchall()
        cursor.close()
        return buses