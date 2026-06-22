-- 04_validar.sql - Comprobacion rapida de que las tablas leen bien la data.
USE tpcds_bigdata;
SELECT 'store_sales' AS tabla, COUNT(*) AS filas FROM store_sales
UNION ALL SELECT 'customer',  COUNT(*) FROM customer
UNION ALL SELECT 'item',      COUNT(*) FROM item
UNION ALL SELECT 'store',     COUNT(*) FROM store
UNION ALL SELECT 'date_dim',  COUNT(*) FROM date_dim
UNION ALL SELECT 'catalog_sales', COUNT(*) FROM catalog_sales;
