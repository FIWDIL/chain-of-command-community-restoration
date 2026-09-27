"""Room continuity, finite equipment and social features for the restored service.

These interactions are reconstructions. They do not manufacture original ranks,
promotion points, authentication records, or combat formulas.
"""
import json
import time
from pathlib import Path
from .roster import weapon_caps
from .simulation import Game


class RoomFeatures:
    def init_room(self, state_dir=None):
        self.round_number = 1
        self.commanders = {(side, slot): (None if slot == 0 else 0)
                           for side in (0, 1) for slot in range(self.game.team_size)}
        self.state_dir = Path(state_dir) if state_dir else None
        self.completed_rounds = []
        self.launch_deadline = 0

    def notice(self, session, text):
        self.emit(session, {'type': 'notice', 'text': text})

    def message_visible(self, session, event):
        if event.get('author') in session.get('ignored', set()):
            return False
        audience = event.get('audience')
        return audience is None or session['username'] in audience

    @staticmethod
    def public_message(event):
        return {k: v for k, v in event.items() if k not in ('audience', 'author')}

    def room_chat(self, session, event):
        text = self.clean_text(event.get('text'), 240)
        channel = event.get('channel', 'room')
        if not text or time.monotonic() - session.get('last_chat', 0) < .5:
            return
        audience = None
        label = 'Room'
        if channel == 'team':
            audience = [s['username'] for s in self.sessions.values() if s['side'] == session['side']]
            label = 'Team'
        elif channel == 'whisper':
            recipient = self.sessions.get(event.get('recipient')) if isinstance(event.get('recipient'), str) else None
            if not recipient:
                self.notice(session, 'That player is no longer in the room.')
                return
            audience = [session['username'], recipient['username']]
            label = 'Private to ' + recipient['name']
        elif channel != 'room':
            return
        session['last_chat'] = time.monotonic()
        self.chat_sequence += 1
        message = dict(type='chat', id=self.chat_sequence, sender=session['name'],
                       text=text, channel=label, author=session['username'], audience=audience)
        self.chat.append(message)
        for member in self.sessions.values():
            if self.message_visible(member, message):
                try:
                    self.emit(member, self.public_message(message))
                except OSError:
                    pass

    def set_ignored(self, session, event):
        target = event.get('player')
        if not isinstance(target, str) or target == session['username']:
            return
        ignored = session.setdefault('ignored', set())
        if event.get('ignored') is True and target in self.sessions:
            ignored.add(target)
        elif event.get('ignored') is False:
            ignored.discard(target)

    def controls_slot(self, session, side, slot):
        if session['owner']:
            return True
        if side != session['side']:
            return False
        seen = set()
        while slot is not None and slot not in seen:
            if slot == session['slot']:
                return True
            seen.add(slot)
            slot = self.commanders.get((side, slot))
        return False

    def set_commander(self, session, event):
        side, slot, commander = event.get('side'), event.get('slot'), event.get('commander')
        if not session['owner'] or self.started or self.launching:
            self.notice(session, 'The host assigns commanders before the match.')
            return
        if type(side) is not int or side not in (0, 1) or type(slot) is not int or not 0 <= slot < self.game.team_size:
            return
        if commander is not None and (type(commander) is not int or not 0 <= commander < self.game.team_size):
            return
        ancestor = commander
        while ancestor is not None:
            if ancestor == slot:
                self.notice(session, 'A fireteam cannot report to itself or one of its subordinates.')
                return
            ancestor = self.commanders.get((side, ancestor))
        self.commanders[side, slot] = commander
        self.add_message('System', f"{'USA' if side == 0 else 'Germany'} fireteam {slot + 1}: " +
                         ('mission commander' if commander is None else f'reports to fireteam {commander + 1}.'))

    def assign_weapons(self, session, event):
        side, slot, requested = event.get('side'), event.get('slot'), event.get('weapons')
        if self.started or self.launching:
            self.notice(session, 'Equipment can be assigned before the match starts.')
            return
        if type(side) is not int or side not in (0, 1) or type(slot) is not int or not 0 <= slot < self.game.team_size:
            return
        if not self.controls_slot(session, side, slot):
            self.notice(session, 'You can equip your fireteam and its subordinates.')
            return
        if not isinstance(requested, list) or len(requested) != 4 or any(w not in ('Rifle', 'MG', 'SMG') for w in requested):
            return
        caps = weapon_caps(self.assets, side)
        for kind in caps:
            if requested.count(kind) > caps[kind]:
                self.notice(session, f'Each fireteam can carry at most {caps[kind]} {kind}.')
                return
        names = dict(zip(('Rifle', 'MG', 'SMG'), ('Garand', 'BAR', 'Thompson') if side == 0 else ('Mauser', 'MG42', 'MP40')))
        others = [u for u in self.game.units if u.side == side and u.slot != slot]
        for kind in caps:
            if sum(u.weapon == names[kind] for u in others) + requested.count(kind) > self.game.pool[kind]:
                self.notice(session, f'No spare {kind} on this side. Return one from another fireteam first.')
                return
        for unit, kind in zip(self.game.owned(side, slot), requested):
            self.game.equip(unit, names[kind])
        for member in self.sessions.values():
            member['ready'] = False
        self.notice(session, 'Equipment assigned.')

    def set_map(self, session, event):
        name = event.get('map')
        if not session['owner'] or self.started or self.launching or not isinstance(name, str) or name not in self.assets.missions:
            return
        self.new_round(name, announce=False)

    def return_lobby(self, session):
        if not session['owner']:
            self.notice(session, 'Only the host can return the room to the lobby.')
            return
        if self.game.winner is None and not self.launching and any(s.get('peer') and s['peer'].ready for s in self.sessions.values()):
            self.notice(session, 'Finish the current match before starting another.')
            return
        self.new_round(self.game.map_name)

    def new_round(self, map_name, announce=True):
        previous = {(u.side, u.index): u.weapon for u in self.game.units}
        game = Game(self.assets, map_name, ai_sides=(0, 1), team_size=self.game.team_size, pool=self.game.pool)
        for unit in game.units:
            game.equip(unit, previous[unit.side, unit.index])
        self.game = game
        self.started = False
        self.launching = False
        self.result_announced = False
        self.round_number += 1
        for member in self.sessions.values():
            old = member.get('peer')
            member.update(peer=None, ready=False, lobby=True, debrief_shown=False,
                          selected=[0, 1, 2, 3], action='walk', down=None, pressed_button=None)
            self.emit(member, {'type': 'return_lobby', 'round': self.round_number, 'map': map_name})
            if old:
                old.ready = False
                try:
                    old.stream.shutdown(2)
                except OSError:
                    pass
        if announce:
            self.add_message('System', 'Back in the lobby. Choose a map and prepare for the next match.')

    def record_result(self):
        record = dict(round=self.round_number, map=self.game.map_name, duration=round(self.game.time, 1),
                      winner=self.game.winner, players=[dict(name=s['name'], side=s['side'], slot=s['slot']) for s in self.sessions.values()],
                      soldiers=[dict(side=u.side, fireteam=u.slot + 1, soldier=u.number + 1, state=u.state,
                                     weapon=u.weapon, ammo=u.ammo, reserve=u.reserve) for u in self.game.units])
        self.completed_rounds.append(record)
        self.completed_rounds = self.completed_rounds[-100:]
        for session in self.sessions.values():
            self.emit(session, {'type': 'result', 'record': record})
        if self.state_dir:
            try:
                self.state_dir.mkdir(parents=True, exist_ok=True)
                target = self.state_dir / 'match-history.json'
                history = json.loads(target.read_text(encoding='utf-8')) if target.is_file() else []
                if not isinstance(history, list):
                    history = []
                temporary = target.with_suffix('.tmp')
                temporary.write_text(json.dumps((history + [record])[-100:], indent=2), encoding='utf-8')
                temporary.replace(target)
            except (OSError, ValueError):
                self.add_message('System', 'The match finished, but its history could not be saved.')
