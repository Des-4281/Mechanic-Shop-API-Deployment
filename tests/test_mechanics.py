import unittest
from app import create_app
from app.models import db, Mechanic, Customer, ServiceTicket
from app.utils.util import encode_mechanic_token, encode_token


class TestMechanics(unittest.TestCase):

    def setUp(self):
        # Runs before EVERY test: fresh app, empty database, one known mechanic
        self.app = create_app('TestingConfig')
        self.mechanic = Mechanic(name="Test Mechanic", email="mech@shop.com", phone="555-000-0000",
                                 salary=50000.0, password="mech123")
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            db.session.add(self.mechanic)
            db.session.commit()
            self.mechanic_id = self.mechanic.id
        self.client = self.app.test_client()

    # ---------- helpers ----------

    def mechanic_header(self, mechanic_id=None):
        """Bearer header with a MECHANIC token (defaults to the setUp mechanic)."""
        with self.app.app_context():
            token = encode_mechanic_token(mechanic_id or self.mechanic_id)
        return {'Authorization': 'Bearer ' + token}

    def customer_header(self):
        """Bearer header with a CUSTOMER token -- should be rejected on mechanic routes."""
        with self.app.app_context():
            token = encode_token(1)
        return {'Authorization': 'Bearer ' + token}

    # ---------- POST /mechanics ----------

    def test_create_mechanic(self):
        payload = {"name": "New Mechanic", "email": "new@shop.com", "phone": "555-111-1111",
                   "salary": 60000.0, "password": "abc123"}
        response = self.client.post('/mechanics', json=payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['name'], "New Mechanic")
        self.assertEqual(response.json['salary'], 60000.0)
        self.assertNotIn('password', response.json)

    def test_create_mechanic_missing_field(self):
        payload = {"name": "New Mechanic", "salary": 60000.0, "password": "abc123"}   # no email
        response = self.client.post('/mechanics', json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.json)

    def test_create_mechanic_duplicate_email(self):
        payload = {"name": "Copy Cat", "email": "mech@shop.com", "phone": "000", "salary": 1.0, "password": "abc123"}
        response = self.client.post('/mechanics', json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['error'], "Email already associated with a mechanic.")

    # ---------- GET /mechanics ----------

    def test_get_mechanics(self):
        response = self.client.get('/mechanics')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 1)
        self.assertEqual(response.json[0]['email'], "mech@shop.com")

    # ---------- POST /mechanics/login ----------

    def test_login_mechanic(self):
        response = self.client.post('/mechanics/login', json={"email": "mech@shop.com", "password": "mech123"})
        self.assertEqual(response.status_code, 200)
        self.assertIn('auth_token', response.json)

    def test_login_mechanic_wrong_password(self):
        response = self.client.post('/mechanics/login', json={"email": "mech@shop.com", "password": "wrong"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json['message'], 'Invalid email or password.')

    # ---------- PUT /mechanics (mechanic token) ----------

    def test_update_mechanic(self):
        payload = {"name": "Updated Mechanic", "email": "mech@shop.com", "phone": "555-000-0000",
                   "salary": 65000.0, "password": "mech123"}
        response = self.client.put('/mechanics', json=payload, headers=self.mechanic_header())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['name'], "Updated Mechanic")
        self.assertEqual(response.json['salary'], 65000.0)

    def test_update_mechanic_no_token(self):
        payload = {"name": "Updated Mechanic", "email": "mech@shop.com", "password": "mech123"}
        response = self.client.put('/mechanics', json=payload)
        self.assertEqual(response.status_code, 401)

    def test_update_mechanic_customer_token(self):
        payload = {"name": "Updated Mechanic", "email": "mech@shop.com", "password": "mech123"}
        response = self.client.put('/mechanics', json=payload, headers=self.customer_header())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json['message'], 'Mechanics Only!')

    # ---------- DELETE /mechanics (mechanic token) ----------

    def test_delete_mechanic(self):
        response = self.client.delete('/mechanics', headers=self.mechanic_header())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/mechanics').json, [])

    def test_delete_mechanic_customer_token(self):
        response = self.client.delete('/mechanics', headers=self.customer_header())
        self.assertEqual(response.status_code, 403)

    def test_delete_mechanic_not_found(self):
        response = self.client.delete('/mechanics', headers=self.mechanic_header(mechanic_id=999))
        self.assertEqual(response.status_code, 404)

    # ---------- GET /mechanics/most-tickets ----------

    def test_most_tickets(self):
        # second mechanic with 2 tickets; setUp mechanic with 0 -> busy one must come first
        with self.app.app_context():
            busy = Mechanic(name="Busy Mechanic", email="busy@shop.com", phone="000", salary=1.0, password="x")
            customer = Customer(name="C", email="c@email.com", phone="000", password="x")
            db.session.add_all([busy, customer])
            db.session.commit()
            for _ in range(2):
                ticket = ServiceTicket(VIN="1HGCM82633A004352", service_date="2026-10-14",
                                       service_desc="Oil change", customer_id=customer.id)
                ticket.mechanics.append(busy)
                db.session.add(ticket)
            db.session.commit()
        response = self.client.get('/mechanics/most-tickets')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 2)
        self.assertEqual(response.json[0]['name'], "Busy Mechanic")


if __name__ == '__main__':
    unittest.main()