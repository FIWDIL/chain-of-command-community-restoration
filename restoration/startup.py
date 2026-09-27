"""A per-launch, one-use Windows event capability for the native engine."""
import ctypes
from ctypes import wintypes
import secrets

class LaunchPermit:
    def __init__(self):
        self.name='Local\\CoCRestored-'+secrets.token_hex(24)
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.CreateEventW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.BOOL,wintypes.LPCWSTR]
        self.kernel.CreateEventW.restype=wintypes.HANDLE
        self.kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        self.kernel.CloseHandle.restype=wintypes.BOOL
        self.handle=self.kernel.CreateEventW(None,False,True,self.name)
        if not self.handle:raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        if self.handle:self.kernel.CloseHandle(self.handle);self.handle=None
