"""Four-soldier player slots, recovered weapon caps, and reconstructed side pools."""
MAX_SLOTS = 7
SOLDIERS_PER_SLOT = 4


def validate_size(size):
    if type(size) is not int or not 1 <= size <= MAX_SLOTS:
        raise ValueError('Choose between 1 and 7 fireteams per side')
    return size


def default_pool(size):
    """Balance defaults, NOT a recovered 2AM stockpile formula."""
    validate_size(size)
    return {'MG': (size + 1) // 2, 'SMG': size // 3}


def weapon_caps(assets, side):
    names = ('AW_BAR', 'AW_Thompson') if side == 0 else ('GW_MG42', 'GW_MP40')
    return {kind: int(assets.objects[name.casefold()]['properties']['INIT_LimitPerSquad'])
            for kind, name in zip(('MG', 'SMG'), names)}


def loadouts(assets, size, side, pool=None):
    """Allocate a finite side stockpile without duplicating it for each player.

    The original word 'Squad' is interpreted as the four-soldier player group.
    The lost assignment routine has not been recovered; allocation is automatic.
    """
    validate_size(size)
    pool = dict(default_pool(size) if pool is None else pool)
    caps = weapon_caps(assets, side)
    if set(pool) != {'MG', 'SMG'}:
        raise ValueError('Stockpile must specify MG and SMG quantities')
    for kind in caps:
        if type(pool[kind]) is not int or not 0 <= pool[kind] <= caps[kind] * size:
            raise ValueError(f'{kind} stockpile exceeds {caps[kind]} per fireteam')
    rifle, mg, smg = ('Garand', 'BAR', 'Thompson') if side == 0 else ('Mauser', 'MG42', 'MP40')
    result = [[rifle] * SOLDIERS_PER_SLOT for _ in range(size)]
    # Spread MGs across the side, then favor rifle-only groups for SMGs.
    mg_order = list(range(0, size, 2)) + list(range(1, size, 2))
    for slot in mg_order[:pool['MG']]:
        result[slot][3] = mg
    smg_order = sorted(range(size), key=lambda slot: (mg in result[slot], slot))
    remaining = pool['SMG']
    for number in range(caps['SMG']):
        for slot in smg_order:
            if not remaining:
                break
            result[slot][2-number] = smg
            remaining -= 1
    return result
