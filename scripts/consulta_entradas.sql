WITH base AS (
    SELECT
        RTRIM(i.f120_referencia) AS referencia,
        CASE
            WHEN d.f470_ind_naturaleza = 1 THEN d.f470_cant_1
            ELSE 0
        END AS entradas_inv,
        RTRIM(h.f350_id_tipo_docto)
            + '-'
            + CAST(h.f350_consec_docto AS VARCHAR(30)) AS documento,
        h.f350_fecha AS fecha,
        RTRIM(b.f150_id) AS bodega,
        RTRIM(t.f200_nit) AS proveedor_nit,
        RTRIM(t.f200_razon_social) AS proveedor_razon_social
    FROM t470_cm_movto_invent d
    INNER JOIN t350_co_docto_contable h
        ON d.f470_rowid_docto = h.f350_rowid
    INNER JOIN t121_mc_items_extensiones ext
        ON d.f470_rowid_item_ext = ext.f121_rowid
    INNER JOIN t120_mc_items i
        ON ext.f121_rowid_item = i.f120_rowid
    INNER JOIN t150_mc_bodegas b
        ON d.f470_rowid_bodega = b.f150_rowid
    LEFT JOIN t200_mm_terceros t
        ON h.f350_rowid_tercero = t.f200_rowid
    LEFT JOIN t284_co_ccosto cc
        ON d.f470_rowid_ccosto_movto = cc.f284_rowid
    LEFT JOIN t125_mc_items_criterios ic
        ON i.f120_rowid = ic.f125_rowid_item
        AND ic.f125_id_plan = '20 '
    LEFT JOIN t106_mc_criterios_item_mayores l
        ON ic.f125_id_plan = l.f106_id_plan
        AND ic.f125_id_criterio_mayor = l.f106_id
    WHERE h.f350_ind_estado = 1
      AND h.f350_fecha >= %(since_date)s
      AND h.f350_id_tipo_docto IN ('EA', 'ED', 'DV')
)
SELECT
    referencia,
    SUM(entradas_inv) AS entradas_inv,
    documento,
    fecha,
    bodega,
    MAX(proveedor_nit) AS proveedor_nit,
    MAX(proveedor_razon_social) AS proveedor_razon_social
FROM base
GROUP BY
    referencia,
    documento,
    fecha,
    bodega
