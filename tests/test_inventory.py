import unittest
from app import create_app
from app.models import db, Inventory, Mechanic
from app.utils.util import encode_mechanic_token, encode_token


class TestInventory(unittest.TestCase):

    def setUp(self):
        # Runs before EVERY test: fresh app, empty database, one mechanic and one part
        self.app = create_app('TestingConfig')
        self.mechanic = Mechanic(name="Test Mechanic", email="mech@shop.com", phone="555-000-0000",
                                 salary=50000.0, password="mech123")
        self.part = Inventory(name="Oil Filter", price=12.99)
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            db.session.add_all([self.mechanic, self.part])
            db.session.commit()
            self.mechanic_id = self.mechanic.id
            self.part_id = self.part.id
        self.client = self.app.test_client()

    # ---------- helpers ----------

    def mechanic_header(self):
        """Bearer header with a MECHANIC token."""
        with self.app.app_context():
            token = encode_mechanic_token(self.mechanic_id)
        return {'Authorization': 'Bearer ' + token}

    def customer_header(self):
        """Bearer header with a CUSTOMER token -- should be rejected on inventory changes."""
        with self.app.app_context():
            token = encode_token(1)
        return {'Authorization': 'Bearer ' + token}

    # ---------- POST /inventory (mechanic token) ----------

    def test_create_part(self):
        payload = {"name": "Brake Pads", "price": 49.99}
        response = self.client.post('/inventory', json=payload, headers=self.mechanic_header())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['name'], "Brake Pads")
        self.assertEqual(response.json['price'], 49.99)

    def test_create_part_missing_price(self):
        response = self.client.post('/inventory', json={"name": "Brake Pads"}, headers=self.mechanic_header())
        self.assertEqual(response.status_code, 400)
        self.assertIn('price', response.json)

    def test_create_part_no_token(self):
        response = self.client.post('/inventory', json={"name": "Brake Pads", "price": 49.99})
        self.assertEqual(response.status_code, 401)

    def test_create_part_customer_token(self):
        payload = {"name": "Brake Pads", "price": 49.99}
        response = self.client.post('/inventory', json=payload, headers=self.customer_header())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json['message'], 'Mechanics Only!')

    # ---------- GET /inventory ----------

    def test_get_parts(self):
        response = self.client.get('/inventory')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 1)
        self.assertEqual(response.json[0]['name'], "Oil Filter")

    # ---------- GET /inventory/<id> ----------

    def test_get_part(self):
        response = self.client.get(f'/inventory/{self.part_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['price'], 12.99)

    def test_get_part_not_found(self):
        response = self.client.get('/inventory/999')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json['error'], "Part not found")

    # ---------- PUT /inventory/<id> (mechanic token) ----------

    def test_update_part(self):
        payload = {"name": "Oil Filter", "price": 14.99}
        response = self.client.put(f'/inventory/{self.part_id}', json=payload, headers=self.mechanic_header())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['price'], 14.99)

    def test_update_part_not_found(self):
        payload = {"name": "Oil Filter", "price": 14.99}
        response = self.client.put('/inventory/999', json=payload, headers=self.mechanic_header())
        self.assertEqual(response.status_code, 404)

    def test_update_part_invalid_price(self):
        payload = {"name": "Oil Filter", "price": "cheap"}
        response = self.client.put(f'/inventory/{self.part_id}', json=payload, headers=self.mechanic_header())
        self.assertEqual(response.status_code, 400)
        self.assertIn('price', response.json)

    def test_update_part_customer_token(self):
        payload = {"name": "Oil Filter", "price": 14.99}
        response = self.client.put(f'/inventory/{self.part_id}', json=payload, headers=self.customer_header())
        self.assertEqual(response.status_code, 403)

    # ---------- DELETE /inventory/<id> (mechanic token) ----------

    def test_delete_part(self):
        response = self.client.delete(f'/inventory/{self.part_id}', headers=self.mechanic_header())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['message'], f'Deleted - Part id: {self.part_id}')
        self.assertEqual(self.client.get(f'/inventory/{self.part_id}').status_code, 404)

    def test_delete_part_not_found(self):
        response = self.client.delete('/inventory/999', headers=self.mechanic_header())
        self.assertEqual(response.status_code, 404)

    def test_delete_part_no_token(self):
        response = self.client.delete(f'/inventory/{self.part_id}')
        self.assertEqual(response.status_code, 401)


if __name__ == '__main__':
    unittest.main()
