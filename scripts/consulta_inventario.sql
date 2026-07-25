SELECT
    RTRIM(b.f150_id) AS bodega,
    RTRIM(i.f120_referencia) AS referencia,
    e.f400_cant_existencia_1 AS inventario
FROM t400_cm_existencia e
INNER JOIN t121_mc_items_extensiones ext
    ON e.f400_rowid_item_ext = ext.f121_rowid
INNER JOIN t120_mc_items i
    ON ext.f121_rowid_item = i.f120_rowid
INNER JOIN t150_mc_bodegas b
    ON e.f400_rowid_bodega = b.f150_rowid
WHERE e.f400_cant_existencia_1 <> 0
  AND b.f150_id IN (
      '1018',
      '1022',
      '1024',
      '1025',
      '1026',
      '1036',
      '4001'
  )
ORDER BY
    b.f150_id,
    i.f120_descripcion;