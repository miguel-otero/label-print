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
winspool.StartDocPrinterW.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(DOCINFO)]
winspool.StartDocPrinterW.restype = ctypes.c_ulong
winspool.EndDocPrinter.argtypes = [ctypes.c_void_p]
winspool.StartPagePrinter.argtypes = [ctypes.c_void_p]
winspool.WritePrinter.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]


class WindowsSpooler:
    def __init__(self, printer_name: str) -> None:
        self.printer_name = printer_name

    def test(self) -> None:
        handle = self._open()
        winspool.ClosePrinter(handle)

    def send(self, zpl: str) -> None:
        payload = zpl.encode("utf-8")
        handle = self._open()
        job_started = False
        page_started = False
        try:
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

    @staticmethod
    def _raise(message: str) -> None:
        code = ctypes.get_last_error()
        detail = ctypes.FormatError(code).strip() if code else "Error desconocido"
        raise SpoolerError(f"{message}: {detail} ({code})")
