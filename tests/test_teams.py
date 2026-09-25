"""Roster, native snapshot and fourteen-connection regressions."""
from collections import Counter
import json
from pathlib import Path
import socket
import threading
import time
import unittest
from restoration.assets import Assets, EFFECT_BASE, EFFECT_COUNT, STATUS, OBJECTIVE, SMOKE_IMAGE
from restoration.roster import default_pool, loadouts, weapon_caps
from restoration.simulation import Game
from restoration.server import MatchServer, CONTROL_VERSION
from restoration import protocol

ROOT = Path(__file__).resolve().parents[1]


class Teams(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.assets = Assets(ROOT/'original')

    def test_all_sizes_own_four_unique_soldiers_and_share_stockpile(self):
        for size in range(1, 8):
            g = Game(self.assets, team_size=size, seed=20)
            self.assertEqual(len(g.units), size*8)
            self.assertEqual(len({u.cell for u in g.units}), size*8)
            self.assertEqual(len({u.uid for u in g.units}), size*8)
            special = {STATUS, OBJECTIVE, SMOKE_IMAGE, *range(EFFECT_BASE, EFFECT_BASE+EFFECT_COUNT)}
            self.assertFalse(special & {u.uid for u in g.units})
            self.assertFalse({u.uid for u in g.units} & {o['uid'] for o in self.assets.definition['objects']})
            for side in (0, 1):
                weapons = Counter(u.weapon for u in g.units if u.side==side)
                self.assertEqual(weapons['BAR' if side==0 else 'MG42'], default_pool(size)['MG'])
                self.assertEqual(weapons['Thompson' if side==0 else 'MP40'], default_pool(size)['SMG'])
                for slot in range(size):
                    self.assertEqual(len(g.owned(side,slot)), 4)
                    self.assertIn(g.player_identity[side,slot], range(4))
                    self.assertEqual([u.number for u in g.owned(side,slot)], list(range(4)))

    def test_recovered_caps_and_custom_pool(self):
        for side in (0,1):
            self.assertEqual(weapon_caps(self.assets,side), {'MG':1,'SMG':2})
            teams = loadouts(self.assets,7,side,{'MG':7,'SMG':14})
            for team in teams:
                self.assertEqual(Counter(team), {'Garand' if side==0 else 'Mauser':1, 'BAR' if side==0 else 'MG42':1, 'Thompson' if side==0 else 'MP40':2})
            for pool in ({'MG':8,'SMG':0},{'MG':0,'SMG':15},{'MG':-1,'SMG':0},{'MG':1,'SMG':0.5}):
                with self.assertRaises(ValueError):loadouts(self.assets,7,side,pool)
        for size in (0,8,True,1.5):
            with self.assertRaises(ValueError):Game(self.assets,team_size=size)

    def test_other_fireteam_cannot_be_ordered_or_retired(self):
        g=Game(self.assets,team_size=7,ai_sides=())
        g.command(0,[0,1,2,3,4,27],'prone',slot=6)
        self.assertTrue(all(u.stance=='prone' for u in g.owned(0,6)))
        self.assertTrue(all(u.stance=='stand' for u in g.units if (u.side,u.slot)!=(0,6)))
        g.command(0,[0,1,2,3],'retreat',slot=6);g.step(.1)
        self.assertIsNone(g.winner)
        self.assertTrue(all(u.active for u in g.owned(0,0)))

    def test_ai_respects_human_slots_and_spreads_destinations(self):
        g=Game(self.assets,team_size=7,ai_sides=(0,1),seed=4)
        g.ai_slots.remove((0,0));g.think()
        self.assertFalse(any(u.path for u in g.owned(0,0)))
        destinations=[u.path[-1] for u in g.units if u.path]
        self.assertGreater(len(destinations),20)
        self.assertEqual(len(destinations),len(set(destinations)))

    def test_all_71_maps_support_56_soldiers_and_last_slot_snapshot(self):
        for name in self.assets.map_files:
            with self.subTest(map=name):
                g=Game(self.assets,name,team_size=7,seed=1)
                self.assertEqual(len({u.cell for u in g.units}),56)
                self.assertFalse({u.cell for u in g.units}&g.blocked)
                model=self.assets.model('LastPlayer',g,1,6)
                self.assertGreater(len(model),1000)
                self.assertEqual([g.unit_label(u,1,6) for u in g.owned(1,6)],['1','2','3','4'])
                self.assertEqual(g.unit_label(g.owned(1,0)[0],1,6),'F1.1')


def wait_for(predicate, seconds=12):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if predicate():return
        time.sleep(.025)
    raise AssertionError('Timed out waiting for match service')


class Connection:
    """A wire-level native client: actual framing and snapshot negotiation, no renderer."""
    def __init__(self,server,side='auto',owner=False):
        self.control=socket.create_connection(('127.0.0.1',server.control_port),timeout=5)
        self.reader=self.control.makefile('rb');self.native=None;self.events=[];self.error=None
        self.send(dict(version=CONTROL_VERSION,password='test',side=side,owner_token=server.owner_token if owner else ''))
        self.info=json.loads(self.reader.readline())
        if 'error' in self.info:return
        self.native=socket.create_connection(('127.0.0.1',server.game_port),timeout=5)
        self.thread=threading.Thread(target=self.consume,daemon=True);self.thread.start()
        self.control_thread=threading.Thread(target=self.consume_control,daemon=True);self.control_thread.start()

    def send(self,event):self.control.sendall((json.dumps(event)+'\n').encode())

    def consume(self):
        try:
            self.native.settimeout(30)
            assert protocol.receive(self.native)[0]==0
            self.native.sendall(protocol.frame(1,1))
            assert protocol.receive(self.native)[0]==2
            self.native.sendall(protocol.frame(2,3,protocol.string(self.info['username'])))
            kind,model=protocol.receive(self.native);assert kind==4 and len(model)>1000
            self.native.sendall(protocol.frame(3,13))
            assert protocol.receive(self.native)[0]==5
            while True:
                kind,data=protocol.receive(self.native)
                assert kind==8
        except (OSError,EOFError):pass
        except Exception as exc:self.error=repr(exc)

    def consume_control(self):
        try:
            while True:
                line=self.reader.readline()
                if not line:break
                event=json.loads(line)
                if event.get('type')=='status':self.events.append(event)
        except (OSError,ValueError):pass

    def close(self):
        for stream in (self.control,self.native):
            if stream:
                try:stream.shutdown(socket.SHUT_RDWR);stream.close()
                except OSError:pass


class NetworkTeams(unittest.TestCase):
    def test_fourteen_players_lobby_ownership_full_room_disconnect_and_rejoin(self):
        assets=Assets(ROOT/'original')
        server=MatchServer(assets,'AbbeyArden',offline=False,bind='127.0.0.1',password='test',game_port=0,control_port=0,team_size=7)
        clients=[];server.start()
        try:
            host=Connection(server,owner=True);clients.append(host)
            for side in (0,1):
                for _ in range(6 if side==0 else 7):clients.append(Connection(server,side=side))
            wait_for(lambda:len(server.sessions)==14 and all(s['peer'] and s['peer'].ready for s in server.sessions.values()))
            self.assertEqual({(c.info['side'],c.info['slot']) for c in clients},{(s,f) for s in (0,1) for f in range(7)})
            self.assertEqual(server.game.time,0)
            extra=Connection(server);clients.append(extra);self.assertIn('error',extra.info)
            guest=clients[6]
            guest.send({'type':'mouse','phase':1,'button':1,'world':'World','x':10**100,'y':10})
            guest.send({'type':'mouse','phase':1,'button':1,'world':'World','x':83,'y':65,'modifiers':[]})
            guest.send({'type':'command','action':'start'});time.sleep(.15);self.assertFalse(server.started)
            host.send({'type':'command','action':'start'});wait_for(lambda:server.game.time>0)
            self.assertEqual(server.game.ai_slots,set())
            guest.send({'type':'command','action':'select','indices':[0,1,2,3,27]})
            guest.send({'type':'command','action':'prone','side':1,'slot':0})
            wait_for(lambda:all(u.stance=='prone' for u in server.game.owned(0,6)))
            self.assertTrue(all(u.stance=='stand' for u in server.game.owned(0,0)))
            # Disconnect and reconnect cannot duplicate or replenish the original soldiers.
            owned=server.game.owned(0,6)
            with server.lock:
                owned[0].ammo=1;owned[0].reserve=0
            original_ids=[u.uid for u in owned]
            guest.close();wait_for(lambda:(0,6) in server.game.ai_slots)
            replacement=Connection(server,side=0);clients.append(replacement)
            wait_for(lambda:replacement.events)
            self.assertEqual(replacement.info['slot'],6)
            self.assertEqual([u.uid for u in server.game.owned(0,6)],original_ids)
            self.assertLessEqual(owned[0].ammo,1);self.assertEqual(owned[0].reserve,0)
            self.assertEqual(len(server.game.units),56)
            for client in clients:
                self.assertIsNone(client.error)
            self.assertFalse(server.stop_event.is_set(),server.errors)
            self.assertTrue(all(len(c.events[-1]['units'])==4 for c in clients if c.events))
        finally:
            server.close()
            for client in clients:client.close()


if __name__=='__main__':unittest.main()
