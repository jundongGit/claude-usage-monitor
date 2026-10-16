# Claude Usage — cloud mirror

Serves the usage dashboard away from the Mac (e.g. on a phone). The menu bar app pushes the
dashboard payload here; viewers sign in with a username and password.

| Route | Who | What |
|---|---|---|
| `POST /api/upload` | menu bar app, `Authorization: Bearer <UPLOAD_TOKEN>` | gzipped payload; stored as the latest copy |
| `POST /api/ping` | menu bar app | heartbeat while unchanged; `409` asks for a full upload |
| `GET /` , `GET /api/usage` | signed-in viewer | the dashboard and its data |
| `GET/POST /login`, `GET /logout` | viewer | sign-in page |
| `GET /healthz` | anyone | liveness |

Only the latest payload is kept, in `./data/` (it already holds the full aggregated history).

## Run

```bash
cp .env.example .env      # fill in, see below
docker compose up -d --build
```

The build context is the repository root, because the dashboard template (`report_template.py`)
is shared with the app. The container joins the external `npm_default` network and listens on
`8000`; point the reverse proxy at `claude-usage:8000` and allow a 10 MB request body.

### Environment

| Variable | Value |
|---|---|
| `ADMIN_USERNAME` | sign-in name, e.g. `usage_admin` |
| `ADMIN_PASSWORD_HASH` | `python3 -c "import bcrypt;print(bcrypt.hashpw(b'<password>', bcrypt.gensalt(12)).decode())"` — write every `$` as `$$` |
| `UPLOAD_TOKEN` | `python3 -c "import secrets;print(secrets.token_urlsafe(32))"`; entered in the app |
| `SESSION_SECRET` | another random string; changing it signs everyone out |

Check the hash survived compose interpolation: `docker exec claude-usage printenv ADMIN_PASSWORD_HASH`
must start with `$2b$12$`.

## Deploy

Use the `/deploy` skill. Current instance: `https://claude-usage.cloud01.top`
(cloud01, `/home/jundong/apps/claude-usage/cloud`).
