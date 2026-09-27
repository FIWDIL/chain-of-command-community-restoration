"""Add a launcher gate before the hash-checked original x86 entry point.

Only PE headers and an appended section change. Original code addresses stay
fixed for the compatibility bridge. This discourages accidental direct launch;
it is not a security boundary against someone modifying the executable.
"""
import hashlib
from pathlib import Path
import struct

ORIGINAL_SHA256='bf817ef80d98872ffe117b9d7d11a79b4238ea616bd9a9a828a97c8db91d5ccd'

def guarded_engine(data):
    if hashlib.sha256(data).hexdigest()!=ORIGINAL_SHA256:
        raise ValueError('Launcher gate requires the preserved Creation 1.50.0.621 engine')
    data=bytearray(data)
    pe=struct.unpack_from('<I',data,0x3c)[0]
    opt=pe+24
    count=struct.unpack_from('<H',data,pe+6)[0]
    table=opt+struct.unpack_from('<H',data,pe+20)[0]
    imagebase=struct.unpack_from('<I',data,opt+28)[0]
    oldentry=struct.unpack_from('<I',data,opt+16)[0]
    sectionalign,filealign=struct.unpack_from('<II',data,opt+32)
    align=lambda n,a:(n+a-1)//a*a
    rva=align(struct.unpack_from('<I',data,opt+56)[0],sectionalign)
    raw=align(len(data),filealign)
    slot=table+count*40
    if any(data[slot:slot+40]) or slot+40>struct.unpack_from('<I',data,table+20)[0]:
        raise ValueError('No unused section-header slot')
    code=bytearray();labels={};fixups=[]
    def emit(b):code.extend(b)
    def absolute(label):
        fixups.append((len(code),label,False));emit(bytes(4))
    def push(label):emit(b'\x68');absolute(label)
    def branch(op,label):emit(op);fixups.append((len(code),label,True));emit(bytes(4))
    def call(address):emit(b'\xff\x15'+struct.pack('<I',address))
    def resolve(label):
        push(label);emit(b'\x53');call(0x50b250) # GetProcAddress(kernel32, name)
        emit(b'\x85\xc0');branch(b'\x0f\x84','deny')
    emit(b'\x9c\x60\x81\xec\x00\x01\x00\x00') # preserve flags/registers, 256-byte buffer
    push('kernel');call(0x50b254);emit(b'\x89\xc3') # GetModuleHandleA -> ebx
    resolve('getenv')
    emit(b'\x89\xe7\x68\x00\x01\x00\x00\x57') # buffer in edi, size, buffer
    push('variable');emit(b'\xff\xd0\x85\xc0');branch(b'\x0f\x84','deny')
    emit(b'\x3d\x00\x01\x00\x00');branch(b'\x0f\x83','deny') # reject missing/truncated token
    resolve('openevent')
    emit(b'\x57\x6a\x00\x68\x00\x00\x10\x00\xff\xd0') # OpenEventA(SYNCHRONIZE, false, token)
    emit(b'\x85\xc0');branch(b'\x0f\x84','deny')
    emit(b'\x89\xc6\x6a\x00\x56');call(0x50b3bc) # WaitForSingleObject(event, 0)
    emit(b'\x89\xc7\x56');call(0x50b244) # save result, CloseHandle
    emit(b'\x85\xff');branch(b'\x0f\x85','deny') # auto-reset event permits only one launch
    emit(b'\x81\xc4\x00\x01\x00\x00\x61\x9d')
    branch(b'\xe9','original')
    labels['deny']=len(code)
    emit(b'\x6a\x30');push('title');push('message');emit(b'\x6a\x00');call(0x50b628)
    emit(b'\x6a\x01');call(0x50b294);emit(b'\xcc') # ExitProcess(1)
    for name,value in [('kernel','kernel32.dll'),('getenv','GetEnvironmentVariableA'),('openevent','OpenEventA'),
                       ('variable','COC_RESTORED_LAUNCH'),('title','CoC Restored+'),
                       ('message','Please start the game using CoC Restored+.exe.')]:
        labels[name]=len(code);emit(value.encode('ascii')+b'\0')
    for offset,label,relative in fixups:
        target=imagebase+oldentry if label=='original' else imagebase+rva+labels[label]
        value=target-(imagebase+rva+offset+4) if relative else target
        struct.pack_into('<i' if relative else '<I',code,offset,value)
    size=align(len(code),filealign)
    header=struct.pack('<8sIIIIIIHHI',b'.cocgate',len(code),rva,size,raw,0,0,0,0,0x60000020)
    data[slot:slot+40]=header
    struct.pack_into('<H',data,pe+6,count+1)
    struct.pack_into('<I',data,opt+16,rva)
    struct.pack_into('<I',data,opt+56,align(rva+len(code),sectionalign))
    struct.pack_into('<I',data,opt+4,struct.unpack_from('<I',data,opt+4)[0]+size)
    struct.pack_into('<I',data,opt+64,0) # optional checksum, unused for this user-mode image
    data.extend(bytes(raw-len(data)));data.extend(code);data.extend(bytes(size-len(code)))
    return bytes(data)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('original',type=Path);p.add_argument('output',type=Path);args=p.parse_args()
    args.output.write_bytes(guarded_engine(args.original.read_bytes()))
    print(hashlib.sha256(args.output.read_bytes()).hexdigest())
