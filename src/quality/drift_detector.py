import os
import psycopg2
from dotenv import load_dotenv
from src.quality.schema_registry import SCHEMAS, PYARROW_TO_PG

load_dotenv()

class DriftDetector:
    def __init__(self):
        host = os.getenv("POSTGRES_SOURCE_HOST")
        port = os.getenv("POSTGRES_SOURCE_PORT")
        user = os.getenv("POSTGRES_SOURCE_USER")
        print(f"DEBUG: Tentative de connexion à la SOURCE -> host={host}, port={port}, user={user}")
        
        self.conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=os.getenv("POSTGRES_SOURCE_PASSWORD"),
            dbname=os.getenv("POSTGRES_SOURCE_DB")
        )
        # Mapping PostgreSQL data_type -> PyArrow logical names (simplifié)
        self.PG_TO_SIMPLIFIED = {
            "bigint": "int64",
            "integer": "int64",
            "double precision": "float64",
            "numeric": "float64",
            "text": "string",
            "character varying": "string",
            "timestamp without time zone": "string",
            "timestamp": "string"
        }

    def check_table_drift(self, table_name, pa_schema):
        """Vérifie si le schéma reel en base correspond au contrat PyArrow."""
        with self.conn.cursor() as cur:
            cur.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position;
            """)
            actual_columns = {row[0]: row[1].lower() for row in cur.fetchall()}

        if not actual_columns:
            return [f"Table '{table_name}' introuvable dans la source PostgreSQL !"]

        drifts = []
        # 1. Vérifier si toutes les colonnes attendues existent
        for field in pa_schema:
            expected_name = field.name
            expected_pa_type = str(field.type) # ex: "int64"
            
            if expected_name not in actual_columns:
                drifts.append(f"Colonne manquante : '{expected_name}'")
                continue
            
            actual_type = actual_columns[expected_name]
            simplified_actual = self.PG_TO_SIMPLIFIED.get(actual_type, "unknown")
            
            # 2. Vérifier si le type correspond (approximation basée sur le registre)
            actual_type_norm = actual_type.lower().replace("double precision", "double")
            expected_type_norm = expected_pa_type.lower().replace("double precision", "double")

            if simplified_actual != expected_pa_type and actual_type_norm != expected_type_norm:
                # On ne lève une erreur de drift que si les types sont incompatibles (ex: numérique vs texte)
                # Mais ici nous restons stricts comme demandé.
                drifts.append(f"Type mismatch sur '{expected_name}' : attendu {expected_pa_type}, actuel '{actual_type}'")

        return drifts

    def run_all_checks(self):
        print(" Lancement de la détection de Drift...")
        all_errors = {}
        
        # On ne vérifie que les tables venant de PostgreSQL
        postgres_tables = ["customers", "orders", "order_items", "order_payments", "order_reviews"]
        
        for table in postgres_tables:
            drifts = self.check_table_drift(table, SCHEMAS[table])
            if drifts:
                all_errors[table] = drifts
                print(f" Drift détecté sur '{table}' : {drifts}")
            else:
                print(f" Table '{table}' : Schéma conforme.")

        if all_errors:
            raise RuntimeError(f"DRIFT DETECTED! Pipeline STOPPED. Details: {all_errors}")
        
        print(" Aucun drift détecté. Le pipeline peut continuer.")

if __name__ == "__main__":
    detector = DriftDetector()
    detector.run_all_checks()
