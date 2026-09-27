"""Recovered soldier poses driven by reconstructed, presentation-only transitions.

The images are original. Durations and the state selection below are not a
recovery of the lost client module. They never change combat probabilities.
"""
import math


def play(game, unit, *fields):
    start = game.time
    unit.visual_sequence = []
    master = game.assets.unit_master(unit.side)
    for field in fields:
        image = master[field]['name'].casefold()
        duration = max(.18, game.assets.animation_lengths.get(image, 1) / 10)
        unit.visual_sequence.append((start, start + duration, field))
        start += duration


def transition(game, unit, old, new, running=False):
    if old == new:
        return
    fields = {
        ('stand', 'crouch'): ('UMImageStand-Kneel',),
        ('crouch', 'stand'): ('UMImageKneel-Stand',),
        ('crouch', 'prone'): ('UMImageKneel-Lying',),
        ('prone', 'crouch'): ('UMImageLying-Kneel',),
        ('stand', 'prone'): ('UMImageStand-Kneel', 'UMImageKneel-Lying'),
        ('prone', 'stand'): ('UMImageLying-Kneel', 'UMImageKneel-Stand'),
    }[old, new]
    if old == 'prone' and new == 'stand' and running:
        fields = ('UMImageLyToRun',)
    play(game, unit, *fields)
    unit.visual_stance = new


def cover(game, unit):
    """Classify nearby existing cover; no new cover bonuses are introduced."""
    if unit.path or not unit.active or unit.carrying:
        return ''
    if unit.cell in game.low:
        return 'left' if unit.stance=='prone' else 'barrel_front'
    angle = math.radians(unit.direction)
    facing = math.cos(angle), math.sin(angle)
    candidates = []
    for dx, dy in ((-1,0),(1,0),(0,-1),(0,1)):
        cell = unit.cell[0]+dx, unit.cell[1]+dy
        if cell not in game.low | game.windows | game.solid:
            continue
        forward = dx*facing[0]+dy*facing[1]
        if forward < -.25:
            continue
        side = 'left' if facing[0]*dy-facing[1]*dx >= 0 else 'right'
        candidates.append((forward, ('barrel_' if cell in game.low and unit.stance!='prone' else '')+side))
    return max(candidates, default=(0,''))[1]


def cover_field(unit, action):
    c = unit.visual_cover
    if c.startswith('barrel'):
        if c == 'barrel_front':
            return 'UM_ImageBarrelhhCoverFire' if action == 'fire' else 'UM_ImageBarrelhhCoverAiming'
        return 'UM_ImageBarrel'+('LC' if c.endswith('left') else 'RC')+('Firing' if action == 'fire' else 'Aiming')
    prefix = ('UM_ImageProne' if unit.stance == 'prone' else 'UMImage')+('LC' if c == 'left' else 'RC')
    return prefix+{'idle':'Idle','aim':'Aim','fire':'Fire','enter':'Proc','end':'AimEnd'}[action]


def sync(game, unit):
    # Also catches stance changes made by CPU tactics rather than mouse orders.
    if unit.stance != unit.visual_stance and unit.active:
        transition(game, unit, unit.visual_stance, unit.stance, unit.mode == 'run')
    if unit.stun>0 and not unit.visual_stunned:
        unit.visual_stunned=True
        play(game,unit,'UMImageFall')
    elif unit.stun<=0 and unit.visual_stunned:
        unit.visual_stunned=False
        play(game,unit,'UMImageGetUp')
    aiming=unit.target or unit.visual_enemy
    if aiming != unit.visual_target and not unit.path:
        if aiming:play(game,unit,'UMImageAiming')
        elif unit.visual_target:play(game,unit,'UMImageAimEnd')
        unit.visual_target=aiming
    new = cover(game, unit)
    old = unit.visual_cover
    if new != old:
        unit.visual_cover = new
        if new and not new.startswith('barrel') and unit.stance != 'prone':
            play(game, unit, cover_field(unit, 'enter'))
        elif old and not new and not unit.path and unit.stance != 'prone':
            if old in ('left','right'):
                play(game, unit, 'UMImageLCAimEnd' if old == 'left' else 'UMImageRCAimEnd')
    if unit.active and not unit.path and unit.stress >= .7 and not unit.visual_duck:
        unit.visual_duck = True
        if new in ('left','right') and unit.stance == 'prone':
            play(game, unit, 'UM_ImageProne'+('LC' if new == 'left' else 'RC')+'DuckProc')
        else:
            play(game, unit, 'UMImageProneDuckPr' if unit.stance == 'prone' else 'UMImageDuckProc')
    elif unit.visual_duck and (unit.stress < .45 or unit.path):
        unit.visual_duck = False
        if new in ('left','right') and unit.stance == 'prone':
            play(game, unit, 'UM_ImageProne'+('LC' if new == 'left' else 'RC')+'DuckEnd')
        else:
            play(game, unit, 'UMImageProneDuckEn' if unit.stance == 'prone' else 'UMImageDuckEnd')


def firing(game, unit):
    if unit.visual_cover:
        field = cover_field(unit, 'fire')
    else:
        field = 'UMImageProneFirin' if unit.stance == 'prone' else 'UMImageStandingFi'
    play(game, unit, field)


def field(game, unit):
    # Carrying takes precedence over stale throw/fire state, as in the existing UI.
    for start, end, name in (() if game.winner is not None else unit.visual_sequence):
        if start <= game.time < end:
            return name, game.time-start
    if unit.state == 'KIA':
        return 'UMImageDead'+str(unit.death_pose), 0
    if unit.state == 'WIA':
        return 'UM_ImageWounded'+unit.wound_pose+'St', 0
    if unit.carrying:
        return ('UM_ImageWoundedCarring' if unit.path else 'UM_ImageWoundedCarringIdle'), game.time
    if game.time < unit.anim_until:
        if unit.animation == 'throw':
            # The recovered prone-throw references contain no throwing bitmap;
            # keep the usable recovered throw rather than an invisible placeholder.
            return 'UMImageStThrowGr', game.time
        return ('UMImageProneFirin' if unit.stance == 'prone' else 'UMImageStandingFi'), game.time
    if unit.path:
        return ('UMImageProneMovin' if unit.mode == 'crawl' else 'UMImageStandingMo' if unit.mode == 'run' else 'UMImageWalking'), game.time
    if unit.visual_duck:
        if unit.visual_cover in ('left','right') and unit.stance == 'prone':
            return 'UM_ImageProne'+('LC' if unit.visual_cover == 'left' else 'RC')+'Duck', 0
        return ('UMImageProneDuck' if unit.stance == 'prone' else 'UMImageDucking'), 0
    if unit.visual_cover:
        if unit.visual_cover in ('left','right') and not (unit.target or unit.visual_enemy) and unit.stance != 'prone' and int(game.time+unit.index)%12 < 2:
            return ('UM_ImagePeekLeft' if unit.visual_cover == 'left' else 'UM_ImagePeekRight'), game.time
        return cover_field(unit, 'aim' if unit.target or unit.visual_enemy else 'idle'), game.time
    if unit.target or unit.visual_enemy:
        return ('UMImageProneAimin' if unit.stance == 'prone' else 'UMImageStandingAi'), 0
    if unit.stance == 'prone':
        return ('UM_ImageBreathing' if int(game.time+unit.index)%12 < 3 else 'UMImageProneIdle'), game.time
    if unit.stance == 'crouch':
        return 'UMImageKneel', 0
    phase = int(game.time+unit.index*3)%24
    return ('UMImageStRest'+str(phase//8+1) if phase%8 >= 6 else 'UMImageStIdle'), game.time
