# NEXORA — BEAST OS

**The Autonomous Business Operating System**

A deployable MVP prototype featuring:
- Business command center with optional OpenAI-powered responses
- AI workforce task board
- Business Brain notes
- Opportunity Radar
- Revenue Intelligence demo
- Business scenario simulator
- Human approval center and activity log
- SQLite persistence

## Deploy to Render

1. Create a GitHub repository and upload the contents of this ZIP.
2. In Render, choose **New + → Blueprint** and connect that GitHub repository.
3. Render detects `render.yaml`; review and deploy.
4. Optional: add `OPENAI_API_KEY` under the Render service's Environment settings for live AI responses.
5. Open your service URL and create an account.

## Important MVP limitations

- Demo opportunities and revenue metrics are illustrative, not live market or financial data.
- Approving an item records the decision only. It does not send emails, change ad budgets, access bank accounts, or execute third-party actions.
- External integrations require API credentials, permissions, secure token storage, and implementation.
- This free Render Blueprint uses SQLite on an ephemeral filesystem. Data (including accounts, tasks and notes) can be lost on restarts/redeploys/spin-down. For persistent data, migrate to managed PostgreSQL before real use.
- This MVP uses a single shared SQLite database and is not a production multi-tenant SaaS launch. Do not invite real customers or store sensitive business data in this prototype.
- For production, add per-user data scoping to every query, stronger session/CSRF controls, rate limiting, backups, monitoring, and a managed PostgreSQL database before inviting real customers.
- Set a strong `SECRET_KEY` in Render. Keep API keys only in Render environment variables, never in source code.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000
