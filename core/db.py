"""core/db.py - Unified FalkorDB connection helper with Cloud & Local support.

Manages FalkorDB connections for both local Docker instances and FalkorDB Cloud.
Configured strictly through environment variables:
- FALKORDB_HOST (default: "localhost")
- FALKORDB_PORT (default: 6379)
- FALKORDB_USERNAME (optional)
- FALKORDB_PASSWORD (optional)
- FALKORDB_SSL (default: "false")
- FALKORDB_GRAPH (default: "supply_chain")

Features:
- 1 retry with exponential backoff on transient connection failures
- Clear error diagnostics for Auth, TLS, and Timeout failures
- Never logs credentials or secrets
"""

import os
import time
import ssl as ssl_module
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from falkordb import FalkorDB
import redis.exceptions

# Ensure .env is loaded
load_dotenv()


def get_connection_config() -> Dict[str, Any]:
    """Parse and return sanitized connection parameters from environment."""
    host = os.getenv("FALKORDB_HOST", "localhost").strip()
    try:
        port = int(os.getenv("FALKORDB_PORT", "6379").strip())
    except ValueError:
        port = 6379

    username = os.getenv("FALKORDB_USERNAME", "").strip() or None
    password = os.getenv("FALKORDB_PASSWORD", "").strip() or None

    ssl_val = os.getenv("FALKORDB_SSL", "false").strip().lower()
    use_ssl = ssl_val in ("true", "1", "yes")

    graph_name = os.getenv("FALKORDB_GRAPH", "supply_chain").strip() or "supply_chain"

    is_cloud = (host != "localhost" and host != "127.0.0.1") or use_ssl or bool(password)

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "ssl": use_ssl,
        "graph_name": graph_name,
        "is_cloud": is_cloud,
    }


def get_db(retries: int = 1, backoff: float = 1.5) -> FalkorDB:
    """Create a FalkorDB client with retry and error categorization.
    
    Never logs passwords or secret tokens.
    """
    cfg = get_connection_config()

    client_kwargs = {
        "host": cfg["host"],
        "port": cfg["port"],
        "socket_timeout": 15,
        "socket_connect_timeout": 15,
    }

    if cfg["username"]:
        client_kwargs["username"] = cfg["username"]
    if cfg["password"]:
        client_kwargs["password"] = cfg["password"]
    if cfg["ssl"]:
        client_kwargs["ssl"] = True

    attempt = 0
    last_err: Optional[Exception] = None

    while attempt <= retries:
        try:
            db = FalkorDB(**client_kwargs)
            # Verify connectivity with PING on underlying Redis client
            db.connection.ping()
            return db
        except (redis.exceptions.AuthenticationError, redis.exceptions.ResponseError) as e:
            err_msg = str(e).lower()
            if "auth" in err_msg or "password" in err_msg or "noauth" in err_msg or "wrongsuser" in err_msg:
                raise ConnectionError(
                    f"FalkorDB Authentication Failed on host '{cfg['host']}:{cfg['port']}'. "
                    f"Verify FALKORDB_USERNAME and FALKORDB_PASSWORD in your environment / .env file."
                ) from e
            last_err = e
        except (ssl_module.SSLError, redis.exceptions.ConnectionError) as e:
            err_str = str(e).lower()
            if "ssl" in err_str or "certificate" in err_str or "tls" in err_str or "handshake" in err_str:
                raise ConnectionError(
                    f"FalkorDB TLS/SSL Handshake Failed on host '{cfg['host']}:{cfg['port']}'. "
                    f"Check FALKORDB_SSL setting (current: {cfg['ssl']}) and TLS certificates."
                ) from e
            last_err = e
        except redis.exceptions.TimeoutError as e:
            last_err = ConnectionError(
                f"FalkorDB Connection Timed Out while reaching '{cfg['host']}:{cfg['port']}' (timeout=15s)."
            )
        except Exception as e:
            last_err = e

        attempt += 1
        if attempt <= retries:
            time.sleep(backoff)

    raise ConnectionError(
        f"Unable to connect to FalkorDB on '{cfg['host']}:{cfg['port']}' after {retries + 1} attempt(s). "
        f"Underlying error: {last_err}"
    )


def get_graph(graph_name: Optional[str] = None):
    """Retrieve the selected FalkorDB graph using unified environment configuration."""
    cfg = get_connection_config()
    target_graph = graph_name or cfg["graph_name"]
    db = get_db()
    return db.select_graph(target_graph)
