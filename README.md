<div align="center">

![Library Service](https://capsule-render.vercel.app/api?type=waving&color=0:7F00FF,50:E100FF,100:FF6B9D&height=230&section=header&text=Library%20Service&fontSize=64&fontColor=ffffff&animation=fadeIn&fontAlignY=38&desc=A%20modern%20API%20for%20library%20management&descAlignY=60&descSize=18)
<br>

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.1-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/Django_REST_Framework-3.18-A30000?style=for-the-badge&logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)

[![Celery](https://img.shields.io/badge/Celery-5.6-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Stripe](https://img.shields.io/badge/Stripe-Checkout-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://stripe.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

[![Tests and code quality](https://github.com/otakuc0der/py-library-service/actions/workflows/tests-and-code-quality.yml/badge.svg)](https://github.com/otakuc0der/py-library-service/actions/workflows/tests-and-code-quality.yml)
![Tests](https://img.shields.io/badge/tests-218%20passed-brightgreen?style=flat-square)
![Code style](https://img.shields.io/badge/code%20style-black-000000?style=flat-square)
![Lint](https://img.shields.io/badge/lint-flake8-4B8BBE?style=flat-square)

<p>
  A backend system that replaces manual library records with a documented API.<br>
  It manages books, customers, borrowings, online payments, overdue fines<br>
  and administrator notifications without requiring a separate front end.
</p>

</div>

---

<div align="center">

## Contents

| Project | API and logic | Running the project |
|:---:|:---:|:---:|
| [About](#about) | [API reference](#api-reference) | [Docker setup](#docker-setup) |
| [Features](#features) | [Authentication](#authentication) | [Local setup](#local-setup) |
| [Tech stack](#tech-stack) | [Payments](#payments-and-overdue-fines) | [Environment](#environment-variables) |
| [Architecture](#architecture) | [Notifications](#telegram-notifications) | [Testing](#testing-and-code-quality) |
| [Database](#database-model) | [Permissions](#permissions) | [Screenshots](#screenshots) |

</div>

---

## About

Library Service is a Django REST Framework project for managing the daily work
of a library. Customers can register, authenticate, browse books, create
borrowings, return books and pay through Stripe Checkout. Administrators can
manage the inventory and inspect all borrowing and payment records.

The application also detects overdue returns, creates fine payments and sends
useful messages to an administrator Telegram chat. Celery processes notification
tasks outside the web request, while Celery Beat starts the daily overdue check.

The project is API-only. Swagger UI acts as the browsable interface for testing
and documenting every endpoint.

> [!NOTE]
> Stripe is configured for test mode. No real card or production payment data is
> required to explore the project.


## Features

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>📚 Library management</h3>
      <ul>
        <li>Complete CRUD operations for books</li>
        <li>Inventory tracking during borrowing and return</li>
        <li>Book details with cover type and daily fee</li>
        <li>Database and application-level validation</li>
      </ul>
    </td>
    <td width="50%" valign="top">
      <h3>👤 Accounts and access</h3>
      <ul>
        <li>Email-based user accounts</li>
        <li>JWT access and refresh tokens</li>
        <li>Custom <code>Authorize</code> request header</li>
        <li>Separate customer and administrator permissions</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>📖 Borrowings</h3>
      <ul>
        <li>Create, list and retrieve borrowing records</li>
        <li>Filter by active status and user</li>
        <li>Transactional inventory updates</li>
        <li>Protection against returning a book twice</li>
      </ul>
    </td>
    <td width="50%" valign="top">
      <h3>💳 Payments and notifications</h3>
      <ul>
        <li>Stripe-hosted Checkout sessions</li>
        <li>Verified Stripe webhook events</li>
        <li>Automatic overdue fine calculation</li>
        <li>Telegram messages sent through Celery</li>
      </ul>
    </td>
  </tr>
</table>

## Tech stack

| Area | Technology | Purpose |
|---|---|---|
| API | Django, Django REST Framework | Models, business logic and REST endpoints |
| Authentication | Simple JWT | Access and refresh token authentication |
| Documentation | drf-spectacular | OpenAPI schema and Swagger UI |
| Database | PostgreSQL | Persistent application data |
| Filtering | django-filter | Borrowing query parameters |
| Payments | Stripe Checkout | Test payment sessions and confirmation |
| Background work | Celery, Celery Beat | Asynchronous and scheduled tasks |
| Message broker | Redis | Celery task delivery and results |
| Monitoring | Flower | Celery worker and task monitoring |
| Notifications | Telegram Bot API | Administrator notifications |
| Environment | python-decouple | Environment-based configuration |
| Packaging | uv | Dependency and virtual environment management |
| Infrastructure | Docker, Docker Compose | Reproducible multi-container startup |
| Quality | unittest, Coverage, Black, Flake8 | Tests, coverage, formatting and linting |
| Automation | GitHub Actions | Checks on pull requests and changes to `main` |

## Architecture

The repository is a modular Django application. Each domain has its own app,
while PostgreSQL, Redis and the external APIs are shared infrastructure.

```mermaid
flowchart TB
    Client["Swagger / API client"] --> API["Django REST API"]
    API --> DB[(PostgreSQL)]
    API --> Stripe["Stripe Checkout"]
    API --> Redis[(Redis)]
    Beat["Celery Beat"] --> Redis
    Redis --> Worker["Celery Worker"]
    Worker --> DB
    Worker --> Telegram["Telegram Bot API"]
    Flower["Flower"] --> Redis
```

<details>
<summary><strong>Project structure</strong></summary>

```text
py-library-service/
├── .github/workflows/       # CI checks
├── books/                   # Inventory and book CRUD
├── borrowings/              # Borrowing, filtering and return logic
├── notifications/           # Telegram formatting and Celery tasks
├── payments/                # Stripe sessions, payments and fines
├── users/                   # Custom user model and JWT endpoints
├── library_service/         # Django and Celery configuration
├── docs/                    # Diagram and screenshots
├── docker-compose.yaml
├── Dockerfile
├── manage.py
├── pyproject.toml
└── uv.lock
```

</details>

### Docker services

| Service | Role | Host address |
|---|---|---|
| `app` | Django API, migrations and static files | `http://localhost:8000` |
| `db` | PostgreSQL database | `localhost:25432` |
| `redis` | Celery broker and result backend | `localhost:6379` |
| `celery_worker` | Executes notification tasks | Internal service |
| `celery_beat` | Starts the daily overdue task | Internal service |
| `flower` | Celery monitoring dashboard | `http://localhost:5555` |

There is no separate long-running Telegram bot container. The bot does not
receive commands from customers. The Celery worker calls the Telegram Bot API
whenever the system needs to publish a notification.

## Database model

<div align="center">
  <img src="docs/database-diagram.png" alt="Library Service database diagram" width="900">
</div>

| Model | Main responsibility |
|---|---|
| `User` | Email-based account, profile data and staff permissions |
| `Book` | Book information, available inventory and daily rental fee |
| `Borrowing` | Borrowing dates and connections to a user and book |
| `Payment` | Regular payment or fine with Stripe Checkout information |

Relationships:

- One user can have many borrowings.
- One book can appear in many borrowings.
- One borrowing can have a regular payment and an additional fine payment.

## Main workflows

<details open>
<summary><strong>Creating and returning a borrowing</strong></summary>

1. An authenticated customer selects a book and an expected return date.
2. The API validates that the book is available and locks its database row.
3. A borrowing is created and the inventory is decreased by one.
4. A Stripe Checkout session is created for the rental price.
5. A Telegram notification is queued after the database transaction succeeds.
6. When the book is returned, the return date is stored and inventory increases.

</details>

<details>
<summary><strong>Overdue return and fine</strong></summary>

If the actual return date is later than the expected date, the system creates a
second payment with type `fine`:

```text
fine = overdue days × book daily fee × FINE_MULTIPLIER
```

The fine has its own Stripe Checkout session. Paying it triggers a separate
Telegram message with the overdue period and payment details.

</details>

<details>
<summary><strong>Daily overdue report</strong></summary>

Celery Beat schedules `check_overdue_borrowings` every day at 09:00 in the
configured Celery timezone. The task finds borrowings due today or earlier that
have not been returned. It sends one detailed Telegram message for each record.
If nothing is overdue, it sends a clear “No Borrowings Overdue Today” message.

</details>

## API reference

After starting the application:

- Swagger UI: [`http://localhost:8000/api/docs/`](http://localhost:8000/api/docs/)
- OpenAPI schema: [`http://localhost:8000/api/schema/`](http://localhost:8000/api/schema/)
- Django admin: [`http://localhost:8000/admin/`](http://localhost:8000/admin/)

### Books

| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/books/` | Public | List books |
| `POST` | `/api/books/` | Admin | Create a book |
| `GET` | `/api/books/{id}/` | Public | Retrieve a book |
| `PUT/PATCH` | `/api/books/{id}/` | Admin | Update book information or inventory |
| `DELETE` | `/api/books/{id}/` | Admin | Delete a book |

### Users and authentication

| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/users/` | Public | Register a customer |
| `POST` | `/api/users/token/` | Public | Obtain access and refresh tokens |
| `POST` | `/api/users/token/refresh/` | Public | Refresh an access token |
| `GET` | `/api/users/me/` | Authenticated | Retrieve the current account |
| `PUT/PATCH` | `/api/users/me/` | Authenticated | Update email or password |

### Borrowings

| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/borrowings/` | Authenticated | List accessible borrowings |
| `POST` | `/api/borrowings/` | Authenticated | Borrow one available book |
| `GET` | `/api/borrowings/{id}/` | Authenticated | Retrieve borrowing details and payments |
| `POST` | `/api/borrowings/{id}/return/` | Authenticated | Return a book and create a fine when overdue |

Available list filters:

| Parameter | Example | Behaviour |
|---|---|---|
| `is_active` | `?is_active=true` | Shows records without an actual return date |
| `is_active` | `?is_active=false` | Shows returned records |
| `user_id` | `?user_id=4` | Filters by customer; available to administrators |

### Payments

| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/payments/` | Authenticated | List accessible payments |
| `GET` | `/api/payments/{id}/` | Authenticated | Retrieve one payment |
| `POST` | `/api/payments/stripe/webhook/` | Stripe | Verify and process a Stripe event |
| `GET` | `/api/payments/checkout/success/?session_id=...` | Public | Read the stored payment status |
| `GET` | `/api/payments/checkout/cancel/` | Public | Explain that checkout was cancelled |

### Why payment confirmation is handled by a webhook

The original task suggested confirming the Stripe Session and marking the
Payment as paid inside the success endpoint. This project uses a slightly
different and more reliable flow.

Stripe explains:

> “Webhooks are required for fulfillment.”

Stripe also describes the purpose of the success page as:

> “Display a confirmation page with your customer's order information.”

— [Stripe: Customize redirect behavior](https://docs.stripe.com/payments/checkout/custom-success-page)

A customer can successfully pay and then close the browser or lose their
internet connection before the success endpoint is opened. Because of this,
the redirect cannot be treated as reliable proof of payment.

In this project:

1. Stripe sends a signed `checkout.session.completed` event to the webhook.
2. The webhook verifies the event signature and checks the payment details.
3. Only the webhook can change the stored Payment status to `paid`.
4. The success endpoint reads the current status from the database and displays
   a confirmation or explains that webhook processing is still pending.
5. The cancel endpoint leaves the Payment as `pending`, so the available
   Checkout Session can still be used later.

This keeps payment confirmation independent from the customer's browser and
prevents an unverified redirect from changing payment data.

## Authentication

The project uses JWT access and refresh tokens. Protected API requests use the
custom `Authorize` header instead of the default `Authorization` header.

```http
Authorize: Bearer <access-token>
```

In Swagger UI, open **Authorize**, enter the value in the same format and then
call protected endpoints.

## Permissions

| Action | Anonymous | Customer | Admin |
|---|:---:|:---:|:---:|
| List and retrieve books | ✅ | ✅ | ✅ |
| Create, update or delete books | ❌ | ❌ | ✅ |
| Create a borrowing | ❌ | ✅ | ✅ |
| View own borrowings and payments | ❌ | ✅ | ✅ |
| View all users' borrowings and payments | ❌ | ❌ | ✅ |
| Filter borrowings by `user_id` | ❌ | ❌ | ✅ |
| Return an accessible borrowing | ❌ | ✅ | ✅ |

## Payments and overdue fines

Stripe Checkout sessions are created automatically. A regular payment is
created together with a borrowing and uses this calculation:

```text
rental amount = rental days × daily fee
```

As explained above, payment confirmation is handled by the verified Stripe
webhook. The success endpoint only displays the Payment status currently stored
in the database.

> [!IMPORTANT]
> Stripe CLI is required only for forwarding webhook events during local
> development. It does not need to run permanently in Docker. In production,
> the webhook endpoint is registered directly in Stripe.

Start local forwarding in a separate terminal:

```powershell
stripe login
stripe listen --events checkout.session.completed --forward-to localhost:8000/api/payments/stripe/webhook/
```

Copy the displayed `whsec_...` value to `STRIPE_WEBHOOK_SECRET` in `.env`.

## Telegram notifications

The administrator chat receives notifications when:

- a new borrowing is created;
- a regular borrowing payment is completed;
- an overdue fine is paid;
- the scheduled overdue report runs;
- the daily report finds no overdue records.

Dynamic user and book values are escaped before they are added to Telegram HTML
messages.

## Docker setup

### 1. Prepare the environment

Clone the repository and open the project directory:

```bash
git clone https://github.com/otakuc0der/py-library-service.git
cd py-library-service
```

Create the `.env` file from `.env.sample`.

#### Windows PowerShell

```powershell
Copy-Item .env.sample .env
```

#### Linux and macOS

```bash
cp .env.sample .env
```

For Docker Compose, use service names rather than `localhost` inside `.env`:

```dotenv
POSTGRES_HOST=db
POSTGRES_PORT=5432
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

Also replace the placeholder secret, Telegram and Stripe values.

### 2. Build and start all services

```powershell
docker compose up --build
```

The application waits for PostgreSQL, applies migrations and collects static
files automatically. Start in detached mode with:

```powershell
docker compose up --build -d
```

### 3. Create an administrator

```powershell
docker compose exec app python manage.py createsuperuser
```

Useful commands:

```powershell
docker compose ps
docker compose logs -f app
docker compose logs -f celery_worker
docker compose down
```

## Local setup

### Requirements

Before starting, install:

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL
- Redis

### 1. Clone the repository

```bash
git clone https://github.com/otakuc0der/py-library-service.git
cd py-library-service
```

### 2. Install dependencies

```bash
uv sync --locked
```

### 3. Create the environment file

#### Windows PowerShell

```powershell
Copy-Item .env.sample .env
```

#### Linux and macOS

```bash
cp .env.sample .env
```

Fill in the required values inside `.env` before continuing.

### 4. Apply database migrations

```bash
uv run python manage.py migrate
```

### 5. Create an administrator

```bash
uv run python manage.py createsuperuser
```

### 6. Start the development server

```bash
uv run python manage.py runserver
```

The API will be available at:

```text
http://localhost:8000/
```

Swagger UI will be available at:

```text
http://localhost:8000/api/docs/
```

For direct local execution, database and Redis hosts normally use `localhost`:

```dotenv
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

Run background processes in separate terminals:

```powershell
uv run celery -A library_service worker -l INFO
uv run celery -A library_service beat -l INFO
uv run celery -A library_service flower --port=5555
```

> [!TIP]
> If PostgreSQL runs through this project's Docker Compose but Django runs on
> Windows, use `POSTGRES_HOST=localhost` and `POSTGRES_PORT=25432`.

## Environment variables

| Variable | Meaning | Docker example |
|---|---|---|
| `SECRET_KEY` | Django cryptographic secret | A long random value |
| `DEBUG` | Development mode | `False` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1` |
| `POSTGRES_DB` | PostgreSQL database | `library_db` |
| `POSTGRES_USER` | PostgreSQL user | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL password | A private value |
| `POSTGRES_HOST` | Database host | `db` |
| `POSTGRES_PORT` | Database container port | `5432` |
| `PGDATA` | PostgreSQL data directory | `/var/lib/postgresql/data` |
| `CELERY_BROKER_URL` | Redis broker URL | `redis://redis:6379/1` |
| `CELERY_RESULT_BACKEND` | Celery result backend | `redis://redis:6379/1` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Private value |
| `TELEGRAM_CHAT_ID` | Administrator chat ID | Numeric chat ID |
| `STRIPE_SECRET_KEY` | Stripe test secret key | `sk_test_...` |
| `STRIPE_WEBHOOK_SECRET` | Local or registered webhook secret | `whsec_...` |
| `FINE_MULTIPLIER` | Overdue fine multiplier | `2` |
| `FLOWER_BASIC_AUTH` | Flower credentials | `admin:password` |

Never commit the real `.env` file or any Stripe and Telegram secrets.

## Testing and code quality

The test suite covers models, serializers, permissions, filtering, borrowing
creation and return, Stripe services and webhooks, Telegram formatting and
Celery tasks. External services are mocked so the unit tests do not send real
Telegram messages or create real Stripe sessions.

```powershell
# Run all tests
uv run python manage.py test

# Reset and collect coverage
uv run coverage erase
uv run coverage run --source=. manage.py test
uv run coverage report -m

# Check formatting and linting
uv run black --check .
uv run flake8 .

# Validate Django configuration and migrations
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
```

GitHub Actions runs Black, Flake8, Django checks and the full unit test suite for
pull requests and changes merged into `main`. The CI test job starts a dedicated
PostgreSQL service and uses safe test configuration values.

## Screenshots

<details open>
<summary><strong>API documentation and authentication</strong></summary>

<table>
  <tr>
    <td align="center"><strong>Swagger overview</strong></td>
    <td align="center"><strong>JWT authentication</strong></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/swagger-overview.png" alt="Swagger overview"></td>
    <td><img src="docs/screenshots/swagger-authentication.png" alt="Swagger authentication"></td>
  </tr>
</table>

</details>

<details>
<summary><strong>Books and borrowings</strong></summary>

<table>
  <tr>
    <td align="center"><strong>Books list</strong></td>
    <td align="center"><strong>Borrowing created</strong></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/books-list.png" alt="Books list"></td>
    <td><img src="docs/screenshots/borrowing-created.png" alt="Borrowing created"></td>
  </tr>
  <tr>
    <td align="center"><strong>Active status filter</strong></td>
    <td align="center"><strong>Administrator user filter</strong></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/borrowing-filtering-by-is-active-flag.png" alt="Borrowing filtering by active status"></td>
    <td><img src="docs/screenshots/borrowing-filtering-by-user-id.png" alt="Borrowing filtering by user ID"></td>
  </tr>
  <tr>
    <td align="center"><strong>Book returned</strong></td>
    <td align="center"><strong>Overdue return</strong></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/borrowing-returned.png" alt="Borrowing returned"></td>
    <td><img src="docs/screenshots/return-book-with-overdue-borrowing.png" alt="Overdue borrowing returned"></td>
  </tr>
</table>

</details>

<details>
<summary><strong>Stripe payments</strong></summary>

<table>
  <tr>
    <td align="center"><strong>Payments list</strong></td>
    <td align="center"><strong>Stripe Checkout</strong></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/payments-list.png" alt="Payments list"></td>
    <td><img src="docs/screenshots/stripe-checkout.png" alt="Stripe Checkout"></td>
  </tr>
  <tr>
    <td align="center"><strong>Successful payment</strong></td>
    <td align="center"><strong>Cancelled Checkout</strong></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/successful-payment-via-stripe.png" alt="Successful Stripe payment"></td>
    <td><img src="docs/screenshots/stripe-payment-cancel.png" alt="Stripe payment cancelled"></td>
  </tr>
  <tr>
    <td align="center"><strong>Missing session ID</strong></td>
    <td align="center"><strong>Unknown session ID</strong></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/checkout-success-with-no-session-id.png" alt="Missing Checkout session ID"></td>
    <td><img src="docs/screenshots/checkout-success-with-unknown-session-id.png" alt="Unknown Checkout session ID"></td>
  </tr>
</table>

</details>

<details>
<summary><strong>Overdue fine payment</strong></summary>

<table>
  <tr>
    <td align="center"><strong>Fine Checkout</strong></td>
    <td align="center"><strong>Fine payment status</strong></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/stripe-checkout-for-paying-fine.png" alt="Stripe Checkout for fine"></td>
    <td><img src="docs/screenshots/success-endpoint-for-paying-fine.png" alt="Fine payment success endpoint"></td>
  </tr>
</table>

</details>

<details>
<summary><strong>Telegram notifications</strong></summary>

<table>
  <tr>
    <td align="center"><strong>New borrowing</strong></td>
    <td align="center"><strong>Borrowing payment</strong></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/telegram-new-borrowing-notification.png" alt="Telegram new borrowing notification"></td>
    <td><img src="docs/screenshots/telegram-new-borrowing-paid-notification.png" alt="Telegram borrowing payment notification"></td>
  </tr>
  <tr>
    <td colspan="2" align="center"><strong>Fine payment notification</strong></td>
  </tr>
  <tr>
    <td colspan="2" align="center"><img src="docs/screenshots/telegram-notification-for-paid-fine.png" alt="Telegram fine payment notification" width="520"></td>
  </tr>
  <tr>
    <td align="center"><strong>Overdue report — first part</strong></td>
    <td align="center"><strong>Overdue report — second part</strong></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/telegram-overdue-report-first-part.png" alt="Telegram overdue report first part"></td>
    <td><img src="docs/screenshots/telegram-overdue-report-second-part.png" alt="Telegram overdue report second part"></td>
  </tr>
</table>

</details>

<details>
<summary><strong>Infrastructure and quality</strong></summary>

<table>
  <tr>
    <td align="center"><strong>Docker Compose services</strong></td>
    <td align="center"><strong>Flower dashboard</strong></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/docker-compose-services.png" alt="Docker Compose services"></td>
    <td><img src="docs/screenshots/flower-dashboard.png" alt="Flower dashboard"></td>
  </tr>
  <tr>
    <td align="center"><strong>GitHub Actions</strong></td>
    <td align="center"><strong>Coverage report</strong></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/github-actions-passed.png" alt="GitHub Actions checks passed"></td>
    <td><img src="docs/screenshots/coverage-report.png" alt="Test coverage report"></td>
  </tr>
</table>

</details>

## Development Notes

During development, all listed tasks were implemented, together with two
optional features.

Most tasks were completed in separate branches and submitted through individual
pull requests. However, the three Stripe tasks covering the initial Checkout
Session, automated session creation and success/cancel handling were combined
into one pull request because they represent a single connected payment
workflow.

> [!NOTE]
> Grouping these Stripe tasks kept the dependent payment logic together and
> avoided splitting one incomplete workflow across several pull requests.

---

<div align="center">
  <a href="#contents">Back to contents ↑</a>
</div>
