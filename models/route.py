# models/route.py
from app import mysql
import MySQLdb.cursors

class Route:
    @staticmethod
    def get_all_active():
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM routes WHERE is_active = TRUE")
        routes = cursor.fetchall()
        cursor.close()
        return routes
    
    @staticmethod
    def get_by_id(route_id):
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM routes WHERE route_id = %s", (route_id,))
        route = cursor.fetchone()
        cursor.close()
        return route
    
    @staticmethod
    def get_stops(route_id):
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT s.*, rs.stop_order, rs.estimated_time_from_prev, rs.distance_from_prev
            FROM stops s
            JOIN route_stops rs ON s.stop_id = rs.stop_id
            WHERE rs.route_id = %s AND rs.is_active = TRUE
            ORDER BY rs.stop_order
        """, (route_id,))
        stops = cursor.fetchall()
        cursor.close()
        return stops

class Stop:
    @staticmethod
    def get_all():
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM stops WHERE is_active = TRUE")
        stops = cursor.fetchall()
        cursor.close()
        return stops
    
    @staticmethod
    def get_by_id(stop_id):
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM stops WHERE stop_id = %s", (stop_id,))
        stop = cursor.fetchone()
        cursor.close()
        return stop
class RouteStop:
    @staticmethod
    def add_stop_to_route(route_id, stop_id, stop_order, estimated_time_from_prev, distance_from_prev):
        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO route_stops (route_id, stop_id, stop_order, estimated_time_from_prev, distance_from_prev)
            VALUES (%s, %s, %s, %s, %s)
        """, (route_id, stop_id, stop_order, estimated_time_from_prev, distance_from_prev))
        mysql.connection.commit()
        route_stop_id = cursor.lastrowid
        cursor.close()
        return route_stop_id
    
    @staticmethod
    def get_stops_for_route(route_id):
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT rs.*, s.stop_name, s.latitude, s.longitude
            FROM route_stops rs
            JOIN stops s ON rs.stop_id = s.stop_id
            WHERE rs.route_id = %s
            ORDER BY rs.stop_order
        """, (route_id,))
        stops = cursor.fetchall()
        cursor.close()
        return stops
    
    @staticmethod
    def remove_stop_from_route(route_id, stop_id):
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM route_stops WHERE route_id = %s AND stop_id = %s", (route_id, stop_id))
        mysql.connection.commit()
        cursor.close()
    
    @staticmethod
    def update_stop_order(route_id, stop_id, new_order):
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE route_stops SET stop_order = %s WHERE route_id = %s AND stop_id = %s", 
                      (new_order, route_id, stop_id))
        mysql.connection.commit()
        cursor.close()