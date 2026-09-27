"""Authoritative local/direct-connect match service for the recovered native client."""
import json
import queue
import secrets
import socket
import threading
import time
from collections import deque
from . import protocol
from .assets import USER, STATUS, OBJECTIVE, OBJECTIVE_FLOOR, OBJECTIVE_FLAG, EFFECT_BASE, EFFECT_COUNT, SMOKE_IMAGE, DESTINATION_BASE, DESTINATION_EDGE_BASE, DESTINATION_FILL_BASE, DESTINATION_PIP_BASE
from .simulation import Game
from .roster import MAX_SLOTS
from .room import RoomFeatures

GAME_PORT=1850
CONTROL_PORT=1851
CONTROL_VERSION=3

class Peer:
    def __init__(self, stream):
        self.stream=stream;self.sequence=0;self.lock=threading.Lock();self.cache={};self.ready=False
        self.batch=None;self.outgoing=queue.Queue(maxsize=16);self.streaming=False
    def send(self,kind,data=b''):
        with self.lock:
            self.sequence+=1;packet=protocol.frame(self.sequence,kind,data)
            if self.batch is not None:self.batch.append(packet)
            elif self.streaming:
                try:self.outgoing.put_nowait(packet)
                except queue.Full:raise OSError('Client cannot keep up with the match')
            else:self.stream.sendall(packet)
    def update(self,uid,prop,value,datatype=1,force=False):
        key=(uid,prop)
        if force or self.cache.get(key)!=value:
            self.send(8,protocol.update(uid,prop,value,datatype));self.cache[key]=value

    def flush(self):
        packet=b''.join(self.batch);self.batch=None
        try:self.outgoing.put_nowait(packet)
        except queue.Full:raise OSError('Client cannot keep up with the match')

    def write(self,stop):
        try:
            while not stop.is_set() and self.ready:
                try:packet=self.outgoing.get(timeout=.5)
                except queue.Empty:continue
                self.stream.sendall(packet)
        except OSError:
            self.ready=False
            try:self.stream.shutdown(socket.SHUT_RDWR)
            except OSError:pass

