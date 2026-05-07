{{ config(materialized='view') }}

with order_items as (
    select * from {{ ref('fct_order_items') }}
),
products as (
    select * from {{ ref('dim_products') }}
),
sellers as (
    select * from {{ ref('dim_sellers') }}
),
dates as (
    select * from {{ ref('dim_date') }}
)

select
    -- Identifiants
    i.order_key,
    i.order_item_id,
    
    -- Métriques (Ventes)
    i.price as unit_price,
    i.freight_value,
    i.total_item_value as total_revenue,
    
    -- Dimensions Produit
    p.category_name_en as product_category,
    p.product_weight_g,
    p.product_volume_cm3,
    
    -- Dimensions Vendeur
    s.seller_city,
    s.seller_state,
    
    -- Temps
    d.date_actual,
    d.month_name as sale_month,
    d.date_year as sale_year

from order_items i
left join products p on i.product_key = p.product_key
left join sellers s on i.seller_key = s.seller_key
left join dates d on i.date_key = d.date_key
