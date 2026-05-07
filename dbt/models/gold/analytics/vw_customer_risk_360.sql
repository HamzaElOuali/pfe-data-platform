{{ config(materialized='view') }}

with scoring as (
    select * from {{ ref('mart_customer_scoring') }}
),
customers as (
    -- On dédoublonne les clients pour n'avoir qu'une ligne par client unique
    select distinct 
        customer_unique_id, 
        customer_city, 
        customer_state,
        latitude,
        longitude
    from {{ ref('dim_customers') }}
)

select
    -- Identité IA
    s.customer_unique_id,
    s.segment_label as customer_segment,
    s.risk_score as churn_probability_score,
    
    -- Localisation
    c.customer_city,
    c.customer_state,
    c.latitude,
    c.longitude

from scoring s
left join customers c on s.customer_unique_id = c.customer_unique_id
