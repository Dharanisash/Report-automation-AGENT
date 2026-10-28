# Operational Run Guide: Packaging Reporting Agent

This guide provides end-to-end instructions for deploying, configuring, and operating the **Autonomous LangGraph Packaging Reporting Agent** in staging and production environments.

---

## 1. Prerequisites

- **Python**: Version `3.9` or higher (`python3 --version`)
- **OpenAI API Key**: Access to GPT-4o (`export OPENAI_API_KEY="sk-proj-..."`)
- **Network / API Access**:
  - Outbound HTTPS to `https://api.openai.com`
  - Access to ServiceNow instance (Table API: `sc_task`, `sc_req_item`)
  - Access to Microsoft Graph API (Intune `deviceAppManagement/mobileApps`)
  - Access to SMTP Relay or Exchange Online (if sending real emails)

---

## 2. Quick Setup & Virtual Environment

### Step 1: Clone Repository & Create Virtual Environment
```bash
git clone https://github.com/Dharanisash/Report-automation-AGENT.git
cd Report-automation-AGENT

python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 2: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Configuration (`.env`)

Copy the example environment configuration template:
```bash
cp .env.example .env
```

Open `.env` and configure your credentials:

```ini
# --- LLM Engine ---
OPENAI_API_KEY=sk-proj-your-openai-api-key-here
OPENAI_MODEL=gpt-4o

# --- Database ---
DB_PATH=packaging_agent_state.db

# --- ServiceNow (Table API) ---
SNOW_INSTANCE_URL=https://your-instance.service-now.com
SNOW_USERNAME=svc_packaging_agent
SNOW_PASSWORD=your_secure_password
SNOW_ASSIGNMENT_GROUP=ITSC_WW_RNTBCI_DIR-ICS_Software_Packaging

# --- Telemetry (Microsoft Intune) ---
INTUNE_TENANT_ID=your-tenant-id
INTUNE_CLIENT_ID=your-client-id
INTUNE_CLIENT_SECRET=your-client-secret

# --- Email Notifications ---
EMAIL_TRANSPORT=mock  # Set to 'smtp' for live dispatch
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=packaging-reporting@your-domain.com
SMTP_PASSWORD=your_password
```

> [!NOTE]
> When `EMAIL_TRANSPORT=mock` or `MOCK_EXTERNAL_SERVICES=true`, the agent logs outgoing emails and telemetry to the console without contacting external mail servers. This is ideal for testing and staging verification.

---

## 4. Running the Agent

### Ad-Hoc Execution
To trigger today's reporting cycle manually:
```bash
python packaging_agent.py
```

### Custom Model or Prompt
```bash
python packaging_agent.py --model gpt-4o --prompt "Execute today's packaging deployment reporting lifecycle."
```

### Expected Output
```text
==================================================================
🚀 Initializing Autonomous Packaging Lifecycle Agent
   Model: gpt-4o
   Database: packaging_agent_state.db
==================================================================
[Agent Engine] Graph compiled successfully. Starting autonomous cycle...

[AGENT DISPATCH] Sending to: ['guillaume.meunier@renault.com']
[AGENT DISPATCH] Subject: [D+1 Update] Software Deployment Status: MAP STUDIO PRO
[AGENT DISPATCH] Content preview: <!DOCTYPE html><html lang="en">...

[SNOW WORKNOTE] SCTASK2444402: [Automated Agent] D+1 deployment report emailed to guillaume.meunier@renault.com. Overall compliance: 90.0%.

==================================================================
🏁 Final Agent Execution Summary:
==================================================================
The packaging deployment reporting lifecycle has been executed successfully:
1. Ingested closed packaging tasks and excluded 'New Application Request' (SCTASK2444499).
2. Deduplicated recipients for 'MAP STUDIO PRO' (guillaume.meunier@renault.com).
3. Evaluated milestones: D+1 dispatched for MAP STUDIO PRO, D+3 dispatched for HORSE POWERTRAIN DIAG.
4. Updated ServiceNow catalog tasks with work notes and marked milestones in state database.
```

---

## 5. Automated Daily Scheduling

To ensure D+1, D+3, and D+7 milestones are checked every day at 08:00 UTC, configure one of the following automated runners:

### Option A: Linux / macOS Cron Job
```bash
crontab -e
```
Add the following entry:
```cron
# Run packaging agent every morning at 08:00 UTC
0 8 * * * cd /path/to/Report-automation-AGENT && /path/to/Report-automation-AGENT/venv/bin/python packaging_agent.py >> /var/log/packaging_agent.log 2>&1
```

### Option B: Docker Container
Build and run the containerized agent:
```bash
docker build -t packaging-agent .
docker run --env-file .env -v $(pwd)/packaging_agent_state.db:/app/packaging_agent_state.db packaging-agent
```

Using Docker Compose:
```bash
docker compose up
```

### Option C: GitHub Actions Workflow
The repository includes a ready-to-use GitHub Actions workflow under `.github/workflows/daily-run.yml` for scheduled execution. Add `OPENAI_API_KEY` to repository secrets.

---

## 6. Database Verification & Inspection

You can inspect the local SQLite state store at any time:

```bash
sqlite3 packaging_agent_state.db "SELECT task_id, app_name, req_type, recipients, d1_dispatched, d3_dispatched, d7_dispatched, is_completed FROM tracked_tasks;"
```

Example output:
| task_id | app_name | req_type | recipients | d1 | d3 | d7 | is_completed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `SCTASK2444402` | MAP STUDIO PRO | Existing Application | `guillaume.meunier@renault.com` | 1 | 0 | 0 | 0 |
| `SCTASK2444488` | HORSE POWERTRAIN DIAG | Horse Application | `brossard.arnaud@renault.com;dharani.devi@renault.com` | 1 | 1 | 0 | 0 |

---

## 7. Running Unit Tests

Run the complete test suite:
```bash
python3 -m unittest discover tests
```
Or using pytest:
```bash
pytest -v --cov=packaging_agent
```

---

## 8. Troubleshooting

| Symptom | Probable Cause | Resolution |
| :--- | :--- | :--- |
| `MISSING OPENAI_API_KEY` | Environment variable not exported | Run `export OPENAI_API_KEY="sk-..."` or set in `.env` |
| `Missing dependencies` | Virtual environment not active | Run `source venv/bin/activate && pip install -r requirements.txt` |
| Intune telemetry returns default mock | Intune API unreachable or app name not registered in Graph API | Agent automatically falls back to ADT telemetry query |
| Duplicate emails sent | Milestone flags not committed | Ensure `packaging_agent_state.db` is writable by the process |
| `New Application Request` processed | Business rule bypass | Verify task `req_type` attribute matches standard naming |
