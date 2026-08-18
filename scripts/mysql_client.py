"""
mysql_client.py
Centralised MySQL connection factory.
All scripts that need MySQL import get_connection() from here.
Credentials are loaded from the project root .env file.
"""

import os
import sys
from pathlib import Path

# Ensure .env at project root is always loaded regardless of CWD
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

try:
    import mysql.connector
except ImportError:
    print("[ERROR] mysql-connector-python is not installed.")
    print("        Run:  pip install mysql-connector-python")
    sys.exit(1)


def get_connection():
    """
    Return a new MySQL connection using credentials from .env.
    Raises EnvironmentError if any required variable is missing.
    """
    host     = os.getenv("MYSQL_HOST")
    port     = os.getenv("MYSQL_PORT", "3306")
    user     = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")
    database = os.getenv("MYSQL_DB")

    missing = [k for k, v in {
        "MYSQL_HOST": host,
        "MYSQL_USER": user,
        "MYSQL_PASSWORD": password,
        "MYSQL_DB": database,
    }.items() if not v]

    if missing:
        raise EnvironmentError(
            f"Missing MySQL env vars: {', '.join(missing)}\n"
            "Check your .env file."
        )

    return mysql.connector.connect(
        host=host,
        port=int(port),
        user=user,
        password=password,
        database=database,
        connection_timeout=30,
        autocommit=False,
    )


if __name__ == "__main__":
    print("[mysql_client] Testing connection...")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT VERSION()")
    version = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    print(f"[mysql_client] Connected successfully. MySQL version: {version}")
