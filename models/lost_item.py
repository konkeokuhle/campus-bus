# models/lost_item.py
from flask import g

class LostItem:
    @staticmethod
    def create(reported_by, item_name, description, category, lost_date, 
               bus_id=None, trip_id=None, contact_info=None, image_url=None):
        cursor = g.db.cursor()
        cursor.execute("""
            INSERT INTO lost_items 
            (reported_by, item_name, item_description, item_category, 
             lost_date, bus_id, trip_id, contact_info, image_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (reported_by, item_name, description, category, lost_date, 
              bus_id, trip_id, contact_info, image_url))
        g.db.commit()
        item_id = cursor.lastrowid
        cursor.close()
        return item_id
    
    @staticmethod
    def search(query=None, category=None, status=None, reported_by=None):
        cursor = g.db.cursor()
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
        
        if reported_by:
            sql += " AND l.reported_by = %s"
            params.append(reported_by)
        
        sql += " ORDER BY l.created_at DESC"
        
        cursor.execute(sql, params)
        items = cursor.fetchall()
        cursor.close()
        return items
    
    @staticmethod
    def mark_found(item_id, found_by):
        cursor = g.db.cursor()
        cursor.execute("""
            UPDATE lost_items 
            SET status = 'found', found_by = %s, found_date = CURDATE()
            WHERE item_id = %s
        """, (found_by, item_id))
        g.db.commit()
        cursor.close()
    
    @staticmethod
    def claim_item(item_id, claimed_by):
        cursor = g.db.cursor()
        cursor.execute("""
            UPDATE lost_items 
            SET status = 'claimed', claimed_by = %s, claimed_date = CURDATE()
            WHERE item_id = %s
        """, (claimed_by, item_id))
        g.db.commit()
        cursor.close()
    
    @staticmethod
    def get_by_id(item_id):
        cursor = g.db.cursor()
        cursor.execute("""
            SELECT l.*, u.full_name as reporter_name, 
                   u2.full_name as finder_name, u3.full_name as claimer_name
            FROM lost_items l
            LEFT JOIN users u ON l.reported_by = u.user_id
            LEFT JOIN users u2 ON l.found_by = u2.user_id
            LEFT JOIN users u3 ON l.claimed_by = u3.user_id
            WHERE l.item_id = %s
        """, (item_id,))
        item = cursor.fetchone()
        cursor.close()
        return item