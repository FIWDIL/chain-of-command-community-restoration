"""Independent capture state for every recovered mission objective."""
from dataclasses import dataclass
import math

@dataclass
class CapturePoint:
    objective: tuple
    title: str = 'Capture point'
    capture_owner: object = None
    capture_side: object = None
    capture_elapsed: float = 0.
    capture_contested: bool = False

    def update(self, units, dt):
        sides={u.side for u in units if u.active and not u.carried_by
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


    def capture_status(self):
        owner='Neutral' if self.capture_owner is None else ('USA','Germany')[self.capture_owner]
        if self.capture_contested:return f'{owner} | Contested'
        if self.capture_side is not None:
            remaining=math.ceil(120-self.capture_elapsed)
            return f'{("USA","Germany")[self.capture_side]} capturing | {remaining//60:02}:{remaining%60:02}'
        return f'{owner} | '+('Capture: 02:00' if self.capture_owner is None else 'Captured')
