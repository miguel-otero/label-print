# Productos sin código propio

Los tres flujos (etiquetas individuales, inventario y entradas) admiten las
presentaciones importadas con `codigo_propio = false`. La presentación elegida
determina automáticamente si se imprime el código de barras. La referencia
interna, descripción y presentación conservan sus coordenadas; el espacio de
las barras queda vacío. No existe una opción manual para cambiar la modalidad.

El catálogo agrupa únicamente presentaciones sin código propio con la misma
referencia, cantidad numérica y UM de barras normalizada (mayúsculas y espacios).
La fila de menor ID representa al grupo; buscar cualquiera de sus códigos del
fabricante devuelve esa misma opción. Los productos con código propio mantienen
su identidad. La agrupación ocurre antes del conteo y la paginación y no modifica
ni elimina datos importados.

Se exige una cantidad por UM positiva y una UM de presentación. El código de
barras puede estar vacío cuando no se imprime. Las cantidades automáticas,
ajustes manuales y límites de lote mantienen su comportamiento. La vista previa
del lote muestra las tres primeras etiquetas resueltas en el orden de impresión.

`PrintHistory.prints_barcode` y cada artículo del lote registran un booleano para
los trabajos nuevos. Los registros anteriores conservan `null` y la interfaz
indica «Modalidad no registrada». Los reintentos utilizan el ZPL almacenado,
incluso si cambia o desaparece el producto del catálogo.

## Actualización y reversión

Actualizar backend y frontend juntos y reiniciar ambos servicios:

```powershell
docker compose --env-file .\conn\.env restart clinic_backend clinic_frontend
```

El backend aplica automáticamente la migración aditiva e idempotente al iniciar.
Para instalaciones con un proceso de migración independiente, ejecutar solamente
`scripts/migrations/20261008_prints_barcode.sql` en la base de la aplicación.
`scripts/postgres_schema.sql` es el esquema de inicialización; no debe ejecutarse
como migración sobre una instalación existente porque recrea el catálogo.

Para revertir, restaurar el código anterior y reiniciar los dos servicios. Dejar
las columnas adicionales: son opcionales y no afectan a la versión anterior.
Los trabajos ya encolados conservan su contenido. No cambia la configuración ni
es necesario reinstalar el agente Windows. Las etiquetas con imágenes no cambian.

## Verificación sin hardware

Las pruebas PostgreSQL crean y eliminan exclusivamente esquemas temporales con
un `search_path` sin acceso al esquema de la cola real. La dependencia de pruebas
se instala en un contenedor temporal:

```powershell
docker compose --env-file .\conn\.env run --rm --no-deps clinic_backend sh -c 'pip install -r requirements-test.txt && PRESENTATION_DATABASE_TESTS=1 CUSTOM_LABEL_DATABASE_TESTS=1 python -m unittest discover -s tests -v'
docker compose --env-file .\conn\.env exec -T clinic_frontend npm test
docker compose --env-file .\conn\.env exec -T clinic_frontend npm run build
python -m compileall app\backend\app app\windows_agent\agent
git diff --check
```

Después de la actualización, comprobar físicamente una etiqueta con barras, una
sin barras y una fila mixta bajo la cuenta de servicio de la Zebra. Confirmar
referencia, descripción y presentación, ausencia de barras y de sus dígitos en
las posiciones correspondientes, y ausencia de textos en posiciones vacías.
