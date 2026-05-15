import streamlit as st
import pandas as pd
import joblib
import os
from datetime import datetime

# Configuration de la page
st.set_page_config(page_title="PFE Platform - Predictive Intelligence", page_icon="🔮", layout="wide")

# Chargement des modèles
@st.cache_resource
def load_models():
    m1 = joblib.load("models/model1_delay.pkl")
    m2 = joblib.load("models/model2_churn.pkl")
    m3 = joblib.load("models/model3_segment.pkl")
    return m1, m2, m3

# Interface
st.title("🔮 Intelligence Prédictive - E-commerce Platform")
st.markdown("---")

col1, col2 = st.columns([1, 2])

with col1:
    st.header("🛒 Paramètres de la Commande")
    distance = st.slider("Distance Client-Vendeur (km)", 0, 3000, 500)
    weight = st.number_input("Poids du colis (g)", value=1000)
    price = st.number_input("Montant de la commande ($)", value=150.0)
    freight = st.number_input("Frais de port ($)", value=20.0)
    review = st.select_slider("Score de satisfaction historique", options=[1, 2, 3, 4, 5], value=4)
    month = st.slider("Mois de l'année", 1, 12, datetime.now().month)
    items = st.number_input("Nombre d'articles", value=1, min_value=1)

    btn = st.button("Lancer le Scoring en Cascade", type="primary")

with col2:
    st.header("📊 Résultats des Modèles")
    
    if btn:
        try:
            m1, m2, m3 = load_models()
            
            # Étape 1 : Prédiction du Délai
            data1 = pd.DataFrame([[distance, freight, month, 1]], 
                                columns=['distance_km', 'total_freight', 'order_month', 'order_day_of_week'])
            delay_pred = m1.predict(data1)[0]
            
            # Étape 2 : Risque de Churn
            data2 = pd.DataFrame([[delay_pred, price, review]], 
                                columns=['predicted_delay', 'total_items_price', 'review_score'])
            churn_proba = m2.predict_proba(data2)[0, 1]
            
            # Étape 3 : Segmentation
            data3 = pd.DataFrame([[churn_proba, price, items]], 
                                columns=['churn_proba', 'total_items_price', 'nb_items'])
            cluster = m3.predict(data3)[0]
            
            # Mapping des segments
            segments = {0: "🥉 Client Standard", 1: "💎 Client VIP", 2: "⚠️ Risque de Churn", 3: "🚩 Client Perdu"}
            seg_name = segments.get(cluster, "Inconnu")

            # Affichage des métriques
            m_col1, m_col2, m_col3 = st.columns(3)
            m_col1.metric("Délai Prédit", f"{delay_pred:.1f} jours")
            m_col2.metric("Risque de Churn", f"{churn_proba*100:.1f}%")
            m_col3.metric("Segment", seg_name)
            
            # Conseils
            st.info(f"**Analyse Business :** Ce client est classé comme **{seg_name}**. "
                    f"Le délai de livraison estimé est de **{delay_pred:.1f} jours**.")
            
            if churn_proba > 0.5:
                st.warning("🚨 Attention : Risque de désabonnement élevé ! Une action marketing est recommandée.")
            else:
                st.success("✅ Client stable : Continuez les campagnes de fidélisation standards.")

        except Exception as e:
            st.error(f"Erreur lors du scoring : {e}")
    else:
        st.info("Modifiez les paramètres à gauche et cliquez sur le bouton pour voir la magie opérer.")

st.markdown("---")
st.caption("Plateforme PFE - Module ML Intelligence - Master Data Platform")
