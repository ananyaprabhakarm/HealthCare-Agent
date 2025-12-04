## Doctor appointment and reporting assistant (MCP-style)

This repo implements a minimal full-stack prototype of an agentic doctor assistant:

- **Backend**: FastAPI with database models and MCP-style tool layer
- **Database**: PostgreSQL (via SQLAlchemy, with a SQLite default for local dev)
- **Frontend**: React (Vite) chat UI for patients and doctors
- **LLM integration**: Pluggable client layer where an MCP-aware LLM can orchestrate tools

The goal is to support:

- Natural-language appointment scheduling from patients
- Multi-turn interactions with context
- Doctor-facing summaries of recent and upcoming appointments
- A secondary notification channel for doctor reports

### Structure

- `backend/`
  - `main.py`: FastAPI entrypoint
  - `app/db.py`: SQLAlchemy engine and session
  - `app/models.py`: core tables (doctors, patients, availability, appointments, chat sessions)
  - `app/schemas.py`: Pydantic request/response models
  - `app/routes/`: HTTP endpoints
  - `app/services/`: calendar, email, notification, LLM integration stubs
  - `app/mcp/tools.py`: core tool implementations the LLM can call
- `frontend/`
  - Vite + React SPA with a patient chat view and doctor dashboard

### Running the backend

From the repo root:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg2://USER:PASSWORD@localhost:5432/doctor_assistant"  # or omit to use SQLite
uvicorn main:app --reload
```

This exposes the FastAPI app at `http://localhost:8000` with:

- `POST /api/chat/patient`
- `POST /api/chat/doctor`
- `POST /api/doctor/summary`

The first import of `backend/main.py` creates the tables automatically.

### Running the frontend

From the repo root:

```bash
cd frontend
npm install
npm run dev
```

Vite serves the UI on `http://localhost:5173` and proxies `/api` to the backend.

### Seeding data for testing

At minimum you need:

- A `Doctor` row for the target doctor (for example, Dr. Ahuja).
- Matching `DoctorAvailability` rows for the weekdays you want to test.

You can insert these via SQLAlchemy shell, Alembic seed, or manual SQL.

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```bash
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000

FRONTEND_HOST=127.0.0.1
FRONTEND_PORT=5173

DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/doctor_assistant

LLM_PROVIDER=openai
LLM_MODEL=gpt-4
LLM_API_KEY=your-openai-api-key-here

GOOGLE_CALENDAR_CREDENTIALS_JSON=/path/to/google-credentials.json
GOOGLE_CALENDAR_DEFAULT_ID=primary

EMAIL_PROVIDER=smtp
EMAIL_FROM_ADDRESS=doctor-assistant@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

NOTIFICATION_PROVIDER=slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
WHATSAPP_API_KEY=your-whatsapp-api-key
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_WHATSAPP_FROM=whatsapp:+1234567890
```

### Integration Details

The system includes end-to-end integrations:

1. **LLM Integration** (`app/services/llm.py`):
   - Supports OpenAI (GPT-4) and Anthropic (Claude) APIs
   - Implements tool-calling with automatic tool execution loop
   - Tools are defined with JSON schemas for the LLM to discover

2. **Google Calendar Integration** (`app/services/calendar.py`):
   - Uses Google Calendar API v3 with service account credentials
   - Creates calendar events when appointments are booked
   - Supports custom calendar IDs or defaults to "primary"

3. **Email Integration** (`app/services/email.py`):
   - Supports multiple providers: SendGrid, Gmail API, or SMTP
   - Sends confirmation emails to patients after booking
   - Configure via `EMAIL_PROVIDER` environment variable

4. **Notification Integration** (`app/services/notification.py`):
   - Supports Slack (webhooks), WhatsApp (Twilio or custom API), and in-app notifications
   - Used for doctor summary reports
   - Configure via `NOTIFICATION_PROVIDER` environment variable

5. **Tool Execution Loop** (`app/routes/chat.py`):
   - When LLM requests a tool call, the backend executes it automatically
   - Tool results are fed back to the LLM for final response generation
   - Supports up to 5 iterations of tool calling per request
   - All tool calls are logged in the database for audit

### How the flows work

- Patients use the patient chat view to ask for availability and bookings.
- Doctors use the doctor chat or the summary buttons for quick statistics.
- The backend exposes MCP-style tools (`get_doctor_availability`, `create_appointment`, `get_appointment_stats`, `send_doctor_notification`) in `app/mcp/tools.py`.
- The LLM client automatically executes tool calls when the LLM requests them, creating a fully agentic workflow.
