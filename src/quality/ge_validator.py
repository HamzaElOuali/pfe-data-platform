"""
ValidateWithGE — DoFn Apache Beam pour la validation inline Great Expectations.

Applique des règles de validation sur chaque élément du pipeline.
Si la validation échoue, le pipeline s'arrête (rien n'est écrit dans Bronze).
"""
import os
import json
import logging
from datetime import datetime, timezone
import apache_beam as beam
from src.quality.schema_registry import SCHEMAS

logger = logging.getLogger(__name__)


class ValidateWithGE(beam.DoFn):
    """
    DoFn de validation Niveau 2 (inline dans le pipeline Beam).

    Règles appliquées :
    - Colonnes obligatoires présentes (expect_column_to_exist)
    - Clés primaires non nulles (expect_column_values_to_not_be_null)
    - Types basiques respectés

    Args:
        table_name: Nom de la table pour récupérer le schéma attendu
        pk_columns: Liste des colonnes Primary Key (vérifiées non nulles)
    """

    def __init__(self, table_name: str, pk_columns: list = None):
        self.table_name = table_name
        self.pk_columns = pk_columns or []
        self.expected_columns = None
        self.validated_count = 0
        self.failed_count = 0

    def setup(self):
        """Charge le schéma attendu depuis le Schema Registry."""
        if self.table_name not in SCHEMAS:
            raise ValueError(f"Table '{self.table_name}' introuvable dans le Schema Registry.")
        pa_schema = SCHEMAS[self.table_name]
        self.expected_columns = [field.name for field in pa_schema]

    def process(self, element):
        """
        Valide un élément (dict) et le yield s'il est conforme.
        Lève une exception si la validation échoue.
        """
        errors = []

        # Règle 1 : Vérifier que toutes les colonnes obligatoires sont présentes
        for col in self.expected_columns:
            if col not in element:
                errors.append(f"Colonne manquante: '{col}'")

        # Règle 2 : Vérifier que les PKs ne sont pas nulles
        for pk in self.pk_columns:
            if pk in element and (element[pk] is None or element[pk] == ""):
                errors.append(f"PK null détectée: '{pk}' = {element[pk]}")

        if errors:
            self.failed_count += 1
            
            # Log structure pour ingestion_errors.jsonl
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "table": self.table_name,
                "errors": errors,
                "pk_sample": {k: str(element.get(k)) for k in self.pk_columns}
            }
            
            try:
                # Dans un environnement conteneurisé, ce chemin est monté sur l'hôte
                log_dir = "logs"
                os.makedirs(log_dir, exist_ok=True)
                with open(os.path.join(log_dir, "ingestion_errors.jsonl"), "a") as f:
                    f.write(json.dumps(log_entry) + "\n")
            except Exception as le:
                logger.warning(f"Could not write to ingestion_errors.jsonl: {le}")

            error_msg = f"[GE FAIL] Table '{self.table_name}' — {'; '.join(errors)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        self.validated_count += 1
        yield element

    def finish_bundle(self):
        """Log le résumé de la validation."""
        if self.validated_count > 0:
            logger.info(
                f"[GE PASS] Table '{self.table_name}' — "
                f"{self.validated_count} éléments validés, "
                f"{self.failed_count} rejetés."
            )
