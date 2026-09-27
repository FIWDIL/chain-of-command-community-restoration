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
from .startup import LaunchPermit

CLIENT_SHA256='bf817ef80d98872ffe117b9d7d11a79b4238ea616bd9a9a828a97c8db91d5ccd'
GUARDED_SHA256='fe20adbe96900d870965503dbe28fae39e49f60f26bfc704dd0f39784baf5ad7'

class Client:
    def __init__(self,original,host='127.0.0.1',password='',control_port=1851,side='auto',owner_token='',name='',lobby=False):
        self.original=Path(original).resolve();self.host=socket.gethostbyname(host.strip());self.password=password;self.control_port=control_port
        self.socket=None;self.reader=None;self.device=None;self.pid=None;self.session=None;self.script=None
        self.events=queue.Queue(maxsize=100);self.outgoing=queue.Queue(maxsize=256);self.closed=threading.Event();self.info={}
        self.side=side;self.owner_token=owner_token
        self.launch_permit=None
        self.sounds={};self.name=name;self.lobby=lobby;self.chat_history=[];self.game_open=False;self.closing_game=False;self.room_state={}

    def start(self):
        self.connect()
        if not self.lobby:self.open_game()
        return self.info

    def connect(self):
        if self.socket:return self.info
        try:
            self.socket=socket.create_connection((self.host,self.control_port),timeout=10);self.reader=self.socket.makefile('rb')
            self.socket.sendall((json.dumps(dict(version=CONTROL_VERSION,password=self.password,side=self.side,
                owner_token=self.owner_token,name=self.name,lobby=self.lobby))+'\n').encode())
            self.info=json.loads(self.reader.readline(4096))
            if 'error' in self.info:raise ValueError(self.info['error'])
            self.socket.settimeout(90)
            threading.Thread(target=self.read,daemon=True).start();threading.Thread(target=self.write,daemon=True).start()
        except Exception:self.close();raise
        return self.info

    def open_game(self):
        if self.game_open:return
        exe=self.original/'engine.exe'
        if not exe.is_file():exe=self.original/'creation.exe'
        expected=GUARDED_SHA256 if exe.name=='engine.exe' else CLIENT_SHA256
        if hashlib.sha256(exe.read_bytes()).hexdigest()!=expected:raise ValueError('Unsupported engine; use the included CoC Restored+ engine')
        assets=Assets(self.original)
        for name in ('Garand','Mauser','BAR','MG42','Thompson','MP40','Grenade','MouseDownClick','MouseUpClick',
                     *(f'Scream{i}' for i in range(1,13))):
            relative=assets.objects[name.casefold()]['properties']['File Name'].replace('\\','/')
            if assets.model_root==self.original/'models':relative=relative.replace('models/cocSc/','models/').replace('models/cocsc/','models/')
            filename=(self.original/relative).resolve()
            if filename.is_relative_to(self.original) and filename.is_file():self.sounds[name]=filename
        for name,relative in (('Scream0','sound/scream.wav'),('MG42 alternate','sound/Mg42-1.WAV')):
            filename=assets.model_root/relative
            if filename.is_file():self.sounds[name]=filename
        try:
            self.device=frida.get_local_device()
            self.launch_permit=LaunchPermit()
            self.pid=self.device.spawn([str(exe),'-g3','-i'+self.host,'-u'+self.info['username'],'-s1'],cwd=str(self.original),stdio='pipe',env={'COC_RESTORED_LAUNCH':self.launch_permit.name})
            self.session=self.device.attach(self.pid)
            self.session.on('detached',self.detached)
            icon=str(Path(__file__).with_name('community.ico').resolve())
            bridge='const restorationIconPath='+json.dumps(icon)+';\nconst renamedDefinition='+str((self.original/'enginedata.odf').is_file()).lower()+';\n'+Path(__file__).with_name('bridge.js').read_text()
            bridge='const flattenedModelPaths='+str(assets.model_root==self.original/'models').lower()+';\n'+bridge
            if self.info['port']!=1850:
                bridge += '\n'+"Interceptor.attach(Process.getModuleByName('ws2_32.dll').getExportByName('connect'),{onEnter(a){let p=a[1];if(p.readU16()===2&&p.add(2).readU8()===7&&p.add(3).readU8()===58){p.add(2).writeU8(PORT>>8);p.add(3).writeU8(PORT&255);}}});".replace('PORT',str(int(self.info['port'])))
            self.script=self.session.create_script(bridge)
            self.script.on('message',self.message);self.script.load()
            self.game_open=True
            self.sync_chat();self.sync_room()
            self.device.resume(self.pid)
        except Exception:
            self.close_game();raise

    def detached(self,*args):
        self.game_open=False
        if not self.closed.is_set() and not self.closing_game:
            self.event({'type':'game_closed'})

    def sync_chat(self):
        if self.script:
            text='\r\n'.join(f"{e['sender']}{' ['+e['channel']+']' if e.get('channel') else ''}: {e['text']}" for e in self.chat_history[-100:])
            try:self.script.post({'type':'chat_display','text':text})
            except frida.InvalidOperationError:pass

    def sync_room(self):
        if self.script:
            try:self.script.post({'type':'room_state','state':self.room_state})
            except frida.InvalidOperationError:pass

    def message(self,message,data):
        if message.get('type')=='send':
            payload=message['payload']
            if payload.get('type')=='mouse' and payload.get('world')=='_HG_CommandDialog_Global' and payload.get('button')==1:
                self.play_sound('MouseDownClick' if payload.get('phase')==0 else 'MouseUpClick', interrupt=False)
            if payload.get('type') in ('debug','ui'):self.event(payload)
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
                if event.get('type')=='return_lobby':
                    self.close_game()
                    self.info['map']=event['map']
                if event.get('type')=='lobby':
                    self.room_state=event;self.sync_room()
                if event.get('type') in ('assignment','lobby'):
                    self.info.update({k:event[k] for k in ('side','slot')})
                if event.get('type')=='chat_history':
                    self.chat_history=((self.chat_history if event.get('append') else [])+event.get('messages',[]))[-100:];self.sync_chat()
                elif event.get('type')=='chat':
                    self.chat_history=(self.chat_history+[event])[-100:];self.sync_chat()
                if event.get('type')=='ui' and event.get('action')=='chat' and self.script:
                    try:self.script.post({'type':'focus_chat'})
                    except frida.InvalidOperationError:pass
                if event.get('type')=='sound':
                    self.play_sound(event.get('name'))
                else:self.event(event)
        except (OSError,EOFError,ValueError) as exc:
            if not self.closed.is_set():self.event({'type':'error','text':str(exc)})
            self.closed.set()

    def play_sound(self, name, interrupt=True):
        filename=self.sounds.get(name) if isinstance(name,str) else None
        if filename:
            flags=winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT
            if not interrupt:flags|=winsound.SND_NOSTOP
            try:winsound.PlaySound(str(filename),flags)
            except RuntimeError:pass

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
        self.close_game()

    def close_game(self):
        self.closing_game=True
        if self.pid and self.device:
            try:self.device.kill(self.pid)
            except (frida.ProcessNotFoundError,frida.InvalidOperationError):pass
            self.pid=None
        if self.session:
            try:self.session.detach()
            except frida.InvalidOperationError:pass
        self.script=None;self.session=None;self.game_open=False;self.closing_game=False
        if self.launch_permit:self.launch_permit.close();self.launch_permit=None
