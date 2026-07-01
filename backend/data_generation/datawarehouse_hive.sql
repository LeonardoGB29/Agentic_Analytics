
-- Tablas de dimensiones:
--   dim_cliente, dim_tienda, dim_producto, dim_fecha
--
-- Tabla de hechos:
--   fact_ventas (particionada por anio de venta)


-- Ejecutar:
--   hive -f datawarehouse_hive.sql

CREATE DATABASE IF NOT EXISTS dw_retail;
USE dw_retail;

-- ============================================================================
-- DIMENSIONES
-- ============================================================================

-- 1. dim_cliente 
DROP TABLE IF EXISTS dim_cliente;
CREATE TABLE dim_cliente
STORED AS PARQUET
AS
SELECT
    c.c_customer_sk          AS cliente_sk,
    c.c_customer_id          AS cliente_id,
    c.c_salutation           AS saludo,
    c.c_first_name           AS nombre,
    c.c_last_name            AS apellido,
    CONCAT(COALESCE(c.c_first_name, ''), ' ', COALESCE(c.c_last_name, ''))
                             AS nombre_completo,
    c.c_email_address        AS email,
    c.c_birth_year           AS anio_nacimiento,
    c.c_birth_country        AS pais_nacimiento,
    c.c_preferred_cust_flag  AS es_cliente_preferido,
    ca.ca_city               AS ciudad,
    ca.ca_state              AS estado,
    ca.ca_country            AS pais,
    ca.ca_zip                AS codigo_postal,
    cd.cd_gender             AS genero,
    cd.cd_marital_status     AS estado_civil,
    cd.cd_education_status   AS nivel_educativo,
    cd.cd_credit_rating      AS calificacion_crediticia,
    hd.hd_buy_potential      AS potencial_compra,
    hd.hd_dep_count          AS num_dependientes,
    hd.hd_vehicle_count      AS num_vehiculos
FROM tpcds_parquet.customer c
LEFT JOIN tpcds_parquet.customer_address ca
    ON c.c_current_addr_sk = ca.ca_address_sk
LEFT JOIN tpcds_parquet.customer_demographics cd
    ON c.c_current_cdemo_sk = cd.cd_demo_sk
LEFT JOIN tpcds_parquet.household_demographics hd
    ON c.c_current_hdemo_sk = hd.hd_demo_sk;


-- 2. dim_tienda
DROP TABLE IF EXISTS dim_tienda;
CREATE TABLE dim_tienda
STORED AS PARQUET
AS
SELECT
    s.s_store_sk             AS tienda_sk,
    s.s_store_id             AS tienda_id,
    s.s_store_name           AS nombre_tienda,
    s.s_number_employees     AS num_empleados,
    s.s_floor_space          AS superficie_m2,
    s.s_hours                AS horario,
    s.s_manager              AS gerente,
    s.s_city                 AS ciudad,
    s.s_county               AS condado,
    s.s_state                AS estado,
    s.s_zip                  AS codigo_postal,
    s.s_country              AS pais,
    s.s_market_id            AS mercado_id,
    s.s_market_desc          AS mercado_desc,
    s.s_division_name        AS division,
    s.s_company_name         AS compania,
    s.s_tax_precentage       AS tasa_impuesto
FROM tpcds_parquet.store s;


-- 3. dim_producto
DROP TABLE IF EXISTS dim_producto;
CREATE TABLE dim_producto
STORED AS PARQUET
AS
SELECT
    i.i_item_sk              AS producto_sk,
    i.i_item_id              AS producto_id,
    COALESCE(i.i_product_name, i.i_item_desc)
                             AS nombre_producto,
    i.i_item_desc            AS descripcion,
    i.i_category             AS categoria,
    i.i_category_id          AS categoria_id,
    i.i_class                AS clase,
    i.i_class_id             AS clase_id,
    i.i_brand                AS marca,
    i.i_brand_id             AS marca_id,
    i.i_manufact             AS fabricante,
    i.i_manufact_id          AS fabricante_id,
    i.i_size                 AS talla,
    i.i_color                AS color,
    i.i_units                AS unidad_medida,
    i.i_current_price        AS precio_actual,
    i.i_wholesale_cost       AS costo_mayoreo
