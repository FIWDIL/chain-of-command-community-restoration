import io
import math
from pathlib import Path
import socket
import struct
import threading
import unittest
from restoration.assets import Assets, USER
from restoration.simulation import Game, WEAPONS
from restoration import protocol

ROOT=Path(__file__).resolve().parents[1]

class Fragmented:
    def __init__(self,data):self.data=io.BytesIO(data)
    def recv(self,n):return self.data.read(min(n,3))

class WireTests(unittest.TestCase):
    def test_fragmented_frame(self):
        self.assertEqual(protocol.receive(Fragmented(protocol.frame(9,8,b'example'))),(8,b'example'))
    def test_reject_bad_frame(self):
        for data in (bytes(22),protocol.frame(1,4)[:-1]+b'x',struct.pack('<4I',0xfedcba98,9000000,1,0xabcdef00)):
            with self.assertRaises((ValueError,EOFError)):protocol.receive(Fragmented(data))
    def test_long_strings(self):
        for n in (0,254,255,65535):
            wire=protocol.string('a'*n);self.assertEqual(protocol.read_string(wire),('a'*n,len(wire)))
    def test_recovered_property_packet(self):
        self.assertEqual(protocol.update(USER,146,1,2).hex(),'ffff01300020920001000000')

class RuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.assets=Assets(ROOT/'original')
    def setUp(self):
        self.g=Game(self.assets,seed=23,ai_sides=())
        self.g.blocked.clear();self.g.solid.clear();self.g.low.clear();self.g.windows.clear();self.g.trees.clear()
        for u in self.g.units:u.x=10+u.side*8;u.y=10+u.index*2;u.hold_fire=True
    def test_wall_and_corner_blocking(self):
        self.g.solid={(14,10)};self.g.blocked=set(self.g.solid)
        self.assertFalse(self.g.clear_line((10,10),(18,10)))
        self.g.solid={(11,10)};self.g.blocked={(11,10),(10,11)}
        self.assertFalse(self.g.clear_line((10,10),(12,12)))
        path=self.g.path((10,10),(12,12));self.assertNotEqual(path[0],(11,11))
        self.assertTrue(all(p not in self.g.blocked for p in path))
    def test_window_requires_standing(self):
        self.g.windows={(14,10)}
        self.assertTrue(self.g.clear_line((10,10),(18,10)))
        self.assertFalse(self.g.clear_line((10,10),(18,10),'prone'))
    def test_enemy_visibility_and_low_cover(self):
        u=self.g.units[4];self.g.solid={(14,y) for y in range(1,99)}
        self.assertFalse(self.g.visible(0,u));self.assertTrue(self.g.visible(1,u))
        self.g.solid.clear();self.g.low={(14,10)}
        self.assertTrue(self.g.clear_line((10,10),(18,10)))
        self.assertFalse(self.g.clear_line((10,10),(18,10),target_stance='prone'))
    def test_enemy_ownership_and_invalid_points(self):
        self.g.command(0,[0],'run',(20,20));self.assertTrue(self.g.units[0].path);self.assertFalse(self.g.units[4].path)
        old=list(self.g.units[0].path)
        self.g.command(0,[0],'run',(math.nan,20));self.assertEqual(self.g.units[0].path,old)
    def test_keep_formation(self):
        self.g.command(0,[0,1,2,3],'walk',(30,30))
        self.assertEqual([u.path[-1] for u in self.g.units[:4]],[(30,30),(30,32),(30,34),(30,36)])
    def test_distance_stress_and_movement_reduce_accuracy(self):
        a,b=self.g.units[0],self.g.units[4];base=self.g.hit_chance(a,b)
        a.stress=1;self.assertLess(self.g.hit_chance(a,b),base);a.stress=0
        a.path=[(11,10)];self.assertLess(self.g.hit_chance(a,b),base);a.path=[]
        b.x=30;self.assertLess(self.g.hit_chance(a,b),base)
    def test_empty_reload_uses_finite_ammunition(self):
        u=self.g.units[0];u.hold_fire=False;u.ammo=1;u.reserve=3;u.stress=1
        self.g.step(.1);self.assertEqual(u.ammo,0);self.assertGreater(u.reload,WEAPONS[u.weapon]['reload'])
        u.hold_fire=True
        for _ in range(80):self.g.step(.1)
        self.assertEqual((u.ammo,u.reserve),(3,0))
    def test_grenade_fuse_blast_and_smoke(self):
        self.g.command(0,[0],'grenade',(10,10))
        self.assertEqual(self.g.units[0].grenades,1)
        self.g.step(4.9);self.assertEqual(self.g.units[0].health,100)
        self.g.step(.11);self.assertEqual(self.g.units[0].health,0);self.assertGreater(self.g.units[0].stun,0)
        self.g.step(2)
        self.g.command(0,[1],'smoke',(14,12));self.g.step(5.01)
        self.assertFalse(self.g.clear_line((10,12),(18,12)))
    def test_carry_and_put_down(self):
        carrier,wounded=self.g.units[:2];wounded.state='WIA';wounded.health=0
        self.g.command(0,[0],'carry');self.assertEqual(carrier.carrying,wounded.uid)
        self.g.command(0,[0],'walk',(12,10));self.g.step(1)
        self.assertEqual(wounded.cell,carrier.cell)
        self.g.command(0,[0],'carry');self.assertEqual(wounded.carried_by,0)
    def test_ai_can_finish_a_match(self):
        g=Game(self.assets,ai_sides=(0,1),seed=2)
        for _ in range(4501):
            g.step(.2)
            if g.winner is not None:break
        self.assertIsNotNone(g.winner)
    def test_all_original_maps_load(self):
        self.assertEqual(len(self.assets.map_files),71)
        for name in self.assets.map_files:
            with self.subTest(map=name):
                g=Game(self.assets,name,seed=1)
                self.assertGreater(len(self.assets.model('Test',g,0)),1000)
    def test_existing_property_clear_encoding(self):
        self.assertEqual(self.assets.encode_properties(dict(type='PLAYER',properties={'World':0}),{},existing=True),b'\x61\0\0\xff\xff')

if __name__=='__main__':unittest.main()
