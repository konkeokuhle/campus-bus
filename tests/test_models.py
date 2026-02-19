# tests/test_models.py
import unittest
from app import create_app, mysql
from models.user import User

class TestUserModel(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        
    def tearDown(self):
        self.app_context.pop()
    
    def test_user_creation(self):
        # Test user creation
        user_id = User.create(
            email='test@test.com',
            password='Test123!',
            full_name='Test User',
            phone_number='1234567890',
            user_type='student'
        )
        
        self.assertIsNotNone(user_id)
        
        # Test user retrieval
        user = User.get_by_id(user_id)
        self.assertIsNotNone(user)
        self.assertEqual(user['email'], 'test@test.com')
        
    def test_user_authentication(self):
        # Create user
        email = 'auth@test.com'
        password = 'Test123!'
        User.create(email, password, 'Auth User', '1234567890', 'student')
        
        # Test correct password
        user = User.authenticate(email, password)
        self.assertIsNotNone(user)
        
        # Test incorrect password
        user = User.authenticate(email, 'wrongpassword')
        self.assertIsNone(user)

if __name__ == '__main__':
    unittest.main()