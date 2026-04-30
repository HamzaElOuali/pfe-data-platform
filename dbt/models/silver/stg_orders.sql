with source as (
    select * from {{ source('bronze', 'orders') }}
),

renamed as (
    select
        order_id,
        -- Masquage PII : SHA-256 sur l'ID client
        sha256(customer_id) as customer_id,
        {{ clean_string('order_status') }} as order_status,
        -- Casting explicite en TIMESTAMP
        order_purchase_timestamp::timestamp as order_purchase_timestamp,
        order_approved_at::timestamp as order_approved_at,
        order_delivered_carrier_date::timestamp as order_delivered_carrier_date,
        order_delivered_customer_date::timestamp as order_delivered_customer_date,
        order_estimated_delivery_date::timestamp as order_estimated_delivery_date,
        _ingested_at,
        _batch_id
    from source
    -- Règle de rejet : PK ou date d'achat manquantes
    where order_id is not null
      and order_purchase_timestamp is not null
),

derived as (
    select
        *,
        -- Calcul des délais de livraison en jours
        date_diff('day', order_purchase_timestamp, order_delivered_customer_date) as delivery_days,
        -- Indicateur de retard
        (order_delivered_customer_date > order_estimated_delivery_date) as is_late,
        -- Calcul de l'ancienneté de la commande en jours par rapport à l'ingestion
        date_diff('day', order_purchase_timestamp, _ingested_at::timestamp) as order_age_days
    from renamed
)

select * from derived
{{ deduplicate('order_id') }}
