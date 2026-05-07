/*
    Mart ML Prediction Master : Table plate (Wide Table) pour le Machine Learning.
    Grain : Une ligne par Commande.
    Combine les caractéristiques logistiques, clients, produits et satisfaction.
*/

with orders as (
    select * from {{ ref('fct_orders') }}
),

customers as (
    select * from {{ ref('dim_customers') }}
),

-- On prend le premier vendeur de la commande pour simplifier la géo (Layer 1)
order_sellers as (
    select 
        order_key,
        seller_key,
        count(*) as nb_items
    from {{ ref('fct_order_items') }}
    group by 1, 2
    qualify row_number() over (partition by order_key order by nb_items desc) = 1
),

sellers as (
    select * from {{ ref('dim_sellers') }}
),

reviews as (
    select 
        order_key,
        avg(review_score) as avg_review_score
    from {{ ref('fct_order_reviews') }}
    group by 1
),

final as (
    select
        o.order_key,
        o.order_status,
        -- Features Temporelles
        extract('month' from o.order_purchase_timestamp) as order_month,
        extract('dayofweek' from o.order_purchase_timestamp) as order_day_of_week,
        extract('hour' from o.order_purchase_timestamp) as order_hour,
        
        -- Features Géo (Client)
        c.customer_city,
        c.customer_state,
        c.latitude as customer_lat,
        c.longitude as customer_lon,
        
        -- Features Géo (Vendeur)
        s.seller_city,
        s.seller_state,
        s.latitude as seller_lat,
        s.longitude as seller_lon,
        
        -- Calcul de la distance Haversine (Simplifié pour SQL)
        6371 * acos(
            least(1, greatest(-1, 
                cos(radians(s.latitude)) * cos(radians(c.latitude)) * 
                cos(radians(c.longitude) - radians(s.longitude)) + 
                sin(radians(s.latitude)) * sin(radians(c.latitude))
            ))
        ) as distance_km,
        
        -- Features Commandes
        o.total_items_price,
        o.total_freight,
        os.nb_items,
        
        -- Satisfaction (Layer 2)
        coalesce(r.avg_review_score, 0) as review_score,
        
        -- TARGETS
        o.delivery_days,
        o.is_late
        
    from orders o
    left join customers c on o.customer_key = c.customer_key
    left join order_sellers os on o.order_key = os.order_key
    left join sellers s on os.seller_key = s.seller_key
    left join reviews r on o.order_key = r.order_key
)

select * from final
