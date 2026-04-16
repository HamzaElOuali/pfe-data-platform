"""
Schema Registry — Contrats PyArrow pour les 9 tables du projet.
Ce module est la source unique de vérité pour la structure attendue des données.
Utilisé par : init_bronze_schema, WriteToBronze, Drift Detector, GE Validator.
"""
import pyarrow as pa

# ══════════════════════════════════════════════════════════════
# Source 1 : CSV (Legacy)
# ══════════════════════════════════════════════════════════════

GEOLOCATION_SCHEMA = pa.schema([
    ("geolocation_zip_code_prefix", pa.int64()),
    ("geolocation_lat", pa.float64()),
    ("geolocation_lng", pa.float64()),
    ("geolocation_city", pa.string()),
    ("geolocation_state", pa.string()),
])

PRODUCT_CATEGORY_TRANSLATION_SCHEMA = pa.schema([
    ("product_category_name", pa.string()),
    ("product_category_name_english", pa.string()),
])

# ══════════════════════════════════════════════════════════════
# Source 2 : PostgreSQL OLTP
# ══════════════════════════════════════════════════════════════

CUSTOMERS_SCHEMA = pa.schema([
    ("customer_id", pa.string()),
    ("customer_unique_id", pa.string()),
    ("customer_zip_code_prefix", pa.int64()),
    ("customer_city", pa.string()),
    ("customer_state", pa.string()),
])

ORDERS_SCHEMA = pa.schema([
    ("order_id", pa.string()),
    ("customer_id", pa.string()),
    ("order_status", pa.string()),
    ("order_purchase_timestamp", pa.string()),
    ("order_approved_at", pa.string()),
    ("order_delivered_carrier_date", pa.string()),
    ("order_delivered_customer_date", pa.string()),
    ("order_estimated_delivery_date", pa.string()),
])

ORDER_ITEMS_SCHEMA = pa.schema([
    ("order_id", pa.string()),
    ("order_item_id", pa.int64()),
    ("product_id", pa.string()),
    ("seller_id", pa.string()),
    ("shipping_limit_date", pa.string()),
    ("price", pa.float64()),
    ("freight_value", pa.float64()),
])

ORDER_PAYMENTS_SCHEMA = pa.schema([
    ("order_id", pa.string()),
    ("payment_sequential", pa.int64()),
    ("payment_type", pa.string()),
    ("payment_installments", pa.int64()),
    ("payment_value", pa.float64()),
])

ORDER_REVIEWS_SCHEMA = pa.schema([
    ("review_id", pa.string()),
    ("order_id", pa.string()),
    ("review_score", pa.int64()),
    ("review_comment_title", pa.string()),
    ("review_comment_message", pa.string()),
    ("review_creation_date", pa.string()),
    ("review_answer_timestamp", pa.string()),
])

# ══════════════════════════════════════════════════════════════
# Source 3 : FastAPI REST API
# ══════════════════════════════════════════════════════════════

PRODUCTS_SCHEMA = pa.schema([
    ("product_id", pa.string()),
    ("product_category_name", pa.string()),
    ("product_name_lenght", pa.float64()),
    ("product_description_lenght", pa.float64()),
    ("product_photos_qty", pa.float64()),
    ("product_weight_g", pa.float64()),
    ("product_length_cm", pa.float64()),
    ("product_height_cm", pa.float64()),
    ("product_width_cm", pa.float64()),
])

SELLERS_SCHEMA = pa.schema([
    ("seller_id", pa.string()),
    ("seller_zip_code_prefix", pa.int64()),
    ("seller_city", pa.string()),
    ("seller_state", pa.string()),
])

# ══════════════════════════════════════════════════════════════
# Registre centralisé — clé = nom de la table bronze
# ══════════════════════════════════════════════════════════════

SCHEMAS = {
    # CSV
    "geolocation": GEOLOCATION_SCHEMA,
    "product_category_name_translation": PRODUCT_CATEGORY_TRANSLATION_SCHEMA,
    # OLTP
    "customers": CUSTOMERS_SCHEMA,
    "orders": ORDERS_SCHEMA,
    "order_items": ORDER_ITEMS_SCHEMA,
    "order_payments": ORDER_PAYMENTS_SCHEMA,
    "order_reviews": ORDER_REVIEWS_SCHEMA,
    # API
    "products": PRODUCTS_SCHEMA,
    "sellers": SELLERS_SCHEMA,
}

# Mapping PyArrow type → PostgreSQL type
PYARROW_TO_PG = {
    pa.int64(): "BIGINT",
    pa.float64(): "DOUBLE PRECISION",
    pa.string(): "TEXT",
}

# Colonnes de métadonnées ajoutées à chaque table Bronze
BRONZE_METADATA_COLUMNS = {
    "_ingested_at": "TIMESTAMP NOT NULL DEFAULT NOW()",
    "_source_file": "TEXT",
    "_batch_id": "TEXT",
    "_api_version": "TEXT",
}


def get_pg_create_table(table_name: str, schema_name: str = "bronze") -> str:
    """Génère le DDL CREATE TABLE pour une table Bronze à partir du Schema Registry."""
    if table_name not in SCHEMAS:
        raise ValueError(f"Table '{table_name}' introuvable dans le Schema Registry.")

    pa_schema = SCHEMAS[table_name]
    columns = []

    # Colonnes métier (depuis PyArrow)
    for field in pa_schema:
        pg_type = PYARROW_TO_PG.get(field.type, "TEXT")
        columns.append(f"    {field.name} {pg_type}")

    # Colonnes de métadonnées Bronze
    for col_name, col_def in BRONZE_METADATA_COLUMNS.items():
        columns.append(f"    {col_name} {col_def}")

    columns_sql = ",\n".join(columns)
    return f"CREATE TABLE IF NOT EXISTS {schema_name}.{table_name} (\n{columns_sql}\n);"
