"""Recovered Creation 1.50 TCP framing. All integers are little-endian."""
import struct

MAX_FRAME = 4 * 1024 * 1024

def string(value):
    raw = value.encode('cp1252')
    n = len(raw)
    prefix = bytes([n]) if n < 255 else struct.pack('<BH', 255, n) if n < 65535 else struct.pack('<BHI', 255, 65535, n)
    return prefix + raw

def read_string(data, offset=0):
    n = data[offset]; offset += 1
    if n == 255:
        n, = struct.unpack_from('<H', data, offset); offset += 2
        if n == 65535:
            n, = struct.unpack_from('<I', data, offset); offset += 4
    if offset + n > len(data):
        raise ValueError('Truncated string')
    return data[offset:offset+n].decode('cp1252'), offset+n

def frame(sequence, kind, data=b''):
    payload = struct.pack('<H', kind) + data + struct.pack('<I', 0x89abcdef)
    if len(payload) > MAX_FRAME:
        raise ValueError('Frame too large')
    return struct.pack('<4I', 0xfedcba98, len(payload), sequence, 0xabcdef00) + payload

def read_exact(stream, size):
    out = bytearray()
    while len(out) < size:
        part = stream.recv(size-len(out))
        if not part:
            raise EOFError('Connection closed')
        out.extend(part)
    return bytes(out)

def receive(stream):
    marker, length, seq, generation = struct.unpack('<4I', read_exact(stream, 16))
    if marker != 0xfedcba98 or generation != 0xabcdef00 or not 6 <= length <= MAX_FRAME:
        raise ValueError('Invalid Creation frame')
    payload = read_exact(stream, length)
    if payload[-4:] != struct.pack('<I', 0x89abcdef):
        raise ValueError('Invalid Creation trailer')
    return struct.unpack_from('<H', payload)[0], payload[2:-4]

def version_request():
    return (struct.pack('<HHH', 0, 150, 150) + string('1.50.0.621') + struct.pack('<HH',150,150)
            + string('')*2 + struct.pack('<H',1) + string('local') + string('')*2 + bytes(16)
            + string('') + bytes(16) + string('cocSc') + struct.pack('<H',0) + string('')*2)

def update(uid, prop, value, datatype=1):
    # Server object references use 0xff to escape the optional compression table.
    result = struct.pack('<BBIH', 0xff, 0xff, uid, prop)
    if datatype in (1,2):
        return result + struct.pack('<i', value)
    if datatype == 3:
        return result + string(value)
    if datatype == 4:
        return result + b'\xff' + struct.pack('<I',value)
    if datatype == 5:
        return result + struct.pack('<f', value)
    raise ValueError('Unsupported update type')
