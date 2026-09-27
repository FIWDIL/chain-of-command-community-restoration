import unittest
from pathlib import Path
from restoration.assets import Assets, OBJECTIVE_FLOOR, OBJECTIVE_FLAG
from restoration.simulation import Game
from restoration.server import MatchServer
from test_native_feedback import RecordingPeer

class CaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets=Assets(Path(__file__).resolve().parents[1]/'game')

    def setUp(self):
        self.g=Game(self.assets,ai_sides=())
        self.g.objective=(50,50)
        for u in self.g.units:u.x=10+u.index;u.y=10+u.side*70;u.hold_fire=True
        self.a=self.g.units[0];self.b=self.g.owned(1,0)[0]

    def occupy(self,u):u.x=u.y=50

    def test_exact_duration_and_no_capture_victory(self):
        self.occupy(self.a)
        self.g.update_capture(119.9)
        self.assertIsNone(self.g.capture_owner)
        self.assertIn('00:01',self.g.capture_status())
        self.g.update_capture(.1)
        self.assertEqual(self.g.capture_owner,0)
        self.assertIsNone(self.g.winner)

    def test_one_square_and_casualties_do_not_capture(self):
        self.a.x=50.5;self.a.y=50
        self.g.update_capture(120)
        self.assertIsNone(self.g.capture_owner)
        self.occupy(self.a);self.a.state='WIA'
        self.g.update_capture(120)
        self.assertIsNone(self.g.capture_owner)
        self.a.state='ready';self.a.x=50.49
        self.g.update_capture(120)
        self.assertEqual(self.g.capture_owner,0)

    def test_contested_pauses_and_leaving_resets(self):
        self.occupy(self.a);self.g.update_capture(30)
        self.occupy(self.b);self.g.update_capture(90)
        self.assertEqual(self.g.capture_elapsed,30)
        self.assertIn('Contested',self.g.capture_status())
        self.b.x=60;self.g.update_capture(10)
        self.assertEqual(self.g.capture_elapsed,40)
        self.a.x=60;self.g.update_capture(1)
        self.assertEqual(self.g.capture_elapsed,0)
        self.assertIsNone(self.g.capture_side)

    def test_recapture_requires_full_timer_and_preserves_owner_until_complete(self):
        self.occupy(self.a);self.g.update_capture(120)
        self.a.x=60;self.occupy(self.b);self.g.update_capture(119)
        self.assertEqual(self.g.capture_owner,0)
        self.g.update_capture(1)
        self.assertEqual(self.g.capture_owner,1)

    def test_native_images_follow_owner_for_every_client(self):
        server=MatchServer(self.assets,'fort',offline=True)
        peer=RecordingPeer()
        session=dict(peer=peer,side=0,slot=0,selected=[0,1,2,3],action='walk')
        for side in (None,0,1):
            server.game.capture_owner=side
            server.refresh(session,True,False)
            self.assertEqual(peer.values[(OBJECTIVE_FLOOR,61)],self.assets.capture_floor_image(side))
            self.assertEqual(peer.values[(OBJECTIVE_FLAG,61)],0 if side is None else self.assets.capture_flags[side])
            self.assertEqual(peer.values[(OBJECTIVE_FLOOR,660)],13 if side is None else 0)
        self.assertEqual(self.assets.capture_images,(self.assets.ref('img - attl static'),self.assets.ref('img - gttl static')))
        self.assertEqual(self.assets.capture_flags,(self.assets.ref('img - actl static'),self.assets.ref('img - gctl static')))
