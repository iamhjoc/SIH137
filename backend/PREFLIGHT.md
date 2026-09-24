# Pre-flight Validation

Before deploying SIH26137, run the pre-flight validation script to catch configuration issues early.

## Usage

```bash
cd backend

# Run validation (will fail on errors)
python scripts/preflight.py

# Run strict mode (will fail on both errors AND warnings)
python scripts/preflight.py --strict
```

## What it checks

| Check | Type | Triggers |
|-------|------|----------|
| `.env` file | ERROR | Missing or not readable |
| `DATABASE_URL` | WARNING | Not set or using placeholder |
| `SECRET_KEY` | ERROR | Missing, default, or too short |
| S3 credentials | ERROR | Required if `OBJECT_STORAGE_BACKEND=s3` |
| `Caddyfile` domain | WARNING | Contains placeholder `yourdomain.com` |
| `CORS_ALLOWED_ORIGINS` | WARNING | Set to wildcard `*` |
| Docker | ERROR | Not installed or not in PATH |
| Docker Compose | ERROR | Not installed or available |
| Alembic migrations | WARNING | No migration files found |
| `requirements.txt` | ERROR | Missing or not readable |

## Exit codes

- `0` — All checks passed
- `1` — One or more checks failed (error mode) or warnings encountered (strict mode)

## Quick fixes

### SECRET_KEY
```bash
# Generate a random key
openssl rand -hex 32

# Add to .env
echo "SECRET_KEY=<paste-output-here>" >> .env
```

### S3 credentials
```bash
# If deploying to production, add to .env:
OBJECT_STORAGE_BACKEND=s3
S3_BUCKET=your-bucket-name
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_ENDPOINT_URL=https://s3.region.amazonaws.com  # or your S3-compatible provider
S3_REGION=region-name
```

Or keep using `filesystem` for dev/test (not recommended for production).

### Caddyfile domain
```bash
# Edit backend/Caddyfile and replace:
api.yourdomain.com { ... }

# With your real domain:
api.example.com { ... }
```

### CORS origins
```bash
# Edit .env and set specific origins:
CORS_ALLOWED_ORIGINS=https://app.example.com,https://example.com
```

## Dev vs. Production

### Development (docker-compose.yml)
```bash
# Minimal .env
DATABASE_URL=postgresql+asyncpg://sih_user:sih_pass@postgres:5432/sih26137
REDIS_URL=redis://redis:6379/0
OBJECT_STORAGE_BACKEND=filesystem
SECRET_KEY=dev-key-change-before-production
CORS_ALLOWED_ORIGINS=*
```

Validation will warn but won't block dev startup.

### Production (docker-compose.prod.yml)
```bash
# Full .env with real credentials
DATABASE_URL=postgresql+asyncpg://real_user:real_password@db.example.com/real_db
REDIS_URL=redis://redis:6379/0
OBJECT_STORAGE_BACKEND=s3
S3_BUCKET=your-prod-bucket
S3_ACCESS_KEY=prod-key
S3_SECRET_KEY=prod-secret
SECRET_KEY=<random-32-byte-hex>
CORS_ALLOWED_ORIGINS=https://app.example.com
```

Run `python scripts/preflight.py --strict` before deploying.

## Typical pre-deployment workflow

```bash
cd backend

# 1. Copy template
cp .env.example .env

# 2. Fill in secrets (use your editor or env-file tools)
nano .env

# 3. Validate
python scripts/preflight.py --strict

# 4. Build and start
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 5. Initialize DB
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed.dummy_data
```
