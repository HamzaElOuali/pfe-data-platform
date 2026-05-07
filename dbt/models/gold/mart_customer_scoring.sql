/*
    Mart Customer Scoring : Table de serving finale.
    Regroupe les résultats de segmentation et les scores de risque.
    C'est cette table qui sera utilisée pour les dashboards stratégiques.
*/

with customer_metrics as (
    select
        c.customer_unique_id,
        count(o.order_key) as order_frequency,
        sum(o.total_order_value) as monetary_value,
        avg(o.delivery_days) as avg_delivery_days,
        sum(case when o.is_late then 1 else 0 end) as total_late_orders,
        avg(r.review_score) as avg_satisfaction_score
    from {{ ref('dim_customers') }} c
    left join {{ ref('fct_orders') }} o on c.customer_key = o.customer_key
    left join {{ ref('fct_order_reviews') }} r on o.order_key = r.order_key
    group by 1
),

scoring as (
    select
        *,
        -- Calcul d'un Score de Risque (0 à 100)
        -- Plus le score est haut, plus le client est "à risque" de ne plus revenir
        case 
            when avg_satisfaction_score < 3 then 80
            when total_late_orders > 0 then 50
            else 20
        end as risk_score,
        
        -- Segmentation (Layer 3)
        case 
            when order_frequency > 1 or monetary_value > 500 then 'VIP'
            when avg_satisfaction_score < 3 or total_late_orders > 1 then 'AT_RISK'
            else 'NEUTRAL'
        end as segment_label
    from customer_metrics
)

select * from scoring
