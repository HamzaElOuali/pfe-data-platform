"""
Regex Patterns — Bibliothèque de motifs pour la validation des données.
Utilisée par le Normalizer et le DQ Rules engine.
"""

# Brésil (Format principal du dataset)
ZIP_CODE_BR = r"^\d{5}-?\d{3}$"  # Supporte 12345 ou 12345-678 (bien que le dataset ait souvent 5 chiffres)
ZIP_CODE_PREFIX_BR = r"^\d{5}$"
STATE_CODE_BR = r"^[A-Z]{2}$"

# Identifiants
UUID_PATTERN = r"^[0-9a-f]{32}$"  # Le dataset utilise des UUID sans tirets (MD5-like)
ORDER_ID_PATTERN = UUID_PATTERN
CUSTOMER_ID_PATTERN = UUID_PATTERN
PRODUCT_ID_PATTERN = UUID_PATTERN

# Numériques & Financier
PRICE_PATTERN = r"^\d+(\.\d{1,2})?$"
INTEGER_PATTERN = r"^\d+$"

# Date & Heure (ISO 8601 simple)
DATE_ISO_PATTERN = r"^\d{4}-\d{2}-\d{2}"
TIMESTAMP_ISO_PATTERN = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"

# Email (basique)
EMAIL_PATTERN = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
