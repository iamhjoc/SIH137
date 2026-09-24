#!/usr/bin/env python
"""
Pre-flight validation script for SIH26137 deployment.
Checks for common configuration, credential, and environment issues before deployment.

Usage:
    python -m app.scripts.preflight [--strict]

    --strict: fail on warnings (not just errors)
"""
import os
import sys
from pathlib import Path
from enum import Enum


class CheckLevel(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    PASS = "PASS"


class Check:
    def __init__(self, name: str, level: CheckLevel, message: str, remediation: str = ""):
        self.name = name
        self.level = level
        self.message = message
        self.remediation = remediation

    def __str__(self):
        icon = {
            CheckLevel.ERROR: "[FAIL]",
            CheckLevel.WARNING: "[WARN]",
            CheckLevel.INFO: "[INFO]",
            CheckLevel.PASS: "[PASS]",
        }[self.level]
        s = f"{icon} {self.name}: {self.message}"
        if self.remediation:
            s += f"\n     -> {self.remediation}"
        return s


def run_checks(strict: bool = False) -> tuple[list[Check], bool]:
    """Run all pre-flight checks. Returns (checks, all_passed)."""
    checks = []
    backend_root = Path(__file__).parent.parent

    # 1. .env file exists
    env_file = backend_root / ".env"
    if not env_file.exists():
        checks.append(
            Check(
                "Environment file",
                CheckLevel.ERROR,
                ".env file not found",
                "Run: cp .env.example .env",
            )
        )
    else:
        checks.append(
            Check("Environment file", CheckLevel.PASS, ".env exists")
        )

    # 2. Load .env (if it exists)
    env_vars = {}
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, val = line.split("=", 1)
                        env_vars[key.strip()] = val.strip()

    # 3. Check DATABASE_URL
    db_url = env_vars.get("DATABASE_URL", "").strip()
    if not db_url or "user:pass" in db_url or "user" == db_url.split("://")[-1].split(":")[0]:
        checks.append(
            Check(
                "Database URL",
                CheckLevel.WARNING,
                "DATABASE_URL not set or using placeholder",
                "Set DATABASE_URL in .env to a real PostgreSQL connection string",
            )
        )
    else:
        checks.append(
            Check("Database URL", CheckLevel.PASS, "DATABASE_URL configured")
        )

    # 4. Check SECRET_KEY
    secret_key = env_vars.get("SECRET_KEY", "").strip()
    if not secret_key or secret_key == "your-secret-key-change-this":
        checks.append(
            Check(
                "SECRET_KEY",
                CheckLevel.ERROR,
                "SECRET_KEY is missing or uses default placeholder",
                "Generate: openssl rand -hex 32; add to .env as SECRET_KEY=...",
            )
        )
    elif len(secret_key) < 32:
        checks.append(
            Check(
                "SECRET_KEY strength",
                CheckLevel.WARNING,
                f"SECRET_KEY is short ({len(secret_key)} chars)",
                "Regenerate with: openssl rand -hex 32",
            )
        )
    else:
        checks.append(
            Check("SECRET_KEY", CheckLevel.PASS, "SECRET_KEY is set")
        )

    # 5. Check S3 configuration (only for production)
    storage_backend = env_vars.get("OBJECT_STORAGE_BACKEND", "filesystem").strip()
    if storage_backend == "s3":
        s3_bucket = env_vars.get("S3_BUCKET", "").strip()
        s3_key = env_vars.get("S3_ACCESS_KEY", "").strip()
        s3_secret = env_vars.get("S3_SECRET_KEY", "").strip()

        if not s3_bucket:
            checks.append(
                Check(
                    "S3 bucket",
                    CheckLevel.ERROR,
                    "S3_BUCKET not configured",
                    "Set S3_BUCKET in .env",
                )
            )
        else:
            checks.append(
                Check("S3 bucket", CheckLevel.PASS, f"S3_BUCKET={s3_bucket}")
            )

        if not s3_key or s3_key == "your-access-key":
            checks.append(
                Check(
                    "S3 access key",
                    CheckLevel.ERROR,
                    "S3_ACCESS_KEY not set",
                    "Set S3_ACCESS_KEY in .env",
                )
            )
        else:
            checks.append(
                Check(
                    "S3 access key",
                    CheckLevel.PASS,
                    f"S3_ACCESS_KEY=***{s3_key[-8:]}",
                )
            )

        if not s3_secret or s3_secret == "your-secret-key":
            checks.append(
                Check(
                    "S3 secret key",
                    CheckLevel.ERROR,
                    "S3_SECRET_KEY not set",
                    "Set S3_SECRET_KEY in .env",
                )
            )
        else:
            checks.append(
                Check(
                    "S3 secret key",
                    CheckLevel.PASS,
                    f"S3_SECRET_KEY=***{s3_secret[-8:]}",
                )
            )
    else:
        checks.append(
            Check(
                "Object storage",
                CheckLevel.INFO,
                f"Using {storage_backend} backend (dev/test only if filesystem)",
            )
        )

    # 6. Check Caddyfile domain
    caddyfile = backend_root / "Caddyfile"
    if caddyfile.exists():
        with open(caddyfile) as f:
            caddyfile_content = f.read()
        if "yourdomain.com" in caddyfile_content:
            checks.append(
                Check(
                    "Caddyfile domain",
                    CheckLevel.WARNING,
                    "Caddyfile contains placeholder 'yourdomain.com'",
                    "Replace with your real domain before deploying to production",
                )
            )
        else:
            checks.append(
                Check("Caddyfile domain", CheckLevel.PASS, "Caddyfile configured")
            )

    # 7. Check CORS origins
    cors_origins = env_vars.get("CORS_ALLOWED_ORIGINS", "*").strip()
    if cors_origins == "*":
        checks.append(
            Check(
                "CORS origins",
                CheckLevel.WARNING,
                "CORS_ALLOWED_ORIGINS is '*' (wildcard)",
                "For production, set CORS_ALLOWED_ORIGINS to specific domain(s)",
            )
        )
    else:
        checks.append(
            Check("CORS origins", CheckLevel.PASS, f"CORS_ALLOWED_ORIGINS={cors_origins}")
        )

    # 8. Check Docker availability
    exit_code = os.system("docker --version > /dev/null 2>&1")
    if exit_code != 0:
        checks.append(
            Check(
                "Docker",
                CheckLevel.ERROR,
                "Docker is not installed or not in PATH",
                "Install Docker Desktop or Docker Engine",
            )
        )
    else:
        checks.append(
            Check("Docker", CheckLevel.PASS, "Docker is available")
        )

    # 9. Check docker-compose
    exit_code = os.system("docker compose version > /dev/null 2>&1")
    if exit_code != 0:
        checks.append(
            Check(
                "Docker Compose",
                CheckLevel.ERROR,
                "Docker Compose is not available",
                "Install Docker Compose (usually comes with Docker Desktop)",
            )
        )
    else:
        checks.append(
            Check("Docker Compose", CheckLevel.PASS, "Docker Compose is available")
        )

    # 10. Check Alembic migrations
    migrations_dir = backend_root / "migrations" / "versions"
    if migrations_dir.exists():
        migration_files = list(migrations_dir.glob("*.py"))
        if not migration_files:
            checks.append(
                Check(
                    "Alembic migrations",
                    CheckLevel.WARNING,
                    "No migration files found in migrations/versions/",
                    "Run: alembic revision --autogenerate -m 'init' (once DB is running)",
                )
            )
        else:
            checks.append(
                Check(
                    "Alembic migrations",
                    CheckLevel.PASS,
                    f"{len(migration_files)} migration file(s) found",
                )
            )

    # 11. Check requirements.txt
    req_file = backend_root / "requirements.txt"
    if not req_file.exists():
        checks.append(
            Check(
                "requirements.txt",
                CheckLevel.ERROR,
                "requirements.txt not found",
            )
        )
    else:
        checks.append(
            Check("requirements.txt", CheckLevel.PASS, "requirements.txt exists")
        )

    return checks, _all_passed(checks, strict)


def _all_passed(checks: list[Check], strict: bool) -> bool:
    """Determine if all checks passed (accounting for strict mode)."""
    for check in checks:
        if check.level == CheckLevel.ERROR:
            return False
        if strict and check.level == CheckLevel.WARNING:
            return False
    return True


def main():
    strict = "--strict" in sys.argv
    checks, passed = run_checks(strict=strict)

    print("\n" + "=" * 70)
    print("SIH26137 Pre-flight Validation")
    print("=" * 70 + "\n")

    for check in checks:
        print(check)

    print("\n" + "=" * 70)
    if passed:
        print("[OK] All checks passed! Ready to deploy.")
        sys.exit(0)
    else:
        level = "strict" if strict else "error"
        print(f"[FAIL] Pre-flight check failed ({level} mode).")
        sys.exit(1)


if __name__ == "__main__":
    main()
