import json
import queue
import tempfile
import unittest
from pathlib import Path
from restoration.assets import Assets
from restoration.server import MatchServer


class RoomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets = Assets(Path(__file__).resolve().parents[1] / 'game')

    def setUp(self):
        self.server = MatchServer(self.assets, 'AbbeyArden', offline=False, team_size=3)
        self.host = self.member('host', 0, 0, True)
        self.ally = self.member('ally', 0, 1)
        self.enemy = self.member('enemy', 1, 0)

    def member(self, name, side, slot, owner=False):
        session = dict(username=name, name=name, side=side, slot=slot, owner=owner, peer=None,
                       outgoing=queue.Queue(maxsize=100), closed=__import__('threading').Event(), ignored=set(),
                       ready=False, lobby=True, selected=[0, 1, 2, 3], action='walk')
        self.server.sessions[name] = session
        return session

    def test_team_and_private_messages_are_not_leaked_to_other_players_or_history(self):
        self.server.room_chat(self.host, dict(text='team only', channel='team'))
        message = self.server.chat[-1]
        self.assertTrue(self.server.message_visible(self.ally, message))
        self.assertFalse(self.server.message_visible(self.enemy, message))
        late = self.member('late', 0, 2)
        self.assertFalse(self.server.message_visible(late, message))
        self.host['last_chat'] = 0
        self.server.room_chat(self.host, dict(text='private', channel='whisper', recipient='enemy'))
        private = self.server.chat[-1]
        self.assertFalse(self.server.message_visible(self.ally, private))
        self.assertTrue(self.server.message_visible(self.enemy, private))
        self.assertNotIn('audience', self.server.public_message(private))
        self.server.set_ignored(self.enemy, dict(player='host', ignored=True))
        self.assertFalse(self.server.message_visible(self.enemy, private))

    def test_finite_weapon_assignment_and_atomic_rejection(self):
        s = self.server
        # Move one existing MG between soldiers in the same fireteam.
        s.assign_weapons(self.host, dict(side=0, slot=0, weapons=['MG', 'Rifle', 'Rifle', 'Rifle']))
        self.assertEqual(s.game.owned(0, 0)[0].weapon, 'BAR')
        before = [(u.weapon, u.ammo, u.reserve) for u in s.game.units]
        s.assign_weapons(self.host, dict(side=0, slot=1, weapons=['MG', 'Rifle', 'Rifle', 'Rifle']))
        self.assertEqual(before, [(u.weapon, u.ammo, u.reserve) for u in s.game.units])
        s.assign_weapons(self.ally, dict(side=1, slot=0, weapons=['Rifle'] * 4))
        self.assertEqual(before, [(u.weapon, u.ammo, u.reserve) for u in s.game.units])
        s.started = True
        s.assign_weapons(self.host, dict(side=0, slot=0, weapons=['Rifle'] * 4))
        self.assertEqual(before, [(u.weapon, u.ammo, u.reserve) for u in s.game.units])

    def test_command_hierarchy_rejects_cycles_and_scopes_equipment_authority(self):
        s = self.server
        s.set_commander(self.host, dict(side=0, slot=2, commander=1))
        self.assertTrue(s.controls_slot(self.ally, 0, 2))
        self.assertFalse(s.controls_slot(self.ally, 0, 0))
        self.assertFalse(s.controls_slot(self.ally, 1, 2))
        s.set_commander(self.host, dict(side=0, slot=0, commander=2))
        self.assertIsNone(s.commanders[0, 0])
        s.set_commander(self.ally, dict(side=0, slot=0, commander=1))
        self.assertIsNone(s.commanders[0, 0])

    def test_return_to_lobby_preserves_players_chat_and_loadouts_resets_casualties(self):
        s = self.server
        s.assign_weapons(self.host, dict(side=0, slot=0, weapons=['MG', 'Rifle', 'Rifle', 'Rifle']))
        s.add_message('host', 'keep this message')
        soldier = s.game.owned(0, 0)[0]
        soldier.state = 'KIA'; soldier.ammo = 0
        s.game.winner = 0; s.started = True
        s.return_lobby(self.enemy)
        self.assertEqual(s.game.winner, 0)
        s.return_lobby(self.host)
        self.assertIsNone(s.game.winner)
        self.assertFalse(s.started)
        self.assertEqual(set(s.sessions), {'host', 'ally', 'enemy'})
        self.assertTrue(any(e['text'] == 'keep this message' for e in s.chat))
        self.assertEqual(s.game.owned(0, 0)[0].weapon, 'BAR')
        self.assertEqual(s.game.owned(0, 0)[0].state, 'ready')
        self.assertGreater(s.game.owned(0, 0)[0].ammo, 0)
        self.assertTrue(all(member['lobby'] and not member['ready'] for member in s.sessions.values()))

    def test_saved_results_contain_actual_outcomes_without_invented_points(self):
        with tempfile.TemporaryDirectory() as directory:
            self.server.state_dir = Path(directory)
            self.server.game.winner = -1
            self.server.record_result()
            records = json.loads((Path(directory) / 'match-history.json').read_text())
            self.assertEqual(records[0]['winner'], -1)
            self.assertEqual(len(records[0]['soldiers']), 24)
            self.assertNotIn('promotion_points', records[0])


if __name__ == '__main__':
    unittest.main()
