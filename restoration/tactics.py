"""Bounded, observation-driven AI for the replacement match service.

Uses the ordinary commands, ammunition, sight and stress rules. No hidden enemy
coordinates are retained: contact memory is a location with a twelve-second TTL.
"""
import math


class TacticalAI:
    def __init__(self, game):
        self.g = game

    def observed(self, observer, target):
        g = self.g
        limit = {'stand': 28, 'crouch': 22, 'prone': 16}[target.stance]
        if target.cell in g.trees: limit *= .65
        return math.dist(observer.cell, target.cell) <= limit and g.clear_line(observer.cell, target.cell, observer.stance, target.stance)

    def protection(self, point, threat):
        g = self.g
        cells = g.ray(threat, point)
        near = cells[-3:]
        return (1.0 if not g.clear_line(threat, point, smoke=False) else
                .65 if point in g.low or any(p in g.low or p in g.windows for p in near) else
                .35 if point in g.trees else 0.0)

    def destination(self, u):
        g = self.g
        # One capturing element, separated supporting sectors around it.
        angle = math.atan2(g.spawns[u.side][1]-g.objective[1], g.spawns[u.side][0]-g.objective[0])
        angle += 2*math.pi*u.slot/max(1,g.team_size)
        radius = 0 if u.slot == 0 else 4+2*(u.slot//4)
        p = (g.objective[0]+math.cos(angle)*radius+(u.number%2-.5)*2,
             g.objective[1]+math.sin(angle)*radius+(u.number//2-.5)*2)
        return g.nearest_open(tuple(round(v) for v in p))

    def choose_position(self, u, goal, threat=None, support=False, retreat=False):
        g = self.g
        distance = math.dist(u.cell, goal)
        step = min(6, distance)
        anchor = u.cell if support or retreat else tuple(u.cell[i]+(goal[i]-u.cell[i])*step/max(1,distance) for i in (0,1))
        candidates = {u.cell, tuple(round(v) for v in anchor)}
        for center in (u.cell, anchor):
            for radius in (2,4):
                for i in range(8):
                    candidates.add(tuple(round(center[j]+radius*(math.cos(i*math.pi/4) if j==0 else math.sin(i*math.pi/4))) for j in (0,1)))
        allies = [a for a in g.units if a.side==u.side and a.active and a.uid!=u.uid]
        ranked=[]
        for p in candidates:
            if not (1<=p[0]<=98 and 1<=p[1]<=98) or p in g.blocked: continue
            progress=distance-math.dist(p,goal)
            if not support and not retreat and distance>3 and progress < .5 and p!=u.cell:continue
            if threat and math.dist(p,threat)<3:continue
            spacing=min((min(math.dist(p,a.cell),math.dist(p,a.path[-1]) if a.path else 99) for a in allies),default=99)
            # Occupied endpoints are never attractive, even behind good cover.
            if spacing < 1.5 and p!=u.cell:continue
            value=-math.dist(p,anchor)*.75-math.dist(p,u.cell)*.2
            if p==u.cell and not support and not retreat and distance>3:value-=12
            if threat:
                protection=self.protection(p,threat)
                value+=protection*(16 if retreat else 10)
                if support and not g.clear_line(p,threat):value-=11
                if retreat:value+=min(5,math.dist(p,threat)-math.dist(u.cell,threat))
            elif p in g.trees or p in g.low:value+=2
            value-=max(0,2.3-spacing)*7
            ranked.append((value,p))
        traffic={}
        for a in allies:
            for p in [a.cell]+a.path[:3]:traffic[p]=traffic.get(p,0)+2
        for _,p in sorted(ranked,reverse=True)[:5]:
            if p==u.cell:return p,[]
            route=g.path(u.cell,p,traffic,max_nodes=768)
            if route:return p,route
        return u.cell,[]

    def hold(self,u,threat=None,role='Covering fire'):
        g=self.g
        u.path=[];u.ai_role=role;u.hold_fire=False
        u.stance='prone'
        if threat:
            u.direction=g.direction(u.cell,threat)
            # A prone support soldier behind a sill must rise to see over it.
            for stance in ('prone','crouch','stand'):
                if g.clear_line(u.cell,threat,stance):u.stance=stance;break

    def smoke_screen(self,u,threat):
        g=self.g
        if not u.smoke or u.stun or u.carrying or g.time<u.ai_smoke_until:return False
        if any(s['smoke'] and math.dist(u.cell,(s['x'],s['y']))<10 for s in g.grenades):return False
        if any(math.dist(u.cell,s[:2])<8 for s in g.smokes):return False
        distance=math.dist(u.cell,threat)
        if distance<5:return False
        point=tuple(round(u.cell[i]+(threat[i]-u.cell[i])*4/distance) for i in (0,1))
        if point in g.blocked or any(p in g.solid or p in g.windows for p in g.ray(u.cell,point)):return False
        before=u.smoke
        g.command(u.side,[u.number],'smoke',point,slot=u.slot)
        if u.smoke<before:
            for ally in g.owned(u.side,u.slot):ally.ai_smoke_until=g.time+25
        return u.smoke<before

    def think(self,slots=None):
        g=self.g
        for side,slot in sorted(g.ai_slots if slots is None else slots):
            members=[u for u in g.owned(side,slot) if u.active and not u.carried_by]
            if not members:continue
            contacts=[e for e in g.units if e.active and e.side!=side and any(self.observed(u,e) for u in members)]
            center=tuple(sum(u.cell[i] for u in members)/len(members) for i in (0,1))
            enemy=min(contacts,key=lambda e:math.dist(center,e.cell),default=None)
            threat=enemy.cell if enemy else None
            if threat:
                for u in members:u.ai_contact=threat;u.ai_contact_until=g.time+12
            else:
                memory=max(members,key=lambda u:u.ai_contact_until)
                if memory.ai_contact_until>g.time:threat=memory.ai_contact
            armed=[u for u in members if u.ammo>0 and not u.reload and u.stun<=0 and not u.carrying]
            # Alternate the firing element; a gunner can move while a rifle covers.
            phase=int((g.time+slot*2)/9)%2
            armed.sort(key=lambda u:((0 if not phase else 2) if u.weapon in ('BAR','MG42') else 1, (u.number+phase*2)%4))
            support=armed[:max(1,len(members)//2)] if enemy else []
            ready=any(not u.path and self.observed(u,enemy) for u in support) if enemy else False
            for u in members:
                if u.stun>0 or u.carrying:continue
                u.hold_fire=False
                danger=next((b for b in g.grenades if not b['smoke'] and math.dist(u.cell,(b['x'],b['y']))<g.assets.grenade_radius+.5 and g.clear_line(u.cell,(b['x'],b['y']),smoke=False)),None)
                if danger:
                    point=(danger['x'],danger['y']);dx=u.x-point[0];dy=u.y-point[1];d=max(.1,math.hypot(dx,dy))
                    dest=g.nearest_open((round(u.x+(dx or 1)*4/d),round(u.y+dy*4/d)))
                    u.path=g.path(u.cell,dest);u.mode='run';u.stance='stand';u.ai_role='Avoid grenade';continue
                # Keep a chosen route long enough to complete a short bound.
                if g.time<u.ai_until and (u.path or u.ai_role=='Wait for smoke'):continue
                goal=self.destination(u)
                if threat and u.stress>.65:
                    p,route=self.choose_position(u,goal,threat,retreat=True)
                    if route:u.path=route;u.mode='crawl' if u.stress>.85 else 'run';u.stance='prone' if u.mode=='crawl' else 'stand';u.ai_role='Seek cover';u.ai_until=g.time+5;continue
                if enemy and u in support:
                    if self.protection(u.cell,threat)<.3:
                        p,route=self.choose_position(u,goal,threat,support=True)
                        if route:u.path=route;u.mode='assault';u.stance='stand';u.ai_role='Support position';u.ai_until=g.time+5;continue
                    self.hold(u,threat);u.target=enemy.uid;continue
                pending=next((s for s in g.grenades if s['smoke'] and math.dist(u.cell,(s['x'],s['y']))<9),None)
                if pending:
                    self.hold(u,threat,'Wait for smoke');u.ai_until=pending['until']+.15;continue
                if enemy and not ready and self.protection(u.cell,threat)<.3 and self.smoke_screen(u,threat):
                    self.hold(u,threat,'Wait for smoke');u.ai_until=g.time+5.15;continue
                if math.dist(u.cell,goal)<1.4:
                    self.hold(u,threat,'Guard');continue
                p,route=self.choose_position(u,goal,threat)
                if route:
                    u.path=route;u.mode='assault' if not threat or ready else 'run' if g.smokes else 'crawl'
                    u.stance='prone' if u.mode=='crawl' else 'stand';u.ai_role='Advance under cover' if threat else 'Approach';u.ai_until=g.time+6
                else:self.hold(u,threat,'Guard')
