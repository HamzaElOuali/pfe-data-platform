with source as (
    select * from {{ source('bronze', 'customers') }}
),

renamed as (
    select
        -- Masquage PII : SHA-256
        sha256(customer_id) as customer_id,
        sha256(customer_unique_id) as customer_unique_id,
        customer_zip_code_prefix::integer as customer_zip_code_prefix,
        -- Normalisation géo
        upper(trim(customer_city)) as customer_city,
        upper(trim(customer_state)) as customer_state,
        _ingested_at,
        _batch_id
    from source
    where customer_id is not null
)

select * from renamed
{{ deduplicate('customer_id') }}
