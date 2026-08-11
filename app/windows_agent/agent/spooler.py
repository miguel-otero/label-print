from __future__ import annotations

import ctypes
import os


class SpoolerError(RuntimeError):
    pass


class DOCINFO(ctypes.Structure):
    _fields_ = [
        ("lpszDocName", ctypes.c_wchar_p),
        ("lpszOutput", ctypes.c_wchar_p),
        ("lpszDatatype", ctypes.c_wchar_p),
    ]


if os.name != "nt":
    raise RuntimeError("El agente de impresion solo puede ejecutarse en Windows.")

winspool = ctypes.WinDLL("winspool.drv", use_last_error=True)
winspool.OpenPrinterW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]
winspool.OpenPrinterW.restype = ctypes.c_bool
winspool.ClosePrinter.argtypes = [ctypes.c_void_p]
winspool.GetPrinterW.argtypes = [
    ctypes.c_void_p,
    ctypes.c_ulong,
    ctypes.c_void_p,
    ctypes.c_ulong,
    ctypes.POINTER(ctypes.c_ulong),
]
winspool.GetPrinterW.restype = ctypes.c_bool
winspool.StartDocPrinterW.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(DOCINFO)]
winspool.StartDocPrinterW.restype = ctypes.c_ulong
winspool.EndDocPrinter.argtypes = [ctypes.c_void_p]
winspool.StartPagePrinter.argtypes = [ctypes.c_void_p]
winspool.WritePrinter.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]

PRINTER_ATTRIBUTE_WORK_OFFLINE = 0x00000400
PRINTER_STATUS_ERRORS = {
    0x00000001: "en pausa",
    0x00000002: "error",
    0x00000004: "pendiente de eliminacion",
    0x00000008: "atasco de papel",
    0x00000010: "sin papel",
    0x00000020: "alimentacion manual requerida",
    0x00000040: "problema de papel",
    0x00000080: "offline",
    0x00000100: "entrada/salida activa",
    0x00000200: "ocupada",
    0x00000400: "imprimiendo",
    0x00000800: "bandeja de salida llena",
    0x00001000: "no disponible",
    0x00002000: "esperando",
    0x00004000: "procesando",
    0x00008000: "inicializando",
    0x00010000: "calentando",
    0x00020000: "toner bajo",
    0x00040000: "sin toner",
    0x00080000: "pagina descartada",
    0x00100000: "requiere intervencion del usuario",
    0x00200000: "sin memoria",
    0x00400000: "puerta abierta",
    0x00800000: "estado del servidor desconocido",
    0x01000000: "ahorro de energia",
}
NON_ERROR_STATUSES = {
    "entrada/salida activa",
    "ocupada",
    "imprimiendo",
    "esperando",
    "procesando",
    "inicializando",
    "calentando",
    "toner bajo",
    "ahorro de energia",
}


class PRINTER_INFO_2(ctypes.Structure):
    _fields_ = [
        ("pServerName", ctypes.c_void_p),
        ("pPrinterName", ctypes.c_void_p),
        ("pShareName", ctypes.c_void_p),
        ("pPortName", ctypes.c_void_p),
        ("pDriverName", ctypes.c_void_p),
        ("pComment", ctypes.c_void_p),
        ("pLocation", ctypes.c_void_p),
        ("pDevMode", ctypes.c_void_p),
        ("pSepFile", ctypes.c_void_p),
        ("pPrintProcessor", ctypes.c_void_p),
        ("pDatatype", ctypes.c_void_p),
        ("pParameters", ctypes.c_void_p),
        ("pSecurityDescriptor", ctypes.c_void_p),
        ("Attributes", ctypes.c_ulong),
        ("Priority", ctypes.c_ulong),
        ("DefaultPriority", ctypes.c_ulong),
        ("StartTime", ctypes.c_ulong),
        ("UntilTime", ctypes.c_ulong),
        ("Status", ctypes.c_ulong),
        ("cJobs", ctypes.c_ulong),
        ("AveragePPM", ctypes.c_ulong),
    ]


class WindowsSpooler:
    def __init__(self, printer_name: str) -> None:
        self.printer_name = printer_name

    def test(self) -> None:
        handle = self._open()
        try:
            self._require_online(handle)
        finally:
            winspool.ClosePrinter(handle)

    def send(self, zpl: str) -> None:
        payload = zpl.encode("utf-8")
        handle = self._open()
        job_started = False
        page_started = False
        try:
            self._require_online(handle)
            if not winspool.StartDocPrinterW(handle, 1, ctypes.byref(DOCINFO("Clinic Label Print", None, "RAW"))):
                self._raise("No se pudo iniciar el trabajo")
            job_started = True
            if not winspool.StartPagePrinter(handle):
                self._raise("No se pudo iniciar la pagina")
            page_started = True
            written = ctypes.c_ulong()
            buffer = ctypes.create_string_buffer(payload)
            if not winspool.WritePrinter(handle, buffer, len(payload), ctypes.byref(written)):
                self._raise("No se pudo escribir en la cola")
            if written.value != len(payload):
                raise SpoolerError("La cola recibio datos incompletos.")
        finally:
            if page_started:
                winspool.EndPagePrinter(handle)
            if job_started:
                winspool.EndDocPrinter(handle)
            winspool.ClosePrinter(handle)

    def _open(self) -> ctypes.c_void_p:
        handle = ctypes.c_void_p()
        if not winspool.OpenPrinterW(self.printer_name, ctypes.byref(handle), None):
            self._raise(f"No se pudo abrir la impresora '{self.printer_name}'")
        return handle

    def _require_online(self, handle: ctypes.c_void_p) -> None:
        needed = ctypes.c_ulong()
        winspool.GetPrinterW(handle, 2, None, 0, ctypes.byref(needed))
        if not needed.value:
            self._raise("No se pudo consultar el estado de la impresora")
        buffer = ctypes.create_string_buffer(needed.value)
        if not winspool.GetPrinterW(handle, 2, buffer, needed.value, ctypes.byref(needed)):
            self._raise("No se pudo consultar el estado de la impresora")
        info = ctypes.cast(buffer, ctypes.POINTER(PRINTER_INFO_2)).contents
        if info.Attributes & PRINTER_ATTRIBUTE_WORK_OFFLINE:
            raise SpoolerError(
                f"La impresora '{self.printer_name}' esta configurada para trabajar sin conexion."
            )
        errors = [
            description
            for flag, description in PRINTER_STATUS_ERRORS.items()
            if info.Status & flag and description not in NON_ERROR_STATUSES
        ]
        if errors:
            raise SpoolerError(
                f"La impresora '{self.printer_name}' no esta disponible: {', '.join(errors)}."
            )

    @staticmethod
    def _raise(message: str) -> None:
        code = ctypes.get_last_error()
        detail = ctypes.FormatError(code).strip() if code else "Error desconocido"
        raise SpoolerError(f"{message}: {detail} ({code})")
