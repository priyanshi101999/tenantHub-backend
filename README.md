# TenantHub Backend

TenantHub is a FastAPI backend for a multi-tenant task and workspace management platform. It supports workspace registration, JWT authentication, plan-based subscription limits, Stripe billing, file uploads, email and push notifications, and background processing.

## Tech Stack

- FastAPI
- SQLAlchemy async ORM
- PostgreSQL
- Alembic
- Redis
- Celery and Celery Beat
- Stripe
- Firebase Admin SDK
- SendGrid
- Twilio
- Pytest
- Docker Compose

## Features

- Workspace registration with a dynamic Free plan assignment from the database
- JWT login, refresh tokens, logout, password reset, email OTP verification, and phone verification
- Admin-managed workspace users with invite links and plan-based user limits
- Task CRUD with pagination, filtering, priorities, statuses, assignees, due dates, and analytics
- Plan-based task limits, user limits, file upload access, email notifications, and push notifications
- Protected file uploads and file opening for task attachments
- Attachment deletion that removes both the database record state and uploaded file from disk
- Stripe Checkout subscriptions, subscription updates, cancellation, and webhook sync
- Firebase Cloud Messaging push notification support
- SendGrid email support
- Redis + Celery support for production-style async workers
- Optional no-Celery mode for hosted demos using in-process background dispatch
- Pytest coverage for API endpoints, services, and business logic
- GitHub Actions build/test/deploy workflow

## Backend Skills Demonstrated

### FastAPI

- Versioned API routing under `/api/v1`
- Dependency injection for database sessions and authenticated users
- Role-based route protection
- Pydantic request and response schemas
- File upload and protected file response endpoints

### PostgreSQL and SQLAlchemy

- Async SQLAlchemy engine and sessions
- Relational workspace, user, task, plan, subscription, and attachment models
- Plan and subscription state stored in the database
- Test database setup isolated from application runtime code

### Stripe

- Stripe Checkout Session creation
- Checkout completion verification
- Subscription creation, update, cancel, and sync
- Webhook handling for checkout, invoice, payment failure, subscription update, and deletion events
- Workspace and plan metadata passed through Stripe sessions/subscriptions

### Firebase Push Notifications

- Device FCM token registration
- Plan-gated push notification support
- Push notification dispatch for task assignment, status updates, and reminders

### Email

- SendGrid email delivery
- Email OTP verification
- Forgot password OTP
- User invite email
- Plan-gated task email notifications

### Redis and Celery

- Redis broker/backend support
- Celery worker for async email, notifications, and Stripe event processing
- Celery Beat scheduler for due-task reminders
- `USE_CELERY=true` enables queued processing
- `USE_CELERY=false` runs email/notification/webhook jobs in background threads for low-cost demos

### Testing

- API endpoint tests
- Service and business-logic tests
- Mocked background jobs for deterministic tests
- GitHub Actions test run on every push and pull request

## API Overview

Base API prefix:

```text
/api/v1
```

Health:

```text
GET /
GET /health
```

Authentication:

```text
POST /api/v1/auth/register
POST /api/v1/auth/verify-email
POST /api/v1/auth/verify-otp
POST /api/v1/auth/login
POST /api/v1/auth/refresh-token
POST /api/v1/auth/change-password
POST /api/v1/auth/forgot-password
POST /api/v1/auth/reset-password
POST /api/v1/auth/set-password
POST /api/v1/auth/logout
POST /api/v1/auth/save-fcm-token
POST /api/v1/auth/send-otp
POST /api/v1/auth/verify-phone
```

Users:

```text
POST   /api/v1/user/create
POST   /api/v1/user/invite
GET    /api/v1/user/list
GET    /api/v1/user/
DELETE /api/v1/user/
```

Tasks:

```text
POST   /api/v1/task/create
PATCH  /api/v1/task/update
DELETE /api/v1/task/
GET    /api/v1/task/list
GET    /api/v1/task/
GET    /api/v1/task/analytics
POST   /api/v1/task/attachment
GET    /api/v1/task/attachment/open
DELETE /api/v1/task/attachment
POST   /api/v1/task/attachment/delete
```

Billing and Stripe:

```text
POST /api/v1/subscription/checkout
POST /api/v1/subscription/checkout/complete
GET  /api/v1/subscription/plans
POST /api/v1/subscription/update
POST /api/v1/subscription/cancel
POST /api/v1/webhook
```

## Local Setup

Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\activate
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create `.env` using the required variables below.

Run the API:

```powershell
uvicorn app.main:app --reload
```

API docs:

```text
http://localhost:8000/docs
```

## Docker Compose

Run the full local stack:

```powershell
docker compose up --build
```

Services:

- FastAPI API
- PostgreSQL
- Redis
- Celery worker
- Celery Beat

## Environment Variables

Required backend variables:

```text
POSTGRES_HOST
POSTGRES_PASSWORD
POSTGRES_PORT
POSTGRES_USER
POSTGRES_DB
DATABASE_URL
SECRET_KEY
ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS
OTP_EXPIRE_MINUTES
SENDGRID_API_KEY
SENDER_MAIL
REDIS_HOST
REDIS_PORT
FRONTEND_BASEURL
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN
TWILIO_SERVICE_SID
USE_CELERY
```

For Render demo deployments without paid Celery workers:

```text
USE_CELERY=false
```

For Docker Compose or production queue workers:

```text
USE_CELERY=true
```

## Tests

Run tests:

```powershell
python -m pytest tests/ -v --tb=short
```

The current suite covers API endpoints, services, and business logic.

## Deployment

The GitHub Actions workflow is in:

```text
.github/workflows/build-deploy.yml
```

It runs tests during build and deploys to Render after a successful push to `main`.

Render production services can be:

- Web Service: FastAPI backend
- PostgreSQL
- Redis
- Optional Background Worker: Celery worker
- Optional Background Worker: Celery Beat

FastAPI start command:

```bash
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
```

Celery worker command:

```bash
celery -A app.core.celery.celery_app worker --loglevel=info
```

Celery Beat command:

```bash
celery -A app.core.celery.celery_app beat --loglevel=info
```

For demo deployments, Celery services can be skipped by leaving `USE_CELERY=false`.
