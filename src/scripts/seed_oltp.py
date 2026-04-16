import os
import pandas as pd
from sqlalchemy import create_engine, text
import time

# DB_URL uses port 5434 to avoid conflict with native Windows PostgreSQL
DB_URL = "postgresql+psycopg2://admin:admin@localhost:5434/oltp_db"

def read_csv_safe(filepath, chunksize=None):
    """Read a CSV with encoding fallback: utf-8 -> latin-1."""
    for encoding in ["utf-8", "latin-1"]:
        try:
            return pd.read_csv(filepath, encoding=encoding, chunksize=chunksize)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Cannot decode {filepath} with utf-8 or latin-1")


def seed_database():
    print("Connecting to postgres_source...")
    engine = create_engine(DB_URL)

    # Check connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Connected successfully!")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "postgres_source")
    data_dir = os.path.normpath(data_dir)
    print(f"Data directory: {data_dir}")

    files_to_load = [
        "customers.csv",
        "orders.csv",
        "order_items.csv",
        "order_payments.csv",
        "order_reviews.csv",
    ]

    for file in files_to_load:
        file_path = os.path.join(data_dir, file)
        if not os.path.exists(file_path):
            print(f"SKIP  {file} — not found at {file_path}")
            continue

        table_name = file.replace(".csv", "")
        print(f"Loading {file} -> table '{table_name}' ...")

        chunk_size = 50_000
        start_time = time.time()

        try:
            for i, chunk in enumerate(read_csv_safe(file_path, chunksize=chunk_size)):
                if_exists_behavior = "replace" if i == 0 else "append"
                chunk.to_sql(table_name, con=DB_URL, if_exists=if_exists_behavior, index=False)
                rows_so_far = (i + 1) * chunk_size
                print(f"  ... {rows_so_far:>8} rows written")

            elapsed = time.time() - start_time
            print(f"  OK  {table_name} loaded in {elapsed:.1f}s")
        except Exception as e:
            print(f"  ERR {file}: {e}")

    print("\nDatabase seeding completed.")


if __name__ == "__main__":
    seed_database()

