# models/residence.py
# models/residence.py
from flask import g
import pymysql.cursors

class Residence:
    @staticmethod
    def get_all_active():
        """Get all active residences"""
        cursor = g.db.cursor()
        cursor.execute("SELECT * FROM residences WHERE is_active = TRUE ORDER BY residence_name")
        residences = cursor.fetchall()
        cursor.close()
        return residences
    
    @staticmethod
    def get_by_id(residence_id):
        """Get residence by ID"""
        cursor = g.db.cursor()
        cursor.execute("SELECT * FROM residences WHERE residence_id = %s", (residence_id,))
        residence = cursor.fetchone()
        cursor.close()
        return residence
    
    @staticmethod
    def get_by_name(residence_name):
        """Get residence by name"""
        cursor = g.db.cursor()
        cursor.execute("SELECT * FROM residences WHERE residence_name = %s", (residence_name,))
        residence = cursor.fetchone()
        cursor.close()
        return residence
    
    @staticmethod
    def get_buses_by_residence(residence_id):
        """Get all buses assigned to a residence"""
        cursor = g.db.cursor()
        cursor.execute("""
            SELECT b.*, u.full_name as driver_name 
            FROM buses b
            LEFT JOIN users u ON b.current_driver_id = u.user_id
            WHERE b.residence_id = %s AND b.bus_status = 'active'
        """, (residence_id,))
        buses = cursor.fetchall()
        cursor.close()
        return buses
    
    @staticmethod
    def validate_bus_number(bus_number, residence_id=None):
        """Validate if bus number belongs to a residence range"""
        cursor = g.db.cursor()
        
        # Extract numeric part from bus number
        import re
        numbers = re.findall(r'\d+', bus_number)
        if not numbers:
            return False, "Invalid bus number format"
        
        bus_num = int(numbers[0])
        
        if residence_id:
            # Check specific residence
            cursor.execute("""
                SELECT * FROM residences 
                WHERE residence_id = %s 
                AND bus_number_start <= %s 
                AND bus_number_end >= %s
            """, (residence_id, bus_num, bus_num))
        else:
            # Find which residence this bus belongs to
            cursor.execute("""
                SELECT residence_id, residence_name 
                FROM residences 
                WHERE bus_number_start <= %s 
                AND bus_number_end >= %s
            """, (bus_num, bus_num))
        
        result = cursor.fetchone()
        cursor.close()
        
        if result:
            return True, result
        else:
            return False, f"Bus number {bus_number} is not assigned to any residence"
    
    @staticmethod
    def get_residence_by_bus_number(bus_number):
        """Get residence that owns a specific bus number"""
        success, result = Residence.validate_bus_number(bus_number)
        if success:
            return result
        return None