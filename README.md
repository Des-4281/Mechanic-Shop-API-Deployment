# Mechanic Shop API

A REST API for a mechanic shop, built with Flask, SQLAlchemy, Marshmallow and MySQL. It manages customers, mechanics, service tickets and a parts inventory. Customers and mechanics log in with JSON Web Tokens, tickets can have several mechanics and parts (with quantities), and the API uses rate limiting and caching.

Every route is documented with **Swagger** (interactive docs at `/api/docs`) and covered by an automated **unittest** suite of 61 tests.

## Tech Stack

- Python 3.9
- Flask 3.1
- Flask-SQLAlchemy 3.1 / SQLAlchemy 2.0
- Flask-Marshmallow / marshmallow-sqlalchemy
- Flask-Limiter (rate limiting)
- Flask-Caching (response caching)
- python-jose (JSON Web Tokens)
- flask-swagger-ui (interactive API docs)
- unittest (Python's built-in test framework)
- MySQL (via `mysql-connector-python`)

## Project Structure

```
Mechanic Shop API/
├── app.py                      # Entry point: creates the app, creates tables, runs the server
├── config.py                   # DevelopmentConfig, TestingConfig, ProductionConfig
├── requirements.txt            # Python packages the app needs
├── app/
│   ├── __init__.py             # create_app() factory, inits extensions, registers blueprints and Swagger UI
│   ├── extensions.py           # Marshmallow, Limiter and Cache instances
│   ├── models.py               # Customer, Mechanic, ServiceTicket, Inventory, ServiceInventory
│   ├── static/
│   │   └── swagger.yaml        # Swagger 2.0 spec for all 24 routes
│   ├── utils/
│   │   └── util.py             # encode_token, encode_mechanic_token, token decorators
│   └── blueprints/
│       ├── customers/          # /customers routes and schemas
│       ├── mechanics/          # /mechanics routes and schemas
│       ├── service_tickets/    # /service-tickets routes and schemas
│       └── inventory/          # /inventory routes and schemas
└── tests/
    ├── test_customers.py       # 18 tests
    ├── test_mechanics.py       # 13 tests
    ├── test_inventory.py       # 14 tests
    └── test_service_tickets.py # 16 tests
```

## Setup

1. **Create and activate a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create the MySQL database**
   ```sql
   CREATE DATABASE mechanic_shop_db;
   ```

4. **Set your environment variables.** Copy `.env.example` to `.env`, fill in your MySQL username and password, and pick a secret key for signing tokens:
   ```
   DATABASE_URL='mysql+mysqlconnector://<user>:<password>@localhost/mechanic_shop_db'
   SECRET_KEY='<your-secret-key>'
   ```
   `.env` is listed in `.gitignore`, so your credentials stay out of the repo.

5. **Run the app**
   ```bash
   python app.py
   ```
   The server starts at `http://127.0.0.1:5000`, and the tables are created automatically on first run.

   > **macOS note:** AirPlay Receiver also listens on port 5000. Use `127.0.0.1` rather than `localhost`, or turn AirPlay Receiver off in System Settings → General → AirDrop & Handoff.

## API Documentation (Swagger)

With the server running, open **http://127.0.0.1:5000/api/docs**.

The page is generated from `app/static/swagger.yaml` and documents all 24 routes in four sections: Customers, Mechanics, Inventory and Service Tickets. For each route it shows:

- what to send, with an example body
- every response it can return (success and error codes), with examples
- the shape of the data, under **Models** at the bottom of the page

**Trying routes from the page:** open a route, click **Try it out**, then **Execute** to send a real request. Protected routes show a lock icon. To use them, log in with `POST /customers/login` or `POST /mechanics/login`, click **Authorize** at the top, and paste `Bearer <auth_token>`. The token is kept if you refresh the page.

The docs page is exempt from rate limiting, so refreshing it doesn't use up the API's request limits.

## Running the Tests

The tests use Python's built-in `unittest` and run against an in-memory SQLite database (`TestingConfig`), so they never touch your MySQL data and don't need the server running. Rate limiting is turned off for tests.

From the project folder, with the virtual environment active:
```bash
python -m unittest discover tests -v
```

There are **61 tests** in four files, one per blueprint, with at least one test for every route. Before each test, `setUp` builds a fresh app and an empty database with only the data that test needs, so tests don't depend on each other.

Besides the success cases, the tests cover the ways each route should fail:

- missing or invalid fields → **400**
- duplicate email → **400**
- wrong password → **401**
- no token or an invalid token → **401**
- a customer token on a mechanics-only route → **403**
- an ID that doesn't exist → **404**

## Data Model

- **Customer**: `id`, `name`, `email` (unique), `phone`, `password`
- **Mechanic**: `id`, `name`, `email` (unique), `phone`, `salary`, `password`
- **ServiceTicket**: `id`, `VIN` (max 17 chars), `service_date`, `service_desc`, `customer_id`
- **Inventory**: `id`, `name`, `price`
- **service_mechanics**: a join table linking service tickets and mechanics (many-to-many)
- **ServiceInventory**: an association model linking service tickets and parts, with a `quantity`

A customer can have many service tickets. A ticket can have many mechanics, and a mechanic can work on many tickets. A ticket can also use many parts, and `ServiceInventory` stores how many of each part it uses. Passwords are accepted when creating or updating an account but are never returned in responses.

## Authentication

Both customers and mechanics log in with their email and password and get back an `auth_token` that expires after 1 hour. Send it in the `Authorization` header:

```
Authorization: Bearer <auth_token>
```

| Token | Required for |
|---|---|
| Customer token | `GET /customers/my-tickets`, `PUT /customers`, `DELETE /customers` |
| Mechanic token | `PUT /mechanics`, `DELETE /mechanics`, `POST /inventory`, `PUT /inventory/<id>`, `DELETE /inventory/<id>` |

Protected routes read the user's ID from the token, so they have no ID in the URL and you can only change your own account. A missing, expired or invalid token returns **401**. A customer token on a mechanics-only route returns **403**.

## Rate Limiting and Caching

- Every API route has a default limit of 200 requests per day and 50 per hour. The Swagger docs page is exempt.
- `POST /customers`, `POST /customers/login` and `POST /mechanics/login` are limited to 5 per minute to stop spam sign-ups and password guessing. Going over a limit returns **429**.
- `GET /mechanics` and `GET /customers` are cached for 60 seconds, so changes can take up to a minute to show up in those lists. `GET /customers` caches each page separately.

## API Endpoints

Base URL: `http://127.0.0.1:5000`

### Customers

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/customers` | – | Create a customer |
| POST | `/customers/login` | – | Log in and get a customer token |
| GET | `/customers` | – | Get all customers. Add `?page=1&per_page=5` to paginate |
| GET | `/customers/<id>` | – | Get one customer |
| GET | `/customers/my-tickets` | Customer | Get the logged-in customer's service tickets |
| PUT | `/customers` | Customer | Update the logged-in customer |
| DELETE | `/customers` | Customer | Delete the logged-in customer and their tickets |

Create / update body:
```json
{
  "name": "Jane Doe",
  "email": "jane@gmail.com",
  "phone": "321-555-0000",
  "password": "test123"
}
```

Login body:
```json
{
  "email": "jane@gmail.com",
  "password": "test123"
}
```

### Mechanics

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/mechanics` | – | Create a mechanic |
| POST | `/mechanics/login` | – | Log in and get a mechanic token |
| GET | `/mechanics` | – | Get all mechanics |
| GET | `/mechanics/most-tickets` | – | Get mechanics ranked by how many tickets they've worked |
| PUT | `/mechanics` | Mechanic | Update the logged-in mechanic |
| DELETE | `/mechanics` | Mechanic | Delete the logged-in mechanic |

Create / update body:
```json
{
  "name": "Bob Smith",
  "email": "Bob@mechanicshop.com",
  "phone": "321-555-0000",
  "salary": 55000,
  "password": "mech123"
}
```

### Service Tickets

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/service-tickets` | – | Create a service ticket |
| GET | `/service-tickets` | – | Get all service tickets, with their mechanics and parts |
| PUT | `/service-tickets/<ticket_id>/assign-mechanic/<mechanic_id>` | – | Assign a mechanic to a ticket |
| PUT | `/service-tickets/<ticket_id>/remove-mechanic/<mechanic_id>` | – | Remove a mechanic from a ticket |
| PUT | `/service-tickets/<ticket_id>/edit` | – | Add and remove several mechanics in one request |
| PUT | `/service-tickets/<ticket_id>/add-part/<inventory_id>` | – | Add a part to a ticket, with an optional quantity (default 1) |

Create body (`customer_id` must belong to an existing customer):
```json
{
  "VIN": "1HGCM82633A004352",
  "service_date": "2026-10-14",
  "service_desc": "Oil change and tire rotation",
  "customer_id": 1
}
```

Edit body:
```json
{
  "add_ids": [1, 2],
  "remove_ids": [3]
}
```

Add part body (optional):
```json
{
  "quantity": 2
}
```

Tickets show their parts under `part_links`:
```json
"part_links": [
  { "quantity": 2, "part": { "id": 1, "name": "Oil Filter", "price": 12.99 } }
]
```

### Inventory

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/inventory` | Mechanic | Create a part |
| GET | `/inventory` | – | Get all parts |
| GET | `/inventory/<id>` | – | Get one part |
| PUT | `/inventory/<id>` | Mechanic | Update a part |
| DELETE | `/inventory/<id>` | Mechanic | Delete a part |

Create / update body:
```json
{
  "name": "Oil Filter",
  "price": 12.99
}
```

## Testing with Postman

Import `Mechanic Shop.postman_collection.json` into Postman. Its `base_url` variable is already set to `http://127.0.0.1:5000`. Both login requests save their token to a collection variable (`token` and `mechanic_token`), and the protected requests use those variables, so there's nothing to copy by hand.

Every request has a test that checks its status code, including two that are meant to fail: **Create Part - Customer Token** expects 403, and **My Tickets - No Token** expects 401.

To run everything, start from an empty database and click **Run** on the collection. The 27 requests run in this order:

1. **Customers**: create, log in, get all, get paginated, get one, update
2. **Mechanics**: create, log in, get all, update
3. **Inventory**: create with a customer token (403), create, get all, get one, update
4. **Service Tickets**: create, get all, assign mechanic, remove mechanic, edit ticket, add part, my tickets with no token (401), my tickets, mechanics by most tickets
5. **Cleanup**: delete part, delete customer, delete mechanic

The requests use ID `1` and create their own accounts, so reset to an **empty** database before running the collection again:
```sql
DROP DATABASE mechanic_shop_db;
CREATE DATABASE mechanic_shop_db;
```
Then restart `python app.py` to recreate the tables.

## License 
MIT
