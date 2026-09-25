"""Launch only our copied client, and bridge its native input to the match service."""
import hashlib
import json
from pathlib import Path
import queue
import socket
import threading
import winsound
import frida
from .assets import Assets
from .server import CONTROL_VERSION

CLIENT_SHA256='bf817ef80d98872ffe117b9d7d11a79b4238ea616bd9a9a828a97c8db91d5ccd'

class Client:
    def __init__(self,original,host='127.0.0.1',password='',control_port=1851,side='auto',owner_token=''):
        self.original=Path(original).resolve();self.host=socket.gethostbyname(host.strip());self.password=password;self.control_port=control_port
        self.socket=None;self.reader=None;self.device=None;self.pid=None;self.session=None;self.script=None
        self.events=queue.Queue(maxsize=100);self.outgoing=queue.Queue(maxsize=256);self.closed=threading.Event();self.info={}
        self.side=side;self.owner_token=owner_token
        self.sounds={}

    def start(self):
        exe=self.original/'creation.exe'
        if hashlib.sha256(exe.read_bytes()).hexdigest()!=CLIENT_SHA256:raise ValueError('Unsupported creation.exe; use the included original 1.50.0.621 client')
        assets=Assets(self.original)
        for name in ('Garand','Mauser','BAR','MG42','Thompson','MP40','Grenade'):
            relative=assets.objects[name.casefold()]['properties']['File Name'].replace('\\','/')
            filename=(self.original/relative).resolve()
            if filename.is_relative_to(self.original) and filename.is_file():self.sounds[name]=filename
        try:
            self.socket=socket.create_connection((self.host,self.control_port),timeout=10);self.reader=self.socket.makefile('rb')
            self.socket.sendall((json.dumps(dict(version=CONTROL_VERSION,password=self.password,side=self.side,owner_token=self.owner_token))+'\n').encode())
            self.info=json.loads(self.reader.readline(4096))
            if 'error' in self.info:raise ValueError(self.info['error'])
            self.socket.settimeout(90)
            self.device=frida.get_local_device()
            self.pid=self.device.spawn([str(exe),'-g3','-i'+self.host,'-u'+self.info['username'],'-s1'],cwd=str(self.original),stdio='pipe')
            self.session=self.device.attach(self.pid)
            self.session.on('detached',lambda *args:self.closed.set())
            bridge=Path(__file__).with_name('bridge.js').read_text()
            if self.info['port']!=1850:
                # Test/custom-port compatibility; only change the game's endpoint, never unrelated sockets.
                bridge += '\n'+"Interceptor.attach(Process.getModuleByName('ws2_32.dll').getExportByName('connect'),{onEnter(a){let p=a[1];if(p.readU16()===2&&p.add(2).readU8()===7&&p.add(3).readU8()===58){p.add(2).writeU8(PORT>>8);p.add(3).writeU8(PORT&255);}}});".replace('PORT',str(int(self.info['port'])))
            self.script=self.session.create_script(bridge)
            self.script.on('message',self.message);self.script.load()
            threading.Thread(target=self.read,daemon=True).start();threading.Thread(target=self.write,daemon=True).start()
            self.device.resume(self.pid)
        except Exception:self.close();raise
        return self.info

    def message(self,message,data):
        if message.get('type')=='send':
            if message['payload'].get('type')=='debug':self.event(message['payload'])
            else:self.send(message['payload'])
        elif message.get('type')=='error':self.event({'type':'error','text':message.get('stack',str(message))})

    def send(self,event):
        if not self.closed.is_set():
            try:self.outgoing.put_nowait(event)
            except queue.Full:pass

    def event(self,event):
        try:self.events.put_nowait(event)
        except queue.Full:
            try:self.events.get_nowait();self.events.put_nowait(event)
            except queue.Empty:pass

    def read(self):
        try:
            while not self.closed.is_set():
                line=self.reader.readline(16385)
                if not line:raise EOFError('Match service disconnected')
                if len(line)>16384:raise ValueError('Oversized service message')
                event=json.loads(line)
                if not isinstance(event,dict):continue
                if event.get('type')=='sound':
                    filename=self.sounds.get(event.get('name')) if isinstance(event.get('name'),str) else None
                    if filename:
                        try:winsound.PlaySound(str(filename),winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
                        except RuntimeError:pass
                else:self.event(event)
        except (OSError,EOFError,ValueError) as exc:
            if not self.closed.is_set():self.event({'type':'error','text':str(exc)})
            self.closed.set()

    def write(self):
        try:
            while not self.closed.is_set():
                try:event=self.outgoing.get(timeout=15)
                except queue.Empty:event={'type':'ping'}
                self.socket.sendall((json.dumps(event,separators=(',',':'))+'\n').encode())
        except OSError:self.closed.set()

    def close(self):
        self.closed.set()
        winsound.PlaySound(None,0)
        if self.socket:
            try:self.socket.shutdown(socket.SHUT_RDWR);self.socket.close()
            except OSError:pass
        if self.pid and self.device:
            try:self.device.kill(self.pid)
            except frida.ProcessNotFoundError:pass
            self.pid=None
        if self.session:
            try:self.session.detach()
            except frida.InvalidOperationError:pass
