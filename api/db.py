"""Remote-first FalkorDB connection; never include credentials in errors."""
import os
from pathlib import Path


class DatabaseError(RuntimeError):
    pass


def connect():
    from dotenv import load_dotenv
    from falkordb import FalkorDB
    from redis.retry import Retry
    from redis.backoff import NoBackoff
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    host = os.getenv('FALKORDB_HOST', '').strip()
    if not host:
        raise DatabaseError('Set FALKORDB_HOST in the repository .env before live verification.')
    tls = os.getenv('FALKORDB_TLS', 'true').lower()
    if tls not in ('true', 'false'):
        raise DatabaseError('FALKORDB_TLS must be true or false.')
    name = os.getenv('GRAPH_NAME', 'corridor')
    if not name or not all(c.isalnum() or c in '_-' for c in name):
        raise DatabaseError('GRAPH_NAME must contain only letters, digits, underscores or hyphens.')
    try:
        client = FalkorDB(host=host, port=int(os.getenv('FALKORDB_PORT', '6379')),
                          username=os.getenv('FALKORDB_USERNAME') or None,
                          password=os.getenv('FALKORDB_PASSWORD') or None,
                          ssl=tls == 'true', ssl_cert_reqs='required',
                          ssl_check_hostname=tls == 'true',
                          socket_connect_timeout=10, socket_timeout=30,
                          retry=Retry(NoBackoff(), 0))
        return client.select_graph(name)
    except Exception:
        raise DatabaseError('Cannot configure FalkorDB; check connection settings.') from None
