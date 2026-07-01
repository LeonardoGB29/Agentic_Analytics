# Esquema usado por el agente

El agente analitico debe consultar la base `dw_retail`, construida como un
esquema estrella sobre TPC-DS. Las consultas del catalogo y las consultas
dinamicas de Gemini deben usar tablas calificadas con base de datos.

## Tabla de hechos

### `dw_retail.fact_ventas`

Tabla central de ventas. Esta particionada por `anio_venta`.

Columnas principales:

- `venta_sk`
- `cliente_sk`
- `tienda_sk`
- `producto_sk`
- `fecha_sk`
- `ticket_number`
- `cantidad`
- `precio_venta`
- `descuento`
- `venta_neta`
- `venta_neta_con_impuesto`
- `impuesto`
- `ganancia_neta`
- `anio_venta`

## Dimensiones

### `dw_retail.dim_cliente`

- `cliente_sk`
- `cliente_id`
- `nombre_completo`
- `email`
- `ciudad`
- `estado`
- `pais`
- `genero`
- `nivel_educativo`
- `potencial_compra`

### `dw_retail.dim_tienda`

- `tienda_sk`
- `tienda_id`
- `nombre_tienda`
- `ciudad`
- `estado`
- `pais`
- `gerente`
- `mercado_desc`

### `dw_retail.dim_producto`

- `producto_sk`
- `producto_id`
- `nombre_producto`
- `categoria`
- `clase`
- `marca`
- `fabricante`
- `precio_actual`
- `costo_mayoreo`

### `dw_retail.dim_fecha`

- `fecha_sk`
- `fecha`
- `anio`
- `mes`
- `dia_mes`
- `dia_semana`
- `trimestre`
- `es_feriado`
- `es_fin_semana`

## Relaciones

- `fact_ventas.cliente_sk = dim_cliente.cliente_sk`
- `fact_ventas.tienda_sk = dim_tienda.tienda_sk`
- `fact_ventas.producto_sk = dim_producto.producto_sk`
- `fact_ventas.fecha_sk = dim_fecha.fecha_sk`

## Reglas para SQL dinamico

- Usar solo `SELECT` o `WITH`.
- Usar solo tablas de `dw_retail`.
- No usar `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`,
  `TRUNCATE`, `MERGE`, `LOAD`, `EXPORT` ni `IMPORT`.
- No incluir `USE dw_retail`.
- No terminar con punto y coma.
- Calificar siempre las tablas, por ejemplo `dw_retail.fact_ventas`.

