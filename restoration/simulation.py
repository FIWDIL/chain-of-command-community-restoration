"""Reconstructed match rules; no claim that these are the lost 2AM server rules."""
from dataclasses import dataclass, field
from collections import deque
from functools import lru_cache
import heapq
import math
import random
from .assets import UNIT_BASE
from .roster import MAX_SLOTS, validate_size, default_pool, loadouts
from .tactics import TacticalAI

# Practical firing intervals, not cyclic rates. All unverified values are explicit here.
WEAPONS = {
    'Garand': dict(magazine=8, interval=1.0, reload=3.2, range=24, accuracy=.70, damage=65),
    'Mauser': dict(magazine=5, interval=1.8, reload=4.0, range=26, accuracy=.76, damage=70),
    'BAR': dict(magazine=20, interval=.30, reload=4.5, range=24, accuracy=.48, damage=58),
    'MG42': dict(magazine=50, interval=.18, reload=6.0, range=27, accuracy=.40, damage=58),
    'Thompson': dict(magazine=30, interval=.24, reload=3.6, range=16, accuracy=.48, damage=40),
    'MP40': dict(magazine=32, interval=.30, reload=3.6, range=17, accuracy=.50, damage=40),
}
SPEEDS = {'run':2.5, 'walk':1.35, 'assault':1.15, 'crawl':.55}

@dataclass
class Unit:
    uid: int
    side: int
    index: int
    x: float
    y: float
    weapon: str
    direction: int = 0
    health: int = 100
    state: str = 'ready'
    stance: str = 'stand'
    mode: str = 'walk'
    path: list = field(default_factory=list)
    ammo: int = 0
    reserve: int = 0
    reload: float = 0
    cooldown: float = 0
    stress: float = 0
    stun: float = 0
    anim_until: float = 0
    animation: str = ''
    hold_fire: bool = False
    target: int = 0
    grenades: int = 0
    smoke: int = 1
    carrying: int = 0
    carried_by: int = 0
    ai_role: str = ''
    ai_until: float = 0
    ai_contact: tuple = (-1, -1)
    ai_contact_until: float = 0
    ai_smoke_until: float = 0

    @property
    def cell(self):
        return round(self.x), round(self.y)

    @property
    def active(self):
        return self.state == 'ready'

    @property
    def slot(self):return self.index // 4

    @property
    def number(self):return self.index % 4

