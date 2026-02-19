# models/lost_item.py
from app import mysql
import MySQLdb.cursors

class LostItem:
    @staticmethod
    def create(reported_by, item_name, description, category, lost_date, 
               bus_id=None, trip_id=None, contact_info=None, image_url=None):
        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO lost_items 
            (reported_by, item_name, item_description, item_category, 
             lost_date, bus_id, trip_id, contact_info, image_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (reported_by, item_name, description, category, lost_date, 
              bus_id, trip_id, contact_info, image_url))
        mysql.connection.commit()
        item_id = cursor.lastrowid
        cursor.close()
        return item_id
    
    @staticmethod
    def search(query=None, category=None, status=None):
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        sql = """
            SELECT l.*, u.full_name as reporter_name
            FROM lost_items l
            JOIN users u ON l.reported_by = u.user_id
            WHERE 1=1
        """
        params = []
        
        if query:
            sql += " AND (l.item_name LIKE %s OR l.item_description LIKE %s)"
            params.extend([f'%{query}%', f'%{query}%'])
        
        if category:
            sql += " AND l.item_category = %s"
            params.append(category)
        
        if status:
            sql += " AND l.status = %s"
            params.append(status)
        
        sql += " ORDER BY l.created_at DESC"
        
        cursor.execute(sql, params)
        items = cursor.fetchall()
        cursor.close()
        return items
    
    @staticmethod
    def mark_found(item_id, found_by):
        cursor = mysql.connection.cursor()
        cursor.execute("""
            UPDATE lost_items 
            SET status = 'found', found_by = %s, found_date = CURDATE()
            WHERE item_id = %s
        """, (found_by, item_id))
        mysql.connection.commit()
        cursor.close()