import unittest
from app import create_app
from app.models import db, Customer, Mechanic, Inventory, ServiceTicket


class TestServiceTickets(unittest.TestCase):

    def setUp(self):
        # Runs before EVERY test: fresh app, empty database, plus everything a ticket needs:
        # one customer, two mechanics, one part, and one existing ticket
        self.app = create_app('TestingConfig')
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            customer = Customer(name="Test User", email="test@email.com", phone="555-555-5555", password="test123")
            mech1 = Mechanic(name="Mechanic One", email="one@shop.com", phone="555-000-0001", salary=50000.0, password="x")
            mech2 = Mechanic(name="Mechanic Two", email="two@shop.com", phone="555-000-0002", salary=50000.0, password="x")
            part = Inventory(name="Oil Filter", price=12.99)
            db.session.add_all([customer, mech1, mech2, part])
            db.session.commit()
            ticket = ServiceTicket(VIN="1HGCM82633A004352", service_date="2026-10-14",
                                   service_desc="Oil change", customer_id=customer.id)
            db.session.add(ticket)
            db.session.commit()
            self.customer_id = customer.id
            self.mech1_id = mech1.id
            self.mech2_id = mech2.id
            self.part_id = part.id
            self.ticket_id = ticket.id
        self.client = self.app.test_client()

    # ---------- helpers ----------

    def assign(self, mechanic_id):
        """Assign a mechanic to the setUp ticket (used to prepare remove/edit tests)."""
        return self.client.put(f'/service-tickets/{self.ticket_id}/assign-mechanic/{mechanic_id}')

    def mechanic_ids(self, response):
        """The list of mechanic IDs on a ticket response."""
        return [m['id'] for m in response.json['mechanics']]

    # ---------- POST /service-tickets ----------

    def test_create_ticket(self):
        payload = {"VIN": "2T1BURHE0JC123456", "service_date": "2026-11-01",
                   "service_desc": "Brake check", "customer_id": self.customer_id}
        response = self.client.post('/service-tickets', json=payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['service_desc'], "Brake check")
        self.assertEqual(response.json['mechanics'], [])
        self.assertEqual(response.json['part_links'], [])

    def test_create_ticket_missing_field(self):
        payload = {"service_date": "2026-11-01", "service_desc": "Brake check",
                   "customer_id": self.customer_id}   # no VIN
        response = self.client.post('/service-tickets', json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn('VIN', response.json)

    def test_create_ticket_customer_not_found(self):
        payload = {"VIN": "2T1BURHE0JC123456", "service_date": "2026-11-01",
                   "service_desc": "Brake check", "customer_id": 999}
        response = self.client.post('/service-tickets', json=payload)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json['error'], "Customer not found.")

    # ---------- GET /service-tickets ----------

    def test_get_tickets(self):
        response = self.client.get('/service-tickets')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 1)
        self.assertEqual(response.json[0]['VIN'], "1HGCM82633A004352")

    # ---------- PUT /service-tickets/<id>/assign-mechanic/<id> ----------

    def test_assign_mechanic(self):
        response = self.assign(self.mech1_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mechanic_ids(response), [self.mech1_id])

    def test_assign_mechanic_twice(self):
        self.assign(self.mech1_id)
        response = self.assign(self.mech1_id)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['error'], "Mechanic is already assigned to this ticket.")

    def test_assign_mechanic_not_found(self):
        response = self.assign(999)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json['error'], "Mechanic not found.")

    def test_assign_ticket_not_found(self):
        response = self.client.put(f'/service-tickets/999/assign-mechanic/{self.mech1_id}')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json['error'], "Service ticket not found.")

    # ---------- PUT /service-tickets/<id>/remove-mechanic/<id> ----------

    def test_remove_mechanic(self):
        self.assign(self.mech1_id)
        response = self.client.put(f'/service-tickets/{self.ticket_id}/remove-mechanic/{self.mech1_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mechanic_ids(response), [])

    def test_remove_mechanic_not_assigned(self):
        response = self.client.put(f'/service-tickets/{self.ticket_id}/remove-mechanic/{self.mech1_id}')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['error'], "Mechanic is not assigned to this ticket.")

    # ---------- PUT /service-tickets/<id>/edit ----------

    def test_edit_ticket(self):
        self.assign(self.mech1_id)
        payload = {"add_ids": [self.mech2_id], "remove_ids": [self.mech1_id]}
        response = self.client.put(f'/service-tickets/{self.ticket_id}/edit', json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mechanic_ids(response), [self.mech2_id])

    def test_edit_ticket_missing_field(self):
        response = self.client.put(f'/service-tickets/{self.ticket_id}/edit', json={"add_ids": [self.mech2_id]})
        self.assertEqual(response.status_code, 400)
        self.assertIn('remove_ids', response.json)

    def test_edit_ticket_not_found(self):
        payload = {"add_ids": [], "remove_ids": []}
        response = self.client.put('/service-tickets/999/edit', json=payload)
        self.assertEqual(response.status_code, 404)

    # ---------- PUT /service-tickets/<id>/add-part/<id> ----------

    def test_add_part(self):
        response = self.client.put(f'/service-tickets/{self.ticket_id}/add-part/{self.part_id}', json={"quantity": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json['part_links']), 1)
        self.assertEqual(response.json['part_links'][0]['quantity'], 2)
        self.assertEqual(response.json['part_links'][0]['part']['name'], "Oil Filter")

    def test_add_part_default_quantity(self):
        response = self.client.put(f'/service-tickets/{self.ticket_id}/add-part/{self.part_id}')   # no body
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['part_links'][0]['quantity'], 1)

    def test_add_part_not_found(self):
        response = self.client.put(f'/service-tickets/{self.ticket_id}/add-part/999', json={"quantity": 1})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json['error'], "Inventory part not found.")


if __name__ == '__main__':
    unittest.main()