class Game:
    def __init__(self, assets, map_name='AbbeyArden', ai_sides=(1,), seed=None, team_size=1, pool=None):
        self.assets=assets; self.map_name=map_name
        self.team_size=validate_size(team_size);self.pool=dict(default_pool(team_size) if pool is None else pool)
        self.ai_slots={(side,slot) for side in ai_sides for slot in range(team_size)}
        self._vision=None
        self.map_objects, scenario=assets.read_map(map_name)
        self.random=random.Random(seed); self.ai_sides=set(ai_sides)
        self.time=0.; self.next_ai=0.; self.units=[]; self.grenades=[]; self.smokes=[]
        self.blasts=[]
        self.winner=None; self.events=[]; self.notices=['','']
        self.blocked=set(); self.solid=set(); self.windows=set(); self.low=set(); self.trees=set()
        self.spawns=[(20,50),(80,50)]
        for obj in self.map_objects:
            p=obj['properties']; terrain=str(p.get('terrain','')).casefold()
            cell=(int(p.get('x',0)),int(p.get('y',0)))
            image=str(p.get('Image','')).casefold()
            if terrain=='_hg_nopass':
                self.blocked.add(cell)
                (self.windows if 'win' in image else self.trees if 'tr0' in image else self.solid).add(cell)
            elif terrain=='_hg_climb':
                self.low.add(cell)
                if 'bh0' in image:
                    self.solid.add(cell); self.blocked.add(cell)
        objectives=[]
        for obj in scenario:
            p=obj['properties']
            if p.get('Type')=='startingpoint':
                side=0 if str(p.get('state','')).lower() in ('usa','american') else 1
                self.spawns[side]=(int(p.get('Start_X',20+side*60)),int(p.get('Start_Y',50)))
            if p.get('Player Type')=='VictoryPoints':
                objectives.append((int(p.get('x',p.get('x_static',50))),int(p.get('y',50))))
        self.objective=self.nearest_open(objectives[0] if objectives else tuple(round((a+b)/2) for a,b in zip(*self.spawns)))
        self.capture_owner=None; self.capture_side=None; self.capture_elapsed=0.
        self.capture_contested=False
        used=set()
        for side in (0,1):
            weapons=loadouts(assets,team_size,side,self.pool)
            positions=self.spawn_cells(self.spawns[side],team_size*4,used)
            for i,(x,y) in enumerate(positions):
                used.add((x,y));weapon=weapons[i//4][i%4]
                u=Unit(UNIT_BASE+side*MAX_SLOTS*4+i,side,i,float(x),float(y),weapon)
                u.direction=self.direction((x,y),self.objective)
                self.equip(u,weapon);u.grenades=assets.grenade_counts[side];self.units.append(u)
        self.player_identity={(side,slot):self.random.randrange(4) for side in (0,1) for slot in range(team_size)}
        self.tactics=TacticalAI(self)
        self.ai_deadlines={(side,slot):(side*self.team_size+slot)*1.4/(2*self.team_size) for side in (0,1) for slot in range(self.team_size)}

    def equip(self, unit, weapon):
        # AmmoMax is treated as total carried ammunition, never added on top of a
        # magazine. The magazine/reload subdivision remains a reconstructed rule.
        unit.weapon=weapon
        total=self.assets.ammo_limits[weapon]
        unit.ammo=min(WEAPONS[weapon]['magazine'],total)
        unit.reserve=total-unit.ammo

    def spawn_cells(self, origin, count, excluded):
        # Flood outward from the recovered spawn through connected walkable tiles.
        # Never place later fireteams across a wall merely because it is nearby.
        start=self.nearest_open(origin);pending=deque([start]);seen={start};result=[]
        while pending and len(result)<count:
            p=pending.popleft()
            if p not in excluded:result.append(p)
            for dx,dy in ((1,0),(0,1),(-1,0),(0,-1)):
                q=(p[0]+dx,p[1]+dy)
                if 1<=q[0]<=98 and 1<=q[1]<=98 and q not in self.blocked and q not in seen:
                    seen.add(q);pending.append(q)
        if len(result)<count:raise ValueError('Recovered deployment area is too small for this team size')
        return result

    def owned(self,side,slot):return [u for u in self.units if u.side==side and u.slot==slot]

    @staticmethod
    def unit_label(u,side,slot):
        if u.side!=side:return ''
        return str(u.number+1) if u.slot==slot else f'F{u.slot+1}.{u.number+1}'

    def nearest_open(self, cell, excluded=()):
        cx,cy=cell
        for r in range(100):
            candidates=[(cx+dx,cy+dy) for dx in range(-r,r+1) for dy in range(-r,r+1) if max(abs(dx),abs(dy))==r]
            for p in sorted(candidates,key=lambda p:math.dist(p,cell)):
                if 1<=p[0]<=98 and 1<=p[1]<=98 and p not in self.blocked and p not in excluded:
                    return p
        raise ValueError('Map has no walkable square')

    def path(self, start, end, traffic=None, max_nodes=None):
        start=tuple(start);end=self.nearest_open(tuple(end))
        queue=[(math.dist(start,end),0,start)];cost={start:0};prev={};visited=set()
        while queue:
            if max_nodes is not None and len(visited)>=max_nodes:return []
            _,g,p=heapq.heappop(queue)
            if p in visited: continue
            if p==end:
                result=[]
                while p!=start: result.append(p);p=prev[p]
                return result[::-1]
            visited.add(p)
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)):
                q=(p[0]+dx,p[1]+dy)
                if not (1<=q[0]<=98 and 1<=q[1]<=98) or q in self.blocked: continue
                if dx and dy and ((p[0]+dx,p[1]) in self.blocked or (p[0],p[1]+dy) in self.blocked): continue
                ng=g+math.hypot(dx,dy)*(2 if q in self.low else 1)
                if traffic and q!=end:ng+=traffic.get(q,0)
                if ng<cost.get(q,float('inf')):
                    cost[q]=ng;prev[q]=p;heapq.heappush(queue,(ng+math.dist(q,end),ng,q))
        return []

    @staticmethod
    @lru_cache(maxsize=32768)
    def ray(a,b):
        # Dense, rounded samples include boundary-adjacent squares; diagonal corners cannot leak shots.
        distance=math.dist(a,b); steps=max(1,math.ceil(distance*4)); seen=set();previous=tuple(a);result=[]
        for i in range(1,steps):
            p=(round(a[0]+(b[0]-a[0])*i/steps),round(a[1]+(b[1]-a[1])*i/steps))
            if p[0]!=previous[0] and p[1]!=previous[1]:
                for q in ((p[0],previous[1]),(previous[0],p[1])):
                    if q not in seen and q!=tuple(a) and q!=tuple(b):seen.add(q);result.append(q)
            if p not in seen and p!=tuple(a) and p!=tuple(b):seen.add(p);result.append(p)
            previous=p
        return tuple(result)

    def clear_line(self, a, b, stance='stand', target_stance='stand', smoke=True):
        cells=self.ray(tuple(a),tuple(b))
        if any(p in self.solid for p in cells): return False
        if (stance!='stand' or target_stance!='stand') and any(p in self.windows for p in cells): return False
        if (stance=='prone' or target_stance=='prone') and any(p in self.low for p in cells): return False
        if smoke and any(math.dist(p,(s[0],s[1]))<=2.5 for p in cells for s in self.smokes):return False
        return True

    def visible(self, side, target):
        if self._vision is not None:return target.uid in self._vision[side]
        if side==target.side:return True
        if target.carried_by:return False
        for u in self.units:
            if not u.active or u.side!=side:continue
            distance=math.dist(u.cell,target.cell)
            limit=28 if target.stance=='stand' else 22 if target.stance=='crouch' else 16
            if target.cell in self.trees: limit*=.65
            if distance<=limit and self.clear_line(u.cell,target.cell,u.stance,target.stance):return True
        return False

    def visibility(self):
        return [{u.uid for u in self.units if self.visible(side,u)} for side in (0,1)]

    def hit_chance(self, shooter, target):
        w=WEAPONS[shooter.weapon];distance=math.dist(shooter.cell,target.cell)
        if distance>w['range'] or not self.clear_line(shooter.cell,target.cell,shooter.stance,target.stance):return 0.
        chance=w['accuracy']*max(.1,1-distance/w['range']*.8)*(1-shooter.stress*.65)
        if shooter.path:chance*=.48
        if shooter.stance=='prone':chance*=1.20
        if target.stance=='prone':chance*=.48
        elif target.stance=='crouch':chance*=.72
        if target.path:chance*=.8
        cells=list(self.ray(shooter.cell,target.cell))
        if target.cell in self.low or any(p in self.low or p in self.windows for p in cells[-3:]):chance*=.45
        if target.cell in self.trees:chance*=.65
        return max(.01,min(.95,chance))

    def command(self,side,indices,action,point=None,slot=0):
        if self.winner is not None:return
        selected=[u for u in self.owned(side,slot) if u.number in indices and u.active and not u.carried_by]
        if not selected:return
        self.notices[side]=''
        if point is not None:
            if not isinstance(point,(list,tuple)) or len(point)!=2:return
            if not all(isinstance(v,(int,float)) and math.isfinite(v) and 0<=v<100 for v in point):return
            point=tuple(round(v) for v in point)
        if action in SPEEDS and point is not None:
            anchor=selected[0].cell; reserved=set()
            for u in selected:
                dest=self.nearest_open((point[0]+u.cell[0]-anchor[0],point[1]+u.cell[1]-anchor[1]),reserved);reserved.add(dest)
                u.path=self.path(u.cell,dest);u.mode=action;u.stance='prone' if action=='crawl' else 'stand';u.target=0
                if not u.path and u.cell!=dest:self.notices[side]='No route to destination'
        elif action=='stop':
            for u in selected:u.path=[];u.target=0
        elif action in ('stand','crouch','prone'):
            for u in selected:u.stance=action;u.path=[]
        elif action in ('hold','free'):
            for u in selected:u.hold_fire=action=='hold';u.target=0
        elif action=='face' and point is not None:
            for u in selected:u.direction=self.direction(u.cell,point);u.path=[]
        elif action=='fire' and point is not None:
            enemies=[u for u in self.units if u.side!=side and u.active and self.visible(side,u) and math.dist(u.cell,point)<=2]
            if enemies:
                target=min(enemies,key=lambda u:math.dist(u.cell,point))
                for u in selected:u.target=target.uid;u.hold_fire=False;u.path=[]
            else:self.notices[side]='No visible enemy at that point'
        elif action in ('grenade','smoke') and point is not None:
            limit=self.assets.grenade_range
            candidates=[u for u in selected if (u.grenades if action=='grenade' else u.smoke)>0 and math.dist(u.cell,point)<=limit and u.stun<=0]
            if not candidates:self.notices[side]=f'Throw range: {limit:g} squares; check remaining grenades';return
            u=min(candidates,key=lambda u:math.dist(u.cell,point));landing=point
            cells=list(self.ray(u.cell,point)); wall=next((p for p in cells if p in self.solid),None)
            if wall:
                self.notices[side]='Wall blocks throw';return
            if any(p in self.windows for p in cells):
                chance=max(.1,1-.9*max(0,math.dist(u.cell,point)-1)/4)
                if self.random.random()>chance:landing=u.cell
            self.grenades.append(dict(x=landing[0],y=landing[1],until=self.time+5,smoke=action=='smoke',side=side))
            if action=='grenade':u.grenades-=1
            else:u.smoke-=1
            u.path=[];u.animation='throw';u.anim_until=self.time+.8;u.direction=self.direction(u.cell,point)
        elif action=='carry':
            for u in selected:
                if u.carrying:
                    wounded=self.by_id(u.carrying);wounded.carried_by=0;u.carrying=0
                else:
                    choices=[w for w in self.units if w.side==side and w.state=='WIA' and not w.carried_by and math.dist(w.cell,u.cell)<=2]
                    if choices:w=min(choices,key=lambda w:math.dist(w.cell,u.cell));w.carried_by=u.uid;u.carrying=w.uid
        elif action=='retreat':
            # One player cannot concede the other six players' fireteams.
            for u in selected:
                u.state='Retreated';u.path=[]
                if u.carrying:self.by_id(u.carrying).carried_by=0;u.carrying=0

    def by_id(self,uid):return next((u for u in self.units if u.uid==uid),None)

    @staticmethod
    def direction(a,b):return int(round(math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))/45)*45)%360

    def hurt(self,u,damage):
        if u.state=='KIA':return
        u.health=max(0,u.health-round(damage));u.stress=min(1,u.stress+.45)
        if u.health==0:
            u.state='KIA' if u.state=='WIA' or self.random.random()<.45 else 'WIA';u.path=[]
            if u.carrying:self.by_id(u.carrying).carried_by=0;u.carrying=0

    def step(self,dt):
        if self.winner is not None:return
        self.time+=dt;self.smokes=[s for s in self.smokes if s[2]>self.time];self.blasts=[b for b in self.blasts if b[2]>self.time]
        for g in list(self.grenades):
            if self.time<g['until']:continue
            self.grenades.remove(g);p=(g['x'],g['y'])
            if g['smoke']:self.smokes.append((p[0],p[1],self.time+30));self.events.append(('smoke',p));continue
            self.events.append(('blast',p))
            self.blasts.append((p[0],p[1],self.time+2.4))
            for u in self.units:
                distance=math.dist(u.cell,p)
                radius=self.assets.grenade_radius
                if distance>=radius or not self.clear_line(p,u.cell,smoke=False):continue
                factor=max(0,1-distance/radius);u.stun=max(u.stun,5*factor);u.stress=min(1,u.stress+factor)
                if self.random.random()<factor:self.hurt(u,150*factor*(.6 if u.stance=='prone' else 1))
        self._vision=self.visibility()
        due={pair for pair in self.ai_slots if self.time>=self.ai_deadlines.get(pair,0)}
        if due:
            self.tactics.think(due)
            for pair in due:self.ai_deadlines[pair]=self.time+1.4
        for u in self.units:
            if not u.active:continue
            u.stress=max(0,u.stress-dt*.025);u.stun=max(0,u.stun-dt);u.cooldown=max(0,u.cooldown-dt)
            if u.reload>0:
                u.reload=max(0,u.reload-dt)
                if not u.reload:n=min(WEAPONS[u.weapon]['magazine'],u.reserve);u.ammo=n;u.reserve-=n
            if u.stun>0:continue
            if u.path:
                speed=SPEEDS[u.mode]*(.6 if u.carrying else 1)*(1-u.stress*.2)
                travel=speed*dt
                while u.path and travel>0:
                    p=u.path[0];dx=p[0]-u.x;dy=p[1]-u.y;distance=math.hypot(dx,dy)
                    # Rounded cells can equal the waypoint halfway through a step,
                    # making the old facing calculation snap east every square.
                    if distance:u.direction=self.direction((u.x,u.y),p)
                    if distance<=travel:
                        u.x,u.y=map(float,p);u.path.pop(0);travel-=distance
                    else:
                        u.x+=dx/distance*travel;u.y+=dy/distance*travel;travel=0
                if u.carrying:w=self.by_id(u.carrying);w.x=u.x;w.y=u.y
            if u.hold_fire or u.carrying or (u.path and u.mode!='assault') or u.cooldown or u.reload:continue
            targets=[v for v in self.units if v.side!=u.side and v.active and self.visible(u.side,v) and self.hit_chance(u,v)>0]
            if not targets:continue
            v=next((v for v in targets if v.uid==u.target),min(targets,key=lambda v:math.dist(u.cell,v.cell)))
            if not u.ammo:
                if u.reserve:u.reload=WEAPONS[u.weapon]['reload']*(1+u.stress)
                continue
            u.ammo-=1;u.cooldown=WEAPONS[u.weapon]['interval']*(1+u.stress*.4)
            u.direction=self.direction(u.cell,v.cell);u.animation='fire';u.anim_until=self.time+.28
            v.stress=min(1,v.stress+.08);self.events.append(('shot',u.uid))
            if self.random.random()<self.hit_chance(u,v):self.hurt(v,WEAPONS[u.weapon]['damage']*self.random.uniform(.65,1.3))
            if not u.ammo and u.reserve:u.reload=WEAPONS[u.weapon]['reload']*(1+u.stress)
        self._vision=None
        self.update_capture(dt)
        active=[any(u.active and u.side==s for u in self.units) for s in (0,1)]
        if not all(active):self.winner=0 if active[0] else 1 if active[1] else -1;return
        if self.time>=900:self.winner=-1

    def update_capture(self, dt):
        sides={u.side for u in self.units if u.active and not u.carried_by
               and abs(u.x-self.objective[0])<.5 and abs(u.y-self.objective[1])<.5}
        self.capture_contested=len(sides)>1
        if self.capture_contested:return
        side=next(iter(sides),None)
        if side is None or side==self.capture_owner:
            self.capture_side=None;self.capture_elapsed=0.
            return
        if self.capture_side!=side:
            self.capture_side=side;self.capture_elapsed=0.
        self.capture_elapsed=min(120.,self.capture_elapsed+max(0.,dt))
        if self.capture_elapsed>=120.:
            self.capture_owner=side;self.capture_side=None;self.capture_elapsed=0.
            self.notices=['Capture point secured by '+('USA' if side==0 else 'Germany')]*2

    def capture_status(self):
        owner='Neutral' if self.capture_owner is None else ('USA','Germany')[self.capture_owner]
        if self.capture_contested:return f'{owner} | Contested'
        if self.capture_side is not None:
            remaining=math.ceil(120-self.capture_elapsed)
            return f'{("USA","Germany")[self.capture_side]} capturing | {remaining//60:02}:{remaining%60:02}'
        return f'{owner} | '+('Capture: 02:00' if self.capture_owner is None else 'Captured')

    def think(self):
        self.tactics.think()

    def image(self,u):
        master=self.assets.objects['_hg_unitmaster_american' if u.side==0 else '_hg_unitmaster_german']['properties']
        if u.state=='WIA':field='UM_ImageWoundedLegSt'
        elif u.state=='KIA':field='UMImageDead'
        elif u.carrying:
            field='UM_ImageWoundedCarring' if u.path else 'UM_ImageWoundedCarringIdle'
        elif self.time<u.anim_until:
            if u.animation=='throw':field='UMImageLyThrowGr' if u.stance=='prone' else 'UMImageStThrowGr'
            else:field='UMImageProneFirin' if u.stance=='prone' else 'UMImageStandingFi'
        elif u.path:field='UMImageProneMovin' if u.mode=='crawl' else 'UMImageStandingMo' if u.mode=='run' else 'UMImageWalking'
        elif u.stance=='prone':field='UMImageProneIdle'
        elif u.stance=='crouch':field='UMImageKneel'
        else:field='UMImageStIdle'
        return master[field]['name'].casefold()

    def status(self,side,slot=0):
        own=self.owned(side,slot)
        ammo='  '.join(f'{u.number+1}:{u.ammo}/{u.reserve}' if u.active else f'{u.number+1}:{u.state}' for u in own)
        if self.winner is not None:
            result='Draw' if self.winner==-1 else 'Victory' if self.winner==side else 'Defeat'
            return f'{result} | Fireteam {slot+1}: Player was soldier {self.player_identity[side,slot]+1} | {ammo}'
        return f'{int(self.time)//60:02}:{int(self.time)%60:02} | {ammo}'
