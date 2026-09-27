import ctypes
import hashlib
from pathlib import Path
import struct
import unittest
from restoration.startup import LaunchPermit
from restoration.client import GUARDED_SHA256
from tools.guard_engine import guarded_engine

class StartupGateTests(unittest.TestCase):
    def test_capability_can_only_be_consumed_once(self):
        permit=LaunchPermit()
        try:
            wait=permit.kernel.WaitForSingleObject
            wait.argtypes=[ctypes.c_void_p,ctypes.c_uint32];wait.restype=ctypes.c_uint32
            self.assertEqual(wait(permit.handle,0),0)
            self.assertEqual(wait(permit.handle,0),258)
            other=LaunchPermit()
            try:self.assertNotEqual(permit.name,other.name)
            finally:other.close()
        finally:permit.close()
        self.assertIsNone(permit.handle)

    def test_patch_preserves_original_sections_and_has_known_hash(self):
        original=(Path(__file__).resolve().parents[1]/'game/creation.exe').read_bytes()
        patched=guarded_engine(original)
        self.assertEqual(hashlib.sha256(patched).hexdigest(),GUARDED_SHA256)
        self.assertEqual(original[0x1000:],patched[0x1000:len(original)])
        pe=struct.unpack_from('<I',original,0x3c)[0]
        self.assertNotEqual(struct.unpack_from('<I',original,pe+40),struct.unpack_from('<I',patched,pe+40))
        with self.assertRaises(ValueError):guarded_engine(patched)