class MatchServer(RoomFeatures):
    def __init__(self,assets,map_name,offline=True,bind=None,password='',game_port=GAME_PORT,control_port=CONTROL_PORT,team_size=1,pool=None,state_dir=None):
        self.assets=assets;self.offline=offline;self.bind=bind or ('127.0.0.1' if offline else '0.0.0.0')
        self.password=password;self.game_port=game_port;self.control_port=control_port
        self.game=Game(assets,map_name,ai_sides=(0,1),team_size=team_size,pool=pool)
        self.owner_token=secrets.token_hex(24);self.started=offline
        self.sessions={};self.lock=threading.RLock();self.stop_event=threading.Event();self.sockets=[];self.threads=[]
        self.pending=queue.Queue(maxsize=1024);self.errors=[]
        self.launching=False;self.chat=deque(maxlen=100);self.chat_sequence=0;self.player_sequence=0
        self.result_announced=False
        self.init_room(state_dir)

    def start(self):
        try:
            for port,handler in ((self.game_port,self.native),(self.control_port,self.control)):
                s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1) if hasattr(socket,'SO_EXCLUSIVEADDRUSE') else None
                s.bind((self.bind,port));s.listen(32);s.settimeout(.5);self.sockets.append(s)
                if handler==self.native:self.game_port=s.getsockname()[1]
                else:self.control_port=s.getsockname()[1]
                self.thread(self.accept,s,handler)
            self.thread(self.loop)
        except Exception:self.close();raise

    def thread(self,fn,*args):
        t=threading.Thread(target=fn,args=args,daemon=True);self.threads.append(t);t.start()

    def accept(self,s,handler):
        while not self.stop_event.is_set():
            try:c,addr=s.accept()
            except socket.timeout:continue
            except OSError:return
            # Cap concurrent unauthenticated sockets as well as player slots.
            with self.lock:
                live=sum(t.is_alive() for t in self.threads)
                self.threads=[t for t in self.threads if t.is_alive()]
            if live>MAX_SLOTS*8+12:c.close();continue
            c.settimeout(10);self.thread(handler,c,addr)

    @staticmethod
    def json_send(stream,value):stream.sendall((json.dumps(value,separators=(',',':'))+'\n').encode())

    @staticmethod
    def emit(session,value):
        try:session['outgoing'].put_nowait(value)
        except queue.Full:raise OSError('Slow control connection')

    def control_writer(self,session):
        try:
            while not self.stop_event.is_set() and not session['closed'].is_set():
                try:value=session['outgoing'].get(timeout=.5)
                except queue.Empty:continue
                self.json_send(session['control'],value)
        except OSError:
            try:session['control'].shutdown(socket.SHUT_RDWR)
            except OSError:pass

    def allocate(self,hello):
        used={(s['side'],s['slot']) for s in self.sessions.values()}
        owner=secrets.compare_digest(str(hello.get('owner_token','')),self.owner_token)
        if self.offline:
            choices=[(0,0)] if (0,0) not in used else []
        else:
            side=hello.get('side','auto')
            if side not in ('auto',0,1):raise ValueError('Choose USA, Germany, or Auto')
            sides=(0,1) if side=='auto' else (side,)
            # Reserve the first USA slot only until the host has joined.
            reserve=not owner and not any(s['owner'] for s in self.sessions.values())
            choices=[(s,slot) for slot in range(self.game.team_size) for s in sides if (s,slot) not in used and (not reserve or (s,slot)!=(0,0))]
            if side=='auto':choices.sort(key=lambda choice:(sum(s==choice[0] for s,_ in used),choice[1],choice[0]))
        if not choices:raise ValueError('The selected side is full; try the other side or Auto')
        return *choices[0],owner or self.offline

    def control(self,c,addr):
        username=None;session=None
        try:
            with c, c.makefile('rb') as reader:
                line=reader.readline(4097)
                if len(line)>4096:raise ValueError('Message too long')
                hello=json.loads(line)
                if not isinstance(hello,dict):return
                if hello.get('version')!=CONTROL_VERSION or not secrets.compare_digest(str(hello.get('password','')),self.password):
                    self.json_send(c,{'error':'Wrong room password or incompatible launcher'});return
                with self.lock:
                    try:side,slot,owner=self.allocate(hello)
                    except ValueError as exc:self.json_send(c,{'error':str(exc)});return
                    username='Local'+secrets.token_hex(8)
                    self.player_sequence+=1
                    name=self.clean_text(hello.get('name',''),24) or ('Host' if owner else f'Player {self.player_sequence}')
                    if any(s.get('name')==name for s in self.sessions.values()):name=f'{name[:18]} {self.player_sequence}'
                    session=dict(side=side,slot=slot,owner=owner,ip=addr[0],peer=None,selected=[0,1,2,3],action='walk',down=None,control=c,
                                 outgoing=queue.Queue(maxsize=32),closed=threading.Event(),name=name,username=username,
                                 lobby=hello.get('lobby') is True,ready=False,last_chat=0,ignored=set())
                    self.sessions[username]=session
                    self.json_send(c,dict(username=username,side=side,slot=slot,owner=owner,map=self.game.map_name,port=self.game_port,
                                          team_size=self.game.team_size,pool=self.game.pool,name=name))
                    self.thread(self.control_writer,session)
                    history=[self.public_message(e) for e in self.chat if self.message_visible(session,e)]
                    # Keep each JSON line below the client's limit even with escaped Unicode.
                    for offset in range(0,max(1,len(history)),4):
                        self.emit(session,{'type':'chat_history','messages':history[offset:offset+4],'append':offset>0})
                    self.add_message('System',f"{name} joined the {'match' if self.offline else 'lobby'}.")
                    if (self.started or self.launching) and session['lobby']:self.emit(session,{'type':'launch'})
                c.settimeout(60);window=time.monotonic();count=0
                while not self.stop_event.is_set():
                    line=reader.readline(4097)
                    if not line:break
                    if len(line)>4096:raise ValueError('Message too long')
                    event=json.loads(line)
                    if not isinstance(event,dict) or not isinstance(event.get('type'),str):continue
                    now=time.monotonic()
                    if now-window>=1:window=now;count=0
                    count+=1
                    if count>120:continue
                    if event.get('type')=='ping':continue
                    try:self.pending.put_nowait((username,event))
                    except queue.Full:pass
        except (OSError,ValueError,TypeError):pass
        finally:
            with self.lock:
                session=self.sessions.pop(username,None)
                if session:session['closed'].set()
                if session:self.add_message('System',f"{session['name']} left the lobby.")
                if session and session['peer']:
                    try:session['peer'].stream.shutdown(socket.SHUT_RDWR)
                    except OSError:pass

    def native(self,c,addr):
        session=None;peer=Peer(c)
        try:
            with c:
                peer.send(0)
                for _ in range(20):
                    kind,data=protocol.receive(c)
                    if kind==1:break
                else:raise ValueError('No client version')
                peer.send(2,protocol.version_request())
                for _ in range(20):
                    kind,data=protocol.receive(c)
                    if kind==3:break
                else:raise ValueError('No client authentication')
                username,_=protocol.read_string(data)
                with self.lock:
                    session=self.sessions.get(username)
                    if not session or session['ip']!=addr[0] or session['peer']:raise ValueError('Unrecognized local client')
                    session['peer']=peer;side=session['side'];model=self.assets.model(username,self.game,side,session['slot'],self.player_names())
                peer.send(4,model)
                while True:
                    kind,data=protocol.receive(c)
                    if kind==13:break
                peer.send(5)
                # Open both native views; the bridge docks the command strip at the bottom.
                peer.update(USER,145,self.assets.hud,4,True);peer.update(USER,146,1,2,True)
                time.sleep(.25)
                peer.update(USER,146,0,2,True);peer.update(USER,145,self.assets.world,4,True);peer.update(USER,146,1,2,True)
                time.sleep(1.5)
                spawn=self.game.owned(side,session['slot'])[0].cell
                peer.update(self.assets.world,101,spawn[0],force=True);peer.update(self.assets.world,102,spawn[1],force=True)
                session['recenter_at']=time.monotonic()+2
                with self.lock:
                    peer.streaming=True;peer.ready=True;self.thread(peer.write,self.stop_event)
                    # Taking over an AI slot keeps injuries and ammunition, but clears old AI orders.
                    for unit in self.game.owned(side,session['slot']):unit.path=[];unit.target=0
                c.settimeout(90)
                while not self.stop_event.is_set():protocol.receive(c)
        except (OSError,EOFError,ValueError,IndexError) as exc:
            if not self.stop_event.is_set():self.errors.append(str(exc))
        finally:
            peer.ready=False
            with self.lock:
                if session and session['peer'] is peer:session['peer']=None

    def handle(self,session,event):
        side=session['side'];kind=event.get('type');peer=session['peer']
        if kind=='chat':
            self.room_chat(session,event);return
        if kind=='ignore':self.set_ignored(session,event);return
        if kind=='equipment':self.assign_weapons(session,event);return
        if kind=='commander':self.set_commander(session,event);return
        if kind=='map':self.set_map(session,event);return
        if kind=='command' and event.get('action')=='lobby':self.return_lobby(session);return
        if kind=='side':
            self.change_side(session,event.get('side'));return
        if kind=='command' and event.get('action')=='start':
            if session.get('lobby'):
                if self.started or self.launching:return
                session['ready']=True
                if session['owner']:
                    self.launching=True;self.launch_deadline=time.monotonic()+45
                    self.add_message('System','The host started the match. Loading battlefield...')
                    for member in self.sessions.values():self.emit(member,{'type':'launch'})
                return
            if session['owner']:
                if all(s['peer'] and s['peer'].ready for s in self.sessions.values()):self.started=True
                else:self.game.notices[side]='Wait for connected players to finish loading'
            return
        if not peer or not peer.ready:return
        if kind=='mouse':
            x=event.get('x');y=event.get('y');phase=event.get('phase');button=event.get('button');world=event.get('world','')
            if type(x) is not int or type(y) is not int or not (-32768<=x<=32767 and -32768<=y<=32767):return
            modifiers=event.get('modifiers',0)
            if type(modifiers) is not int:return
            if button==1 and phase==1:
                session['pressed_button']=None
            if world=='_HG_CommandDialog_Global' and button==1:
                hit=self.assets.hud_action(x,y)
                if phase==0:
                    session['pressed_button']=hit[0] if hit else None
                    return
                if phase!=1:return
                session['pressed_button']=None
                if not hit:return
                name,row=hit
                session['clicked_button']=name;session['clicked_until']=time.monotonic()+.2
                session['selected']=[row-1] if row else [0,1,2,3]
                base=name.rstrip('1234')
                action={'Interface_WalkTo':'walk','Interface_Run':'run','Interface_CrawlTo':'crawl','Interface_Assault':'assault',
                        'Interface_FireAt':'fire','Interface_Face':'face','Interface_ThrowGranade':'grenade',
                        'Interface_HoldFire':'hold','Interface_FireAtWill':'free','Interface_TakeWounded':'carry',
                        'Interface_UpDown':'prone'}.get(base)
                if action=='prone':
                    own=[u for u in self.game.owned(side,session['slot']) if u.number in session['selected']]
                    if own and all(u.stance=='prone' for u in own):action='stand'
                if action:self.choose(session,action)
                if 'Center' in name:self.center(session)
                if name=='Retreat':self.choose(session,'retreat')
                if name.startswith('Rotate '):
                    # Rotation is native; the server coordinate system remains unchanged.
                    current=session.get('rotation',0);current=(current+(1 if name=='Rotate Right' else -1))%4;session['rotation']=current
                    prop=self.assets.fields_for('WORLD').get('Rotation')
                    if prop:peer.update(self.assets.world,prop['id'],current)
                return
            if world!='World':return
            if phase==0:session['down']=(x,y,button);return
            if phase!=1:return
            down=session.get('down');session['down']=None
            if button==1:
                if down and math_dist(down[:2],(x,y))>1:
                    lo=(min(x,down[0]),min(y,down[1]));hi=(max(x,down[0]),max(y,down[1]))
                    selected=[u.number for u in self.game.owned(side,session['slot']) if u.active and lo[0]<=u.x<=hi[0] and lo[1]<=u.y<=hi[1]]
                else:
                    own=[u for u in self.game.owned(side,session['slot']) if u.active and math_dist(u.cell,(x,y))<=1.5]
                    selected=[min(own,key=lambda u:math_dist(u.cell,(x,y))).number] if own else []
                if selected:
                    if modifiers&4:session['selected']=sorted(set(session['selected']+selected))
                    else:session['selected']=selected
            elif button==2:
                if down and math_dist(down[:2],(x,y))>1:action='face'
                else:action=session['action']
                if self.started:self.game.command(side,session['selected'],action,(x,y),slot=session['slot'])
                if action in ('grenade','smoke','fire','face'):session['action']='walk'
        elif kind=='command':
            # The launcher command strip uses the same authoritative validation as native input.
            action=event.get('action')
            if not isinstance(action,str):return
            if action=='cancel':session['action']='walk';session['down']=None
            elif action=='select' and isinstance(event.get('indices'),list):session['selected']=[i for i in event['indices'] if type(i)==int and 0<=i<=3]
            elif action=='center':self.center(session)
            elif action=='objective':self.center(session,self.game.objective)
            elif action in ('walk','run','assault','crawl','grenade','smoke','fire','face','hold','free','stop','prone','stand','crouch','carry','retreat'):self.choose(session,action)

    def choose(self,session,action):
        if action in ('walk','run','assault','crawl','grenade','smoke','fire','face'):
            session['action']='walk' if session['action']==action and action not in ('walk','run','assault','crawl') else action
        elif self.started:self.game.command(session['side'],session['selected'],action,slot=session['slot'])

    def center(self,session,point=None):
        units=[u for u in self.game.owned(session['side'],session['slot']) if u.number in session['selected']]
        peer=session['peer']
        if units and peer and peer.ready:
            x,y=point or units[0].cell
            peer.update(self.assets.world,101,x,force=True);peer.update(self.assets.world,102,y,force=True)

    @staticmethod
    def clean_text(value,limit):
        if not isinstance(value,str):return ''
        return ' '.join(''.join(c for c in value if c.isprintable()).split())[:limit]

    def add_message(self,sender,text):
        self.chat_sequence+=1
        event=dict(type='chat',id=self.chat_sequence,sender=sender,text=text)
        self.chat.append(event)
        for member in self.sessions.values():
            if not member['closed'].is_set():
                try:self.emit(member,event)
                except OSError:pass

    def change_side(self,session,side):
        if type(side) is not int or side not in (0,1):return
        reason=None
        if self.started or self.launching or session['peer']:
            reason='Sides can be changed before the match starts.'
        elif side!=session['side']:
            used={s['slot'] for s in self.sessions.values() if s['side']==side}
            slot=next((i for i in range(self.game.team_size) if i not in used),None)
            if slot is None:reason='That side is full.'
            else:
                session.update(side=side,slot=slot,selected=[0,1,2,3],action='walk',ready=False)
                self.add_message('System',f"{session['name']} moved to {'USA' if side==0 else 'Germany'}.")
        if reason:self.emit(session,{'type':'notice','text':reason})
        self.emit(session,{'type':'assignment','side':session['side'],'slot':session['slot']})

    def lobby_snapshot(self,session):
        teams=[]
        for side in (0,1):
            fireteams=[]
            for slot in range(self.game.team_size):
                member=next((s for s in self.sessions.values() if (s['side'],s['slot'])==(side,slot)),None)
                fireteams.append(dict(slot=slot,name=member['name'] if member else 'CPU',commander=self.commanders.get((side,slot)),
                    weapons=[u.weapon for u in self.game.owned(side,slot)],
                    player=member['username'] if member else None,host=bool(member and member['owner']),
                    ready=bool(member and (member['ready'] or (member['peer'] and member['peer'].ready)))))
            teams.append(dict(side=side,name='USA' if side==0 else 'Germany',fireteams=fireteams))
        return dict(type='lobby',teams=teams,finished=self.game.winner is not None,round=self.round_number,owner=session['owner'],ignored=sorted(session.get('ignored',set())),side=session['side'],slot=session['slot'],started=self.started,
                    launching=self.launching,ready=session['ready'],map=self.game.map_name)

    def loop(self):
        last=time.monotonic();last_status=0
        while not self.stop_event.wait(.05):
            now=time.monotonic();dt=min(.25,now-last);last=now
            with self.lock:
                ready=[s for s in self.sessions.values() if s['peer'] and s['peer'].ready]
                try:
                    for _ in range(120):
                        try:username,event=self.pending.get_nowait()
                        except queue.Empty:break
                        if username in self.sessions:
                            session=self.sessions[username]
                            try:self.handle(session,event)
                            except OSError:
                                if session['peer']:
                                    session['peer'].ready=False
                                    try:session['peer'].stream.shutdown(socket.SHUT_RDWR)
                                    except OSError:pass
                    ready=[s for s in self.sessions.values() if s['peer'] and s['peer'].ready]
                    self.game.ai_slots={(side,slot) for side in (0,1) for slot in range(self.game.team_size)}-{(s['side'],s['slot']) for s in ready}
                    if self.launching and time.monotonic()>self.launch_deadline:
                        self.add_message('System','A battlefield could not finish loading. The room is returning to the lobby.')
                        self.new_round(self.game.map_name)
                        ready=[]
                    if self.launching and self.sessions and all(s['peer'] and s['peer'].ready for s in self.sessions.values()):
                        self.started=True;self.launching=False;self.add_message('System','Match started.')
                    running=self.started and bool(ready)
                    if running:self.game.step(dt)
                    if self.game.winner is not None and not self.result_announced:
                        self.result_announced=True
                        self.record_result()
                        self.add_message('System','Match ended: '+('Draw' if self.game.winner==-1 else ('USA' if self.game.winner==0 else 'Germany')+' won.'))
                    visibility=self.game.visibility()
                    for session in ready:
                        try:
                            session['peer'].batch=[]
                            self.refresh(session,running,now-last_status>=.5,visibility)
                            session['peer'].flush()
                        except OSError:
                            session['peer'].ready=False
                            try:session['peer'].stream.shutdown(socket.SHUT_RDWR)
                            except OSError:pass
                    if now-last_status>=.5:
                        for session in self.sessions.values():
                            try:self.emit(session,self.lobby_snapshot(session))
                            except OSError:pass
                        last_status=now
                    self.game.events.clear()
                except Exception as exc:
                    self.errors.append(repr(exc));self.stop_event.set()

    def show_debrief(self,session):
        peer=session['peer'];side=session['side'];game=self.game
        result='Draw' if game.winner==-1 else 'Victory' if game.winner==side else 'Defeat'
        cause='Time limit reached.' if game.winner==-1 else 'The opposing side can no longer fight.' if game.winner==side else 'Your side can no longer fight.'
        text={'LEndGameVictory':result,'LEDEndCause':cause,'LEDFireTeamStatus':'Your fireteam',
              'LEDPersonalStatus':f"You were soldier {game.player_identity[side,session['slot']]+1}.",
              'LED_VPRest':'Objective capture scoring is disabled.'}
        for unit in game.owned(side,session['slot']):
            text[f'LEDSoldier{unit.number+1}']={'ready':'Survived','WIA':'Wounded','KIA':'Killed','retreated':'Withdrew'}.get(unit.state,unit.state)
        for name,value in text.items():peer.update(self.assets.ref(name),95,value,3,True)
        peer.update(0x20003056,95,'USA\rGermany',3,True)
        peer.update(USER,145,self.assets.ref('EndGameScoring'),4,True)
        peer.update(USER,146,1,2,True)
        session['debrief_shown']=True

    def player_names(self):
        return {} if self.offline else {(s['side'],s['slot']):s.get('name','Player') for s in self.sessions.values()}

    def refresh(self,session,running,send_status,visibility=None):
        peer=session['peer'];side=session['side']
        slot=session['slot'];visibility=visibility or self.game.visibility()
        if session.get('recenter_at') and time.monotonic()>=session['recenter_at']:
            self.center(session);session['recenter_at']=0
        if self.game.winner is not None and not session.get('debrief_shown'):
            self.show_debrief(session)
        peer.update(OBJECTIVE,97,self.assets.world,4)
        peer.update(OBJECTIVE_FLOOR,97,self.assets.world,4)
        peer.update(OBJECTIVE_FLOOR,61,self.assets.capture_floor_image(self.game.capture_owner),4)
        peer.update(OBJECTIVE_FLOOR,660,13 if self.game.capture_owner is None else 0)
        peer.update(OBJECTIVE_FLAG,97,self.assets.world,4)
        peer.update(OBJECTIVE_FLAG,61,self.assets.capture_flags[self.game.capture_owner] if self.game.capture_owner is not None else 0,4)
        names=self.player_names()
        for u in self.game.units:
            visible=u.uid in visibility[side] and not u.carried_by
            peer.update(u.uid,97,self.assets.world if visible else 0,4)
            if not visible:continue
            # Integer cells are also needed by terrain sorting and text placement.
            peer.update(u.uid,59,round(u.x));peer.update(u.uid,60,round(u.y))
            peer.update(u.uid,365,u.x,5);peer.update(u.uid,366,u.y,5);peer.update(u.uid,68,u.direction)
            peer.update(u.uid,61,self.assets.unit_image(self.game,u),4)
            peer.update(u.uid,106,0 if u.stance=='crouch' and u.side==1 and not u.path else 1)
            peer.update(u.uid,79,self.assets.ref(f'img - dot{u.number+1} static') if u.side==side and u.slot==slot and u.active else 0,4)
            peer.update(u.uid,80,0,4)
            peer.update(u.uid,95,self.assets.unit_name(u,side,slot,names),3)
        for u in self.game.owned(side,slot):
            uid=DESTINATION_BASE+u.number
            show=bool(u.active and u.path)
            flash=show and int(self.game.time*3)%2==0
            if u.active and u.path:
                peer.update(uid,59,u.path[-1][0]);peer.update(uid,60,u.path[-1][1])
            peer.update(uid,61,0,4)
            peer.update(uid,97,0,4)
            for edge,(dx,dy) in enumerate(((0,0),(1,0),(0,1),(0,0))):
                edge_uid=DESTINATION_EDGE_BASE+u.number*4+edge
                if show:
                    peer.update(edge_uid,59,u.path[-1][0]+dx);peer.update(edge_uid,60,u.path[-1][1]+dy)
                peer.update(edge_uid,660,1 if flash else 0)
                peer.update(edge_uid,97,self.assets.world if flash else 0,4)
            fill_uid=DESTINATION_FILL_BASE+u.number
            if show:
                peer.update(fill_uid,59,u.path[-1][0])
                peer.update(fill_uid,60,u.path[-1][1])
            peer.update(fill_uid,660,5+u.number if flash else 0)
            peer.update(fill_uid,97,self.assets.world if flash else 0,4)
            pip_uid=DESTINATION_PIP_BASE+u.number
            if show:
                peer.update(pip_uid,59,u.path[-1][0]);peer.update(pip_uid,60,u.path[-1][1])
            peer.update(pip_uid,660,9+u.number if show else 0)
            peer.update(pip_uid,97,self.assets.world if show else 0,4)
        destination_state=tuple((u.path[-1],int(self.game.time*3)%2) if u.active and u.path else None for u in self.game.owned(side,slot))
        if destination_state!=session.get('destination_state'):
            session['destination_state']=destination_state
            session['destination_refresh']=session.get('destination_refresh',0)+1
            # Clear the complete filled-tile area when it flashes off or moves.
            peer.update(self.assets.world,86,session['destination_refresh'],2,True)
        for obj in self.assets.hud_buttons:
            p=obj['properties']
            name=obj['name'];row=int(p.get('SoldNum',0))
            action={'Interface_WalkTo':'walk','Interface_Run':'run','Interface_CrawlTo':'crawl','Interface_Assault':'assault',
                    'Interface_FireAt':'fire','Interface_Face':'face','Interface_ThrowGranade':'grenade'}.get(name.rstrip('1234'))
            selected=session['selected']==([row-1] if row else [0,1,2,3])
            pressed=(name==session.get('pressed_button') or (action==session['action'] and selected)
                     or (name==session.get('clicked_button') and time.monotonic()<session.get('clicked_until',0)))
            img=p.get('ImagePressed' if pressed else 'ImageIdle',p.get('Image'))
            if img:peer.update(obj['uid'],61,img['ref'],4)
        sound=None
        for kind,value in self.game.events:
            if kind=='shot':
                u=self.game.by_id(value)
                if u.uid in visibility[side] and sound!='Grenade':sound=u.weapon
            elif kind=='blast':sound='Grenade'
        if sound:
            # The lost client module's DirectSound trigger is replaced by local playback.
            # Send a symbolic allow-listed name, never a remote filesystem path.
            try:self.emit(session,{'type':'sound','name':sound})
            except OSError:pass
        effects=[(x,y,SMOKE_IMAGE) for x,y,_ in self.game.smokes for x,y in ((x,y),(x-1,y),(x,y+1))]
        # The recovered grenade reference is a small flash. Surviving imagery
        # also shows an explosion cloud, so retain the recovered exp2 cloud.
        # Their combined timing remains reconstructed, not a recovered script.
        effects += [(x,y,img) for x,y,_ in self.game.blasts
                    for img in (self.assets.grenade_image,self.assets.ref('img - exp2 action'))]
        for i in range(EFFECT_COUNT):
            uid=EFFECT_BASE+i
            if i<len(effects):
                x,y,img=effects[i];peer.update(uid,59,x);peer.update(uid,60,y);peer.update(uid,61,img,4);peer.update(uid,97,self.assets.world,4)
            else:peer.update(uid,97,0,4)
        if send_status:
            text=self.game.status(side,slot)
            if not running:text='Waiting for host to begin battle; vacant fireteams will use AI'
            command=f"Fireteam {slot+1} | Selected {','.join(str(i+1) for i in session['selected'])}: {session['action']}"
            peer.update(STATUS,95,text if self.game.winner is not None else command+' | '+self.game.notices[side],3)
            peer.update(OBJECTIVE,95,self.game.capture_status(),3)
            peer.update(self.assets.ref('LClock'),95,f'{int(self.game.time)//60:02}:{int(self.game.time)%60:02}',3)
            for u in self.game.owned(side,slot):
                i=str(u.number+1)
                icon={'Garand':'wgar','Mauser':'wkar','BAR':'wbar','MG42':'wm42','Thompson':'wtom','MP40':'wm40'}.get(u.weapon)
                if icon and 'img - '+icon+' static' in self.assets.objects:
                    peer.update(self.assets.ref('_HG_UnitTile_ShowWeapon'+i),61,self.assets.ref('img - '+icon+' static'),4)
                for name,value in [('_HG_UnitTile_State',u.state if not u.active else 'Reload' if u.reload else 'Moving' if u.path else u.stance.title()),
                                   ('_HG_UnitTile_Info',str(round(u.stress*100))),('_HG_UnitTile_InfoHit',str(u.health)),
                                   ('_HG_UnitTile_ShowAmmo',str(u.ammo+u.reserve)),('_HG_UnitTile_AmGranade',str(u.grenades))]:
                    peer.update(self.assets.ref(name+i),95,value,3)
            roster=[]
            for team in (0,1):
                for group in range(self.game.team_size):
                    member=next((s for s in self.sessions.values() if s['side']==team and s['slot']==group),None)
                    control='AI' if not member else 'Player' if member['peer'] and member['peer'].ready else 'Loading'
                    roster.append(dict(side=team,slot=group,control=control,active=sum(u.active for u in self.game.owned(team,group))))
            try:self.emit(session,{'type':'status','text':text,'command':command,'notice':self.game.notices[side],
                                   'started':self.started,'roster':roster,'winner':self.game.winner,
                                   'units':[dict(index=u.number,state=u.state,weapon=u.weapon,ammo=u.ammo,reserve=u.reserve,health=u.health) for u in self.game.owned(side,slot)]})
            except OSError:pass
        peer.update(USER,86,round(self.game.time*20)+1,2,True)

    def close(self):
        self.stop_event.set()
        for s in self.sockets:
            try:s.close()
            except OSError:pass
        with self.lock:
            for session in self.sessions.values():
                session['closed'].set()
                for s in (session['control'],session['peer'].stream if session['peer'] else None):
                    if s:
                        try:s.shutdown(socket.SHUT_RDWR);s.close()
                        except OSError:pass

def math_dist(a,b):
    return ((a[0]-b[0])**2+(a[1]-b[1])**2)**.5
