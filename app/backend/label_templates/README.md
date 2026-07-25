# Label templates

Plantillas ZPL exportadas desde ZebraDesigner para enviar como trabajos RAW a la cola de impresion.

`etiquetas3.zpl` imprime 3 etiquetas por fila y contiene placeholders:

- `Codigo1`, `Descripcion1`, `Presentacion1`, `Codigobarras1`
- `Codigo2`, `Descripcion2`, `Presentacion2`, `Codigobarras2`
- `Codigo3`, `Descripcion3`, `Presentacion3`, `Codigobarras3`

`etiquetas3_bold.zpl` es una copia de `etiquetas3.zpl` con los campos de texto duplicados
con un desplazamiento horizontal de 1 dot para simular negrilla en impresoras Zebra.
