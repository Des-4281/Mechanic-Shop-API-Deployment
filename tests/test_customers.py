import unittest
from app import create_app
from app.models import db, Customer, ServiceTicket
from app.utils.util import encode_token


class TestCustomers(unittest.TestCase):

    def setUp(self):
        # Runs before EVERY test: fresh app, empty database, one known customer
        self.app = create_app('TestingConfig')
        self.customer = Customer(name="Test User", email="test@email.com", phone="555-555-5555", password="test123")
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            db.session.add(self.customer)
            db.session.commit()
            self.customer_id = self.customer.id
        self.client = self.app.test_client()

    # ---------- helpers ----------

    def auth_header(self, customer_id=None):
        """Bearer header with a customer token (defaults to the setUp customer)."""
        with self.app.app_context():
            token = encode_token(customer_id or self.customer_id)
        return {'Authorization': 'Bearer ' + token}

    # ---------- POST /customers ----------

    def test_create_customer(self):
        payload = {"name": "John Doe", "email": "jd@email.com", "phone": "123-456-7890", "password": "abc123"}
        response = self.client.post('/customers', json=payload)
        self.assertEqual(response.status_code, 999)
        self.assertEqual(response.json['name'], "John Doe")
        self.assertNotIn('password', response.json)          # password must never come back

    def test_create_customer_missing_field(self):
        payload = {"name": "John Doe", "phone": "123-456-7890", "password": "abc123"}   # no email
        response = self.client.post('/customers', json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.json)

    def test_create_customer_duplicate_email(self):
        payload = {"name": "Copy Cat", "email": "test@email.com", "phone": "000", "password": "abc123"}
        response = self.client.post('/customers', json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['error'], "Email already associated with an account.")

    # ---------- GET /customers ----------

    def test_get_customers(self):
        response = self.client.get('/customers')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 1)
        self.assertEqual(response.json[0]['email'], "test@email.com")

    def test_get_customers_paginated(self):
        response = self.client.get('/customers?page=1&per_page=5')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 1)

    # ---------- GET /customers/<id> ----------

    def test_get_customer(self):
        response = self.client.get(f'/customers/{self.customer_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['name'], "Test User")

    def test_get_customer_not_found(self):
        response = self.client.get('/customers/999')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json['error'], "Customer not found.")

    # ---------- POST /customers/login ----------

    def test_login_customer(self):
        credentials = {"email": "test@email.com", "password": "test123"}
        response = self.client.post('/customers/login', json=credentials)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'success')
        self.assertIn('auth_token', response.json)

    def test_login_wrong_password(self):
        credentials = {"email": "test@email.com", "password": "wrong"}
        response = self.client.post('/customers/login', json=credentials)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json['message'], 'Invalid email or password.')

    def test_login_missing_password(self):
        response = self.client.post('/customers/login', json={"email": "test@email.com"})
        self.assertEqual(response.status_code, 400)

    # ---------- PUT /customers (protected) ----------

    def test_update_customer(self):
        payload = {"name": "Updated User", "email": "test@email.com", "phone": "111-111-1111", "password": "test123"}
        response = self.client.put('/customers', json=payload, headers=self.auth_header())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['name'], "Updated User")
        self.assertEqual(response.json['phone'], "111-111-1111")

    def test_update_customer_no_token(self):
        payload = {"name": "Updated User", "email": "test@email.com", "password": "test123"}
        response = self.client.put('/customers', json=payload)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json['message'], 'Token is missing!')

    def test_update_customer_invalid_token(self):
        payload = {"name": "Updated User", "email": "test@email.com", "password": "test123"}
        response = self.client.put('/customers', json=payload, headers={'Authorization': 'Bearer not-a-real-token'})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json['message'], 'Invalid token!')

    # ---------- DELETE /customers (protected) ----------

    def test_delete_customer(self):
        response = self.client.delete('/customers', headers=self.auth_header())
        self.assertEqual(response.status_code, 200)
        # really gone?
        self.assertEqual(self.client.get(f'/customers/{self.customer_id}').status_code, 404)

    def test_delete_customer_no_token(self):
        response = self.client.delete('/customers')
        self.assertEqual(response.status_code, 401)

    def test_delete_customer_not_found(self):
        # valid token for a customer ID that doesn't exist
        response = self.client.delete('/customers', headers=self.auth_header(customer_id=999))
        self.assertEqual(response.status_code, 404)

    # ---------- GET /customers/my-tickets (protected) ----------

    def test_my_tickets(self):
        with self.app.app_context():
            db.session.add(ServiceTicket(VIN="1HGCM82633A004352", service_date="2026-10-14",
                                         service_desc="Oil change", customer_id=self.customer_id))
            db.session.commit()
        response = self.client.get('/customers/my-tickets', headers=self.auth_header())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 1)
        self.assertEqual(response.json[0]['service_desc'], "Oil change")

    def test_my_tickets_no_token(self):
        response = self.client.get('/customers/my-tickets')
        self.assertEqual(response.status_code, 401)


if __name__ == '__main__':
    unittest.main()