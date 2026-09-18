import os
import re
import urllib.parse
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings

def normalize_database_url(url: str) -> str:
    """
    Ensure correct dialect specification and robust parsing for SQLAlchemy (Psycopg 3).
    - Strips surrounding quotes and whitespace from environment variables.
    - Converts 'postgres://', 'postgresql://', or 'postgresql+psycopg2://' to 'postgresql+psycopg://'.
    - Handles unencoded special characters (like '@') in passwords by splitting
      on the last '@' (which delimits userinfo from host:port).
    - Preserves query parameters, paths, and SSL flags.
    """
    if not url:
        return "sqlite:///./healthvault.db"
    url = url.strip().strip("'\"")
    if url.startswith("sqlite"):
        return url

    # Determine scheme prefix and standardize to postgresql+psycopg:// (Psycopg 3)
    scheme = "postgresql+psycopg://"
    if url.startswith("postgresql+psycopg://"):
        rest = url[len("postgresql+psycopg://"):]
    elif url.startswith("postgresql+psycopg3://"):
        rest = url[len("postgresql+psycopg3://"):]
    elif url.startswith("postgresql+psycopg2://"):
        rest = url[len("postgresql+psycopg2://"):]
    elif url.startswith("postgres://"):
        rest = url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        rest = url[len("postgresql://"):]
    else:
        return url

    # Separate query parameters
    query_part = ""
    if "?" in rest:
        rest, query_part = rest.split("?", 1)
        query_part = "?" + query_part

    # Separate path / database name
    path_part = ""
    if "/" in rest:
        auth_host, path_part = rest.split("/", 1)
        path_part = "/" + path_part
    else:
        auth_host = rest

    # Split credentials and host at the LAST '@'
    if "@" in auth_host:
        userinfo, hostinfo = auth_host.rsplit("@", 1)
        if ":" in userinfo:
            username, raw_password = userinfo.split(":", 1)
            # Unquote in case partially encoded, then quote properly for URL safety
            unquoted_pw = urllib.parse.unquote(raw_password)
            encoded_pw = urllib.parse.quote_plus(unquoted_pw)
            userinfo = f"{username}:{encoded_pw}"
        return f"{scheme}{userinfo}@{hostinfo}{path_part}{query_part}"

    return f"{scheme}{rest}{path_part}{query_part}"

def mask_database_url(url: str) -> str:
    """
    Redacts password in database URL for safe logging and reporting.
    """
    if not url or url.startswith("sqlite"):
        return url
    try:
        norm = normalize_database_url(url)
        u = make_url(norm)
        if u.password:
            return str(u.set(password="***"))
        return str(u)
    except Exception:
        return re.sub(r":([^:@]+)@", ":***@", url)

def create_app_engine(db_url: Optional[str] = None):
    raw_url = db_url or os.environ.get("DATABASE_URL") or settings.DATABASE_URL
    url = normalize_database_url(raw_url)
    is_prod = getattr(settings, "ENVIRONMENT", "").lower() == "production"

    if url.startswith("sqlite"):
        if is_prod:
            raise RuntimeError(
                "Production environment requires a valid PostgreSQL DATABASE_URL. "
                "Silent fallback to SQLite is prohibited in production."
            )
        engine_kwargs = {"connect_args": {"check_same_thread": False}}
    else:
        # PostgreSQL / Supabase connection pool configuration
        connect_args = {"connect_timeout": 10}
        if "sslmode=" not in url.lower() and not ("localhost" in url or "127.0.0.1" in url):
            connect_args["sslmode"] = "require"

        engine_kwargs = {
            "pool_pre_ping": True,
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 10,
            "connect_args": connect_args
        }

    return create_engine(url, **engine_kwargs)

def get_database_engine_type(eng=None) -> str:
    current_engine = eng or engine
    return current_engine.dialect.name

NORMALIZED_DATABASE_URL = normalize_database_url(os.environ.get("DATABASE_URL") or settings.DATABASE_URL)
engine = create_app_engine(NORMALIZED_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

