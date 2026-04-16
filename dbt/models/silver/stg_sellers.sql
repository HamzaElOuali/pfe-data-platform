with source as (
    select * from {{ source('bronze', 'sellers') }}
),

renamed as (
    select
        -- Masquage PII : SHA-256
        sha256(seller_id) as seller_id,
        seller_zip_code_prefix::integer as seller_zip_code_prefix,
        upper(trim(seller_city)) as seller_city,
        upper(trim(seller_state)) as seller_state,
        _ingested_at,
        _api_version
    from source
    where seller_id is not null
)

select * from renamed
{{ deduplicate('seller_id') }}
