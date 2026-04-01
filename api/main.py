from fastapi import FastAPI
from typing import List

app = FastAPI(
    title="Olist REST API Mock",
    description="API mock pour exposer les données products et sellers du dataset Olist."
)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/products")
def get_products():
    """Endpoint pour récupérer le catalogue produit Olist (Full Refresh)"""
    # TODO (Ingestion Ticket) : 
    # Mettre en place la lecture de olist_products_dataset.csv
    # et retourner les produits sous format JSON.
    return {
        "status": "success",
        "data": [], 
        "message": "Endpoint products prêt pour intégration métier."
    }

@app.get("/sellers")
def get_sellers():
    """Endpoint pour récupérer le référentiel des vendeurs Olist (Full Refresh)"""
    # TODO (Ingestion Ticket) : 
    # Mettre en place la lecture de olist_sellers_dataset.csv
    # et retourner les vendeurs sous format JSON.
    return {
        "status": "success",
        "data": [], 
        "message": "Endpoint sellers prêt pour intégration métier."
    }
