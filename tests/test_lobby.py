"""Real control connections exercise pre-game lobby ownership and chat."""
import json
import socket
import threading
import time
import unittest
from pathlib import Path
from restoration.assets import Assets
from restoration.server import MatchServer, CONTROL_VERSION

ROOT=Path(__file__).resolve().parents[1]

def wait_for(predicate):
    end=time.monotonic()+6
    while time.monotonic()<end:
        if predicate():return
        time.sleep(.025)
    raise AssertionError('Lobby update timed out')

class LobbyClient:
    def __init__(self,server,name,side=0,owner=False):
        self.socket=socket.create_connection(('127.0.0.1',server.control_port),timeout=5)
        self.reader=self.socket.makefile('rb');self.events=[]
        self.send(dict(version=CONTROL_VERSION,password='',side=side,name=name,lobby=True,owner_token=server.owner_token if owner else ''))
        self.info=json.loads(self.reader.readline())
        self.thread=threading.Thread(target=self.read,daemon=True);self.thread.start()
    def read(self):
        try:
            for line in self.reader:self.events.append(json.loads(line))
        except (OSError,ValueError):pass
    def send(self,event):self.socket.sendall((json.dumps(event)+'\n').encode())
    def close(self):
        try:self.socket.shutdown(socket.SHUT_RDWR)
        except OSError:pass
        self.socket.close();self.reader.close()

class LobbyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.assets=Assets(ROOT/'game')
    def setUp(self):
        self.server=MatchServer(self.assets,'AbbeyArden',offline=False,bind='127.0.0.1',game_port=0,control_port=0,team_size=2)
        self.server.start();self.clients=[]
    def client(self,name,side=0,owner=False):
        c=LobbyClient(self.server,name,side,owner);self.clients.append(c);return c
    def tearDown(self):
        for c in self.clients:c.close()
        self.server.close()
    def test_lobby_does_not_need_native_game_and_host_can_change_side(self):
        host=self.client('Host',1,True);guest=self.client('Guest',0)
        wait_for(lambda:any(e['type']=='lobby' for e in guest.events))
        self.assertEqual(host.info['side'],1);self.assertFalse(self.server.started)
        host.send({'type':'side','side':0})
        wait_for(lambda:any(e['type']=='assignment' and e['side']==0 for e in host.events))
        self.assertEqual(self.server.sessions[host.info['username']]['slot'],1)
        guest.send({'type':'side','side':1})
        wait_for(lambda:any(e['type']=='assignment' and e['side']==1 for e in guest.events))
        self.assertTrue(all(s['peer'] is None for s in self.server.sessions.values()))
    def test_full_side_rejected_and_equipment_unchanged(self):
        host=self.client('Host',0,True);a=self.client('A',1);b=self.client('B',1)
        before=[(u.uid,u.weapon,u.ammo) for u in self.server.game.units]
        host.send({'type':'side','side':1})
        wait_for(lambda:any(e['type']=='notice' for e in host.events))
        self.assertEqual(self.server.sessions[host.info['username']]['side'],0)
        self.assertEqual(before,[(u.uid,u.weapon,u.ammo) for u in self.server.game.units])
    def test_chat_is_broadcast_with_server_author_and_bounded_history(self):
        host=self.client('Host',0,True);guest=self.client('Guest',1)
        host.send({'type':'chat','text':'Hello room','sender':'Impersonated'})
        wait_for(lambda:any(e['type']=='chat' and e['text']=='Hello room' for e in guest.events))
        message=next(e for e in guest.events if e.get('text')=='Hello room')
        self.assertEqual(message['sender'],'Host')
        with self.server.lock:
            for i in range(110):self.server.chat.append(dict(type='chat',id=i,sender='X'*24,text='\u754c'*240))
        late=self.client('Late',1)
        wait_for(lambda:any(e['type']=='chat_history' and e.get('append') for e in late.events))
        wait_for(lambda:sum(len(e['messages']) for e in late.events if e['type']=='chat_history')==100)
        chunks=[e for e in late.events if e['type']=='chat_history']
        self.assertTrue(all(len(json.dumps(e).encode())<16384 for e in chunks))
    def test_only_host_launches_and_sides_lock_while_loading(self):
        host=self.client('Host',0,True);guest=self.client('Guest',1)
        guest.send({'type':'command','action':'start'})
        wait_for(lambda:self.server.sessions[guest.info['username']]['ready'])
        self.assertFalse(self.server.launching);self.assertFalse(self.server.started)
        host.send({'type':'command','action':'start'})
        wait_for(lambda:any(e['type']=='launch' for e in guest.events))
        self.assertTrue(self.server.launching);self.assertFalse(self.server.started)
        guest.send({'type':'side','side':0})
        wait_for(lambda:any(e['type']=='notice' for e in guest.events))
        self.assertEqual(self.server.sessions[guest.info['username']]['side'],1)

if __name__=='__main__':unittest.main()
