import math
from pathlib import Path
import unittest
from restoration.assets import Assets
from restoration.simulation import Game

class TacticalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.assets=Assets(Path(__file__).resolve().parents[1]/'game')
    def setUp(self):
        self.g=Game(self.assets,ai_sides=(0,),seed=9)
        self.g.blocked.clear();self.g.solid.clear();self.g.windows.clear();self.g.low.clear();self.g.trees.clear()
        self.g.objective=(32,12)
        for u in self.g.units:
            u.x=10 if u.side==0 else 23;u.y=8+u.number*3
        self.group=self.g.owned(0,0)
    def test_fire_and_movement_and_role_rotation(self):
        g=self.g;g.think()
        supports=[u for u in self.group if u.ai_role=='Covering fire']
        movers=[u for u in self.group if u.path]
        self.assertEqual(len(supports),2);self.assertEqual(len(movers),2)
        self.assertTrue(all(u.stance=='prone' for u in supports))
        self.assertGreater(math.dist(movers[0].path[-1],movers[1].path[-1]),1.5)
        for u in g.units:u.health=10000
        g.step(.1)
        self.assertTrue(any(u.ammo<8 for u in supports if u.weapon=='Garand'))
        self.assertTrue(any(u.stress>0 for u in g.units if u.side==1))
        before={u.uid for u in supports}
        g.time=10
        for u in self.group:u.path=[];u.ai_until=0
        g.think()
        self.assertNotEqual(before,{u.uid for u in self.group if u.ai_role=='Covering fire'})
    def test_cover_is_directional_and_endpoints_reserved(self):
        g=self.g;u=self.group[0];threat=(23,8)
        g.low={(14,y) for y in range(4,20)}
        p,route=g.tactics.choose_position(u,(25,8),threat,support=True)
        self.assertTrue(route);self.assertGreater(g.tactics.protection(p,threat),0)
        u.path=route
        other=self.group[1];q,_=g.tactics.choose_position(other,(25,11),threat,support=True)
        self.assertGreaterEqual(math.dist(p,q),1.5)
        self.assertEqual(g.tactics.protection((16,8),threat),0)
    def test_smoke_waits_for_fuse_and_uses_one_inventory_item(self):
        g=self.g
        for u in self.group:u.reload=8
        g.think()
        self.assertEqual(len(g.grenades),1)
        self.assertEqual(sum(u.smoke for u in self.group),3)
        self.assertTrue(all(not u.path and u.ai_role=='Wait for smoke' for u in self.group))
        for _ in range(24):g.step(.2)
        self.assertFalse(g.smokes);self.assertEqual(len(g.grenades),1)
        g.step(.21)
        self.assertTrue(g.smokes)
        g.time=6;g.think()
        self.assertTrue(any(u.path for u in self.group))
        self.assertEqual(sum(u.smoke for u in self.group),3)
    def test_hidden_contact_is_not_tracked_and_memory_expires(self):
        g=self.g;g.think();remembered=self.group[0].ai_contact
        g.solid={(15,y) for y in range(1,99)};g.blocked=set(g.solid)
        for u in g.units:
            if u.side==1:u.x=70
        g.time=2;g.think()
        self.assertEqual(self.group[0].ai_contact,remembered)
        self.assertLessEqual(self.group[0].ai_contact_until,12)
        g.time=15;g.think()
        self.assertTrue(all(u.ai_contact_until<g.time for u in self.group))
    def test_human_orders_not_changed(self):
        g=self.g;g.ai_slots.clear();g.command(0,[0],'run',(8,30))
        original=list(self.group[0].path);g.think()
        self.assertEqual(original,self.group[0].path)
    def test_gunner_is_used_then_can_bound(self):
        g=self.g;gunner=self.group[3];gunner.weapon='BAR';gunner.ammo=20
        g.think();self.assertEqual(gunner.ai_role,'Covering fire')
        g.time=10
        for u in self.group:u.path=[];u.ai_until=0
        g.think();self.assertNotEqual(gunner.ai_role,'Covering fire')
    def test_high_stress_seeks_shelter(self):
        g=self.g;u=self.group[0];u.stress=.9
        g.solid={(12,y) for y in range(5,10)};g.blocked=set(g.solid)
        # Other fireteam members can still report the contact around the wall.
        g.think()
        self.assertIn(u.ai_role,('Seek cover','Covering fire','Wait for smoke','Advance under cover'))
        if u.ai_role=='Seek cover':self.assertEqual(u.mode,'crawl')

if __name__=='__main__':unittest.main()
