"""One service/console process per Windows machine."""
import ctypes
from contextlib import contextmanager
from ctypes import wintypes


@contextmanager
def single_instance():
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateMutexW(None, False, "Global\\ClinicLabelPrintAgent")
    error = ctypes.get_last_error()
    if not handle:
        raise RuntimeError("No se puede iniciar el agente; compruebe si el servicio ya está ejecutándose.")
    try:
        if error == 183:  # ERROR_ALREADY_EXISTS
            raise RuntimeError("Ya hay un agente ejecutándose en este equipo.")
        yield
    finally:
        kernel.CloseHandle(handle)
