import unittest
from pathlib import Path
from restoration.assets import Assets, DEPLOYMENT_BASE
from restoration.simulation import Game
from restoration import presentation
from restoration.server import MatchServer
from test_native_feedback import RecordingPeer


class AssetRestorationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets=Assets(Path(__file__).resolve().parents[1]/'game')

    def setUp(self):
        self.game=Game(self.assets,'fort',ai_sides=())
        self.unit=self.game.units[0]
        self.unit.hold_fire=True

    def test_complete_archive_catalog_and_variant_selection(self):
        self.assertEqual(len(self.assets.map_files),81)
        self.assertEqual(len(self.assets.missions),153)
        for name in ('Remagen','StoneHouse / Alternate layout','fort / Mission 2'):
            terrain,scenario=self.assets.read_map(name)
            self.assertTrue(terrain)
        self.assertNotEqual(self.assets.read_map('fort')[1],self.assets.read_map('fort / Mission 2')[1])
        for obj in self.assets.read_map('germhq')[0]:
            p=obj['properties']
            self.assertNotIn(p.get('terrain'),('_HG_Evan','_Evan','_HG_NEvan'))
            self.assertNotEqual(p.get('World'),'Worlds')

    def test_stance_transition_advances_frames_then_settles(self):
        g,u=self.game,self.unit
        g.command(0,[0],'prone')
        self.assertEqual(g.image(u),self.assets.unit_master(0)['UMImageStand-Kneel']['name'])
        first=self.assets.unit_image(g,u)
        g.time=.11
        self.assertNotEqual(first,self.assets.unit_image(g,u))
        g.time=max(5,u.visual_sequence[-1][1]+1)
        self.assertEqual(g.image(u),self.assets.unit_master(0)['UMImageProneIdle']['name'])

    def test_cover_states_use_original_left_right_prone_and_barrel_clips(self):
        g,u=self.game,self.unit
        for side in (0,1):
            u=g.owned(side,0)[0]
            for stance in ('stand','prone'):
                u.stance=stance
                for cover in ('left','right','barrel_left','barrel_right','barrel_front'):
                    u.visual_cover=cover
                    for action in ('idle','aim','fire'):
                        name=presentation.cover_field(u,action)
                        self.assertIn(name,self.assets.unit_master(side))
                        image=self.assets.unit_master(side)[name]['name'].casefold()
                        self.assertIn('mag 8',self.assets.objects[image]['properties'])

    def test_casualties_have_visible_art_and_emit_sound_without_changing_damage(self):
        g,u=self.game,self.unit
        g.hurt(u,200)
        self.assertIn(('scream',u.uid),g.events)
        self.assertEqual(u.health,0)
        g.time=u.visual_sequence[-1][1]+1
        self.assertIn('mag 8',self.assets.objects[g.image(u)]['properties'])
        u.state='KIA';g.winner=1
        self.assertIn('mag 8',self.assets.objects[g.image(u)]['properties'])

    def test_every_recovered_animated_unit_image_has_clock_driven_frames(self):
        for side in (0,1):
            for value in self.assets.unit_master(side).values():
                if not isinstance(value,dict) or not value.get('name','').startswith('img - '):continue
                name=value['name'].casefold()
                if self.assets.animation_lengths.get(name,0)>1:
                    self.assertEqual(len(self.assets.motion_frames[name]),self.assets.animation_lengths[name])
        ids=[o['uid'] for o in self.assets.motion_objects]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertLess(max(ids),0x20010000)

    def test_extra_objectives_capture_independently_and_deployment_is_owned(self):
        g=self.game
        self.assertTrue(g.extra_objectives)
        point=g.extra_objectives[0]
        for u in g.units:u.x,u.y=10+u.index,20+u.side*50
        u=g.units[0];u.x,u.y=point.objective
        g.update_capture(120)
        self.assertEqual(point.capture_owner,0)
        self.assertIsNone(g.capture_owner)
        server=MatchServer(self.assets,'fort',offline=True)
        peer=RecordingPeer()
        session=dict(peer=peer,side=0,slot=0,selected=[0,1,2,3],action='walk',deployment=True)
        server.refresh(session,True,False)
        for i,(owner,*_) in enumerate(server.game.deployment):
            self.assertEqual(peer.values[DEPLOYMENT_BASE+i,97],self.assets.world if owner==0 else 0)

    def test_hidden_play_again_does_not_intercept_rotation(self):
        self.assertEqual(self.assets.hud_action(255,5,False)[0],'Rotate Left')
        self.assertEqual(self.assets.hud_action(255,5,True)[0],'Play Again')


if __name__=='__main__':unittest.main()