FROM tpcds_parquet.item i;


-- 4. dim_fecha ───────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dim_fecha;
CREATE TABLE dim_fecha
STORED AS PARQUET
AS
SELECT
    d.d_date_sk              AS fecha_sk,
    d.d_date                 AS fecha,
    d.d_year                 AS anio,
    d.d_moy                  AS mes,
    d.d_dom                  AS dia_mes,
    d.d_dow                  AS dia_semana_num,
    d.d_day_name             AS dia_semana,
    d.d_qoy                  AS trimestre,
    d.d_quarter_name         AS nombre_trimestre,
    d.d_week_seq             AS semana_seq,
    d.d_holiday              AS es_feriado,
    d.d_weekend              AS es_fin_semana,
    d.d_current_day          AS es_dia_actual,
    d.d_current_week         AS es_semana_actual,
    d.d_current_month        AS es_mes_actual,
    d.d_current_quarter      AS es_trimestre_actual,
    d.d_current_year         AS es_anio_actual
FROM tpcds_parquet.date_dim d;


-- ============================================================================
-- TABLA DE HECHOS
-- ============================================================================

DROP TABLE IF EXISTS fact_ventas;
CREATE TABLE fact_ventas (
    venta_sk                 bigint,
    cliente_sk               int,
    tienda_sk                int,
    producto_sk              int,
    fecha_sk                 int,
    promo_sk                 int,
    ticket_number            int,
    cantidad                 int,
    precio_venta             decimal(7,2),
    costo_mayoreo            decimal(7,2),
    descuento                decimal(7,2),
    venta_neta               decimal(7,2),
    venta_neta_con_impuesto  decimal(7,2),
    impuesto                 decimal(7,2),
    cupon                    decimal(7,2),
    ganancia_neta            decimal(7,2)
)
PARTITIONED BY (anio_venta int)
STORED AS PARQUET;


SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;

INSERT OVERWRITE TABLE fact_ventas PARTITION(anio_venta)
SELECT
    -- Genera un SK sintético con ROW_NUMBER (o simplemente usa ticket + item)
    ROW_NUMBER() OVER (ORDER BY ss.ss_ticket_number, ss.ss_item_sk)
                                 AS venta_sk,
    ss.ss_customer_sk            AS cliente_sk,
    ss.ss_store_sk               AS tienda_sk,
    ss.ss_item_sk                AS producto_sk,
    ss.ss_sold_date_sk           AS fecha_sk,
    ss.ss_promo_sk               AS promo_sk,
    ss.ss_ticket_number          AS ticket_number,
    ss.ss_quantity               AS cantidad,
    ss.ss_sales_price            AS precio_venta,
    ss.ss_wholesale_cost         AS costo_mayoreo,
    ss.ss_ext_discount_amt       AS descuento,
    ss.ss_net_paid               AS venta_neta,
    ss.ss_net_paid_inc_tax       AS venta_neta_con_impuesto,
    ss.ss_ext_tax                AS impuesto,
    ss.ss_coupon_amt             AS cupon,
    ss.ss_net_profit             AS ganancia_neta,
    d.d_year                     AS anio_venta
FROM tpcds_parquet.store_sales ss
JOIN tpcds_parquet.date_dim d
    ON ss.ss_sold_date_sk = d.d_date_sk;



SELECT 'dim_cliente'  AS tabla, COUNT(*) AS filas FROM dw_retail.dim_cliente
UNION ALL
SELECT 'dim_tienda',  COUNT(*) FROM dw_retail.dim_tienda
UNION ALL
SELECT 'dim_producto', COUNT(*) FROM dw_retail.dim_producto
UNION ALL
SELECT 'dim_fecha',    COUNT(*) FROM dw_retail.dim_fecha
UNION ALL
SELECT 'fact_ventas',  COUNT(*) FROM dw_retail.fact_ventas;

-- Ver particiones creadas
SHOW PARTITIONS dw_retail.fact_ventas;
