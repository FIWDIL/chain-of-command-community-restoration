"""Recovered fields govern inventory, blast reach and selected presentation."""
import copy
import queue
from pathlib import Path
import unittest
from unittest.mock import patch

from restoration.assets import Assets, EFFECT_BASE
from restoration.simulation import Game
from restoration.server import MatchServer
from test_native_feedback import RecordingPeer

ROOT = Path(__file__).resolve().parents[1]


class RecoveredRulesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets = Assets(ROOT / 'game')

    def test_inventory_and_equipment_use_recovered_ammunition_limits(self):
        game = Game(self.assets, ai_sides=())
        expected = {'Garand':70, 'Mauser':70, 'BAR':900, 'MG42':900, 'Thompson':200, 'MP40':200}
        for unit in game.units:
            self.assertEqual(unit.grenades, 5)
            for weapon, total in expected.items():
                game.equip(unit, weapon)
                self.assertEqual(unit.ammo + unit.reserve, total)

    def test_recovered_values_are_used_instead_of_duplicate_constants(self):
        assets = copy.copy(self.assets)
        assets.grenade_counts = (3, 4)
        assets.ammo_limits = dict.fromkeys(self.assets.ammo_limits, 3)
        assets.grenade_range = 2
        game = Game(assets, ai_sides=())
        unit = game.units[0]
        unit.x = unit.y = 10
        self.assertEqual((unit.ammo, unit.reserve, unit.grenades), (3, 0, 3))
        self.assertEqual(game.owned(1,0)[0].grenades, 4)
        game.command(0,[0],'grenade',(13,10))
        self.assertFalse(game.grenades)
        game.solid.clear();game.windows.clear()
        game.command(0,[0],'grenade',(12,10))
        self.assertEqual(len(game.grenades), 1)

    def test_five_throws_exhaust_inventory(self):
        game = Game(self.assets, ai_sides=())
        unit = game.units[0]
        for _ in range(6):
            game.command(0,[0],'grenade',unit.cell)
        self.assertEqual(unit.grenades, 0)
        self.assertEqual(len(game.grenades), 5)

    def test_blast_has_no_effect_at_or_outside_recovered_falloff_radius(self):
        game = Game(self.assets, ai_sides=())
        game.solid.clear();game.windows.clear();game.low.clear()
        for i,unit in enumerate(game.units):
            unit.x=30+i;unit.y=30;unit.hold_fire=True
        for unit,x in zip(game.units[:3],(11,12,13)):
            unit.x=x;unit.y=10
        game.grenades.append(dict(x=10,y=10,until=0,smoke=False,side=0))
        with patch.object(game.random,'random',return_value=0):
            game.step(.01)
        self.assertLess(game.units[0].health,100)
        for unit in game.units[1:3]:
            self.assertEqual((unit.health,unit.stun,unit.stress),(100,0,0))

    def test_native_grenade_effect_uses_imageshop_reference(self):
        server = MatchServer(self.assets,'AbbeyArden')
        server.game.blasts=[(20,20,2)]
        peer = RecordingPeer()
        session=dict(peer=peer,side=0,slot=0,selected=[0,1,2,3],action='walk',outgoing=queue.Queue())
        server.refresh(session,True,False)
        self.assertEqual(peer.values[EFFECT_BASE,61],self.assets.ref('img - grex action'))
        self.assertEqual(peer.values[EFFECT_BASE+1,61],self.assets.ref('img - exp2 action'))

    def test_original_hud_shows_total_ammunition_and_five_grenades(self):
        server = MatchServer(self.assets,'AbbeyArden')
        peer = RecordingPeer()
        session=dict(peer=peer,side=0,slot=0,selected=[0,1,2,3],action='walk',outgoing=queue.Queue())
        server.refresh(session,True,True)
        for unit in server.game.owned(0,0):
            n=str(unit.number+1)
            self.assertEqual(peer.values[self.assets.ref('_HG_UnitTile_ShowAmmo'+n),95],str(self.assets.ammo_limits[unit.weapon]))
            self.assertEqual(peer.values[self.assets.ref('_HG_UnitTile_AmGranade'+n),95],'5')

    def test_unitmaster_assignments_cover_crouch_throw_and_carry_idle(self):
        game = Game(self.assets, ai_sides=())
        for side,master_name in enumerate(('_hg_unitmaster_american','_hg_unitmaster_german')):
            unit=game.owned(side,0)[0]
            master=self.assets.objects[master_name]['properties']
            unit.stance='crouch'
            self.assertEqual(game.image(unit),master['UMImageKneel']['name'])
            unit.stance='prone';unit.animation='throw';unit.anim_until=1
            self.assertEqual(game.image(unit),master['UMImageLyThrowGr']['name'])
            unit.carrying=game.owned(side,0)[1].uid
            self.assertEqual(game.image(unit),master['UM_ImageWoundedCarringIdle']['name'])
            unit.path=[(20,20)]
            self.assertEqual(game.image(unit),master['UM_ImageWoundedCarring']['name'])
