from datetime import datetime, timedelta, timezone

from app.schemas import LabelFormat, PrintHistory, Product


PRODUCTS = [
    Product(id=1, product_code="MED-0001", description="Guantes nitrilo talla M caja x100", unit_of_measure="CAJA", barcode="CB00001", presentation_quantity="100 u"),
    Product(id=2, product_code="MED-0002", description="Jeringa descartable 5ml esteril", unit_of_measure="UN", barcode="CB00002", presentation_quantity="1 u"),
    Product(id=3, product_code="MED-0003", description="Alcohol etilico 96 grados 1L", unit_of_measure="BOT", barcode="CB00003", presentation_quantity="1 L"),
    Product(id=4, product_code="MED-0004", description="Gasa esteril 10x10 cm sobre x5", unit_of_measure="SOB", barcode="CB00004", presentation_quantity="5 u"),
    Product(id=5, product_code="MED-0005", description="Algodon hidrofilo 500g", unit_of_measure="BLS", barcode="CB00005", presentation_quantity="500 g"),
    Product(id=6, product_code="MED-0006", description="Termometro digital clinico", unit_of_measure="UN", barcode="CB00006", presentation_quantity="1 u"),
    Product(id=7, product_code="MED-0007", description="Mascarilla quirurgica triple capa", unit_of_measure="CAJA", barcode="CB00007", presentation_quantity="50 u"),
    Product(id=8, product_code="MED-0008", description="Suero fisiologico 500ml", unit_of_measure="BOT", barcode="CB00008", presentation_quantity="500 ml"),
    Product(id=9, product_code="MED-0009", description="Vendas elasticas 10cm x 5m", unit_of_measure="UN", barcode="CB00009", presentation_quantity="1 u"),
    Product(id=10, product_code="MED-0010", description="Aposito adhesivo esteril 10x15cm", unit_of_measure="UN", barcode="CB00010", presentation_quantity="1 u"),
    Product(id=11, product_code="MED-0011", description="Ibuprofeno 400mg blister x10", unit_of_measure="BLI", barcode="CB00011", presentation_quantity="10 comp"),
    Product(id=12, product_code="MED-0012", description="Paracetamol 500mg blister x20", unit_of_measure="BLI", barcode="CB00012", presentation_quantity="20 comp"),
]

FORMATS = [
    LabelFormat(id=4, name="ZebraDesigner 3 columnas", code="etiquetas3", width_mm=100, height_mm=25, preview_type="format2", active=True, template_file="etiquetas3.zpl"),
    LabelFormat(id=5, name="ZebraDesigner 3 columnas negrilla", code="etiquetas3_bold", width_mm=100, height_mm=25, preview_type="format2", active=True, template_file="etiquetas3_bold.zpl"),
]

now = datetime.now(timezone.utc)
HISTORY = [
    PrintHistory(id=1, timestamp=now - timedelta(minutes=12), user="operador1", product_code="MED-0001", product_description="Guantes nitrilo talla M caja x100", format="etiquetas3", quantity=5, status="success"),
    PrintHistory(id=2, timestamp=now - timedelta(hours=1), user="operador1", product_code="MED-0007", product_description="Mascarilla quirurgica triple capa", format="etiquetas3", quantity=10, status="success"),
    PrintHistory(id=3, timestamp=now - timedelta(hours=3), user="operador2", product_code="MED-0003", product_description="Alcohol etilico 96 grados 1L", format="etiquetas3_bold", quantity=2, status="error", message="Impresora desconectada"),
    PrintHistory(id=4, timestamp=now - timedelta(days=1), user="operador1", product_code="MED-0012", product_description="Paracetamol 500mg blister x20", format="etiquetas3", quantity=20, status="success"),
]
