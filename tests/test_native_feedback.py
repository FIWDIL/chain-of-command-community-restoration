"""Native presentation updates retain ownership and clean up transient feedback."""
from pathlib import Path
import unittest
from restoration.assets import Assets, DESTINATION_BASE, DESTINATION_EDGE_BASE, DESTINATION_FILL_BASE, DESTINATION_PIP_BASE
from restoration.server import MatchServer

ROOT=Path(__file__).resolve().parents[1]

class RecordingPeer:
    ready=True
    def __init__(self):self.values={}
    def update(self,uid,prop,value,datatype=1,force=False):self.values[uid,prop]=value

class NativeFeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.assets=Assets(ROOT/'game')
    def setUp(self):
        self.server=MatchServer(self.assets,'AbbeyArden',team_size=2)
        self.peer=RecordingPeer()
        self.session=dict(peer=self.peer,side=0,slot=0,selected=[0,1,2,3],action='walk')
    def refresh(self):self.server.refresh(self.session,True,False)
    def test_fractional_positions_and_friendly_head_pips(self):
        u=self.server.game.units[0];u.x+=3.25
        self.refresh()
        self.assertEqual(self.peer.values[u.uid,365],u.x)
        self.assertEqual(self.peer.values[u.uid,59],round(u.x))
        self.assertEqual(self.peer.values[u.uid,79],self.assets.ref('img - dot1 static'))
        other=self.server.game.owned(0,1)[0]
        self.assertEqual(self.peer.values[other.uid,79],0)
        self.assertEqual(self.peer.values[other.uid,80],0)
    def test_multiplayer_names_follow_owners_and_clear_offline(self):
        self.server.offline=False
        self.server.sessions={'a':dict(side=0,slot=0,name='Alice'),'b':dict(side=0,slot=1,name='Bob')}
        self.refresh()
        for u in self.server.game.owned(0,1):self.assertEqual(self.peer.values[u.uid,95],'\x01Bob')
        for u in self.server.game.owned(0,0):self.assertEqual(self.peer.values[u.uid,95],'')
        dead=self.server.game.owned(0,1)[0];dead.state='KIA';self.refresh()
        self.assertEqual(self.peer.values[dead.uid,95],'')
        dead.state='Retreated';self.refresh()
        self.assertEqual(self.peer.values[dead.uid,95],'')
        self.server.offline=True;self.refresh()
        for u in self.server.game.owned(0,1):self.assertEqual(self.peer.values[u.uid,95],'')
    def test_locomotion_advances_original_frames_and_stops_on_arrival(self):
        g=self.server.game
        for side in (0,1):
            u=g.owned(side,0)[0]
            for mode in ('walk','run','crawl'):
                u.mode=mode;u.path=[(30,40)];u.stance='prone' if mode=='crawl' else 'stand'
                frames=[]
                for t in (0,.2,.4):
                    g.time=t;frames.append(self.assets.unit_image(g,u))
                self.assertEqual(len(set(frames)),3)
                moving=g.image(u)
                u.path=[]
                self.assertNotIn(self.assets.unit_image(g,u),self.assets.motion_frames[moving])
    def test_keyboard_orders_are_ignored(self):
        self.server.handle(self.session,dict(type='key',key=82))
        self.assertEqual(self.session['action'],'walk')
        self.server.handle(self.session,dict(type='key',key=49))
        self.assertEqual(self.session['selected'],[0,1,2,3])
    def test_debrief_reports_casualties_and_opens_recovered_world_once(self):
        game=self.server.game;game.winner=0;game.owned(0,0)[1].state='WIA'
        self.refresh()
        self.assertEqual(self.peer.values[self.assets.ref('LEndGameVictory'),95],'Victory')
        self.assertEqual(self.peer.values[self.assets.ref('LEDSoldier2'),95],'Wounded')
        self.assertTrue(self.session['debrief_shown'])
        self.assertEqual(self.peer.values[0x20003001,145],self.assets.ref('EndGameScoring'))
    def test_destination_flashes_and_clears_on_arrival(self):
        g=self.server.game;u=g.owned(0,0)[0];u.path=[(30,40)]
        g.owned(0,1)[0].path=[(50,60)]
        self.refresh()
        self.assertEqual(self.peer.values[DESTINATION_BASE,59],30)
        self.assertEqual(self.peer.values[DESTINATION_BASE,60],40)
        self.assertEqual(self.peer.values[DESTINATION_EDGE_BASE,660],1)
        self.assertEqual(self.peer.values[DESTINATION_FILL_BASE,97],self.assets.world)
        self.assertEqual(self.peer.values[DESTINATION_FILL_BASE,60],40)
        self.assertEqual(self.peer.values[DESTINATION_FILL_BASE,660],5)
        self.assertEqual(self.peer.values[DESTINATION_PIP_BASE,660],9)
        self.assertEqual(self.peer.values[DESTINATION_PIP_BASE,59],30)
        g.time=.4;self.refresh()
        self.assertEqual(self.peer.values[DESTINATION_EDGE_BASE,660],0)
        self.assertEqual(self.peer.values[DESTINATION_FILL_BASE,97],0)
        self.assertEqual(self.peer.values[DESTINATION_FILL_BASE,660],0)
        self.assertEqual(self.peer.values[DESTINATION_PIP_BASE,97],self.assets.world)
        self.assertEqual(self.peer.values[self.assets.world,86],2)
        self.assertEqual(self.peer.values[DESTINATION_BASE,97],0)
        u.path=[];self.refresh()
        self.assertEqual(self.peer.values[DESTINATION_BASE,97],0)
        self.assertEqual(self.peer.values[DESTINATION_BASE,61],0)
        self.assertEqual(self.peer.values[DESTINATION_EDGE_BASE,97],0)
        self.assertEqual(self.peer.values[DESTINATION_PIP_BASE,97],0)
    def test_run_button_uses_pressed_art_and_releases(self):
        self.server.handle(self.session,dict(type='mouse',world='_HG_CommandDialog_Global',phase=0,button=1,x=100,y=22))
        self.refresh()
        button=self.assets.objects['interface_run']
        self.assertEqual(self.peer.values[button['uid'],61],button['properties']['ImagePressed']['ref'])
        self.server.handle(self.session,dict(type='mouse',world='World',phase=1,button=1,x=90,y=90))
        self.refresh()
        self.assertEqual(self.peer.values[button['uid'],61],button['properties']['ImageIdle']['ref'])

if __name__=='__main__':unittest.main()
