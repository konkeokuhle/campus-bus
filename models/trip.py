# models/trip.py
from flask import g
from datetime import datetime

class Trip:
    @staticmethod
    def get_active_trips():
        cursor = g.db.cursor()
        cursor.execute("""
            SELECT t.*, b.bus_number, r.route_name, 
                   cs.stop_name as current_stop_name,
                   ns.stop_name as next_stop_name,
                   u.full_name as driver_name
            FROM trips t
            JOIN buses b ON t.bus_id = b.bus_id
            JOIN routes r ON t.route_id = r.route_id
            LEFT JOIN stops cs ON t.current_stop_id = cs.stop_id
            LEFT JOIN stops ns ON t.next_stop_id = ns.stop_id
            LEFT JOIN users u ON t.driver_id = u.user_id
            WHERE t.trip_status IN ('scheduled', 'in_progress')
            AND t.trip_date = CURDATE()
            ORDER BY t.scheduled_start_time
        """)
        trips = cursor.fetchall()
        cursor.close()
        return trips
    
    @staticmethod
    def get_by_driver(driver_id):
        cursor = g.db.cursor()
        cursor.execute("""
            SELECT t.*, b.bus_number, r.route_name
            FROM trips t
            JOIN buses b ON t.bus_id = b.bus_id
            JOIN routes r ON t.route_id = r.route_id
            WHERE t.driver_id = %s AND t.trip_date = CURDATE()
            ORDER BY t.scheduled_start_time
        """, (driver_id,))
        trips = cursor.fetchall()
        cursor.close()
        return trips
    
    @staticmethod
    def start_trip(trip_id):
        cursor = g.db.cursor()
        cursor.execute("""
            UPDATE trips 
            SET trip_status = 'in_progress', actual_start_time = NOW() 
            WHERE trip_id = %s
        """, (trip_id,))
        g.db.commit()
        cursor.close()
    
    @staticmethod
    def complete_trip(trip_id):
        cursor = g.db.cursor()
        cursor.execute("""
            UPDATE trips 
            SET trip_status = 'completed', actual_end_time = NOW() 
            WHERE trip_id = %s
        """, (trip_id,))
        g.db.commit()
        cursor.close()
    
    @staticmethod
    def update_current_stop(trip_id, stop_id):
        cursor = g.db.cursor()
        cursor.execute("""
            UPDATE trips 
            SET current_stop_id = %s 
            WHERE trip_id = %s
        """, (stop_id, trip_id))
        g.db.commit()
        cursor.close()

class LiveLocation:
    @staticmethod
    def update_location(trip_id, latitude, longitude, speed=0, heading=0):
        cursor = g.db.cursor()
        cursor.execute("""
            INSERT INTO live_locations (trip_id, latitude, longitude, speed, heading)
            VALUES (%s, %s, %s, %s, %s)
        """, (trip_id, latitude, longitude, speed, heading))
        g.db.commit()
        cursor.close()
    
    @staticmethod
    def get_latest_for_trip(trip_id):
        cursor = g.db.cursor()
        cursor.execute("""
            SELECT * FROM live_locations 
            WHERE trip_id = %s 
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (trip_id,))
        location = cursor.fetchone()
        cursor.close()
        return location
    
    @staticmethod
    def get_recent_locations(trip_id, limit=10):
        cursor = g.db.cursor()
        cursor.execute("""
            SELECT * FROM live_locations 
            WHERE trip_id = %s 
            ORDER BY timestamp DESC 
            LIMIT %s
        """, (trip_id, limit))
        locations = cursor.fetchall()
        cursor.close()
        return locations

class StopNotification:
    @staticmethod
    def create(trip_id, stop_id, notification_type, departure_countdown=None):
        cursor = g.db.cursor()
        cursor.execute("""
            INSERT INTO stop_notifications (trip_id, stop_id, notification_type, departure_countdown)
            VALUES (%s, %s, %s, %s)
        """, (trip_id, stop_id, notification_type, departure_countdown))
        g.db.commit()
        notification_id = cursor.lastrowid
        cursor.close()
        return notification_id
    
    @staticmethod
    def mark_sent(notification_id):
        cursor = g.db.cursor()
        cursor.execute("UPDATE stop_notifications SET notification_sent = TRUE WHERE notification_id = %s", (notification_id,))
        g.db.commit()
        cursor.close()