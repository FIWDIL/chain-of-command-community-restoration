"""Read original ODF/OIX data, then build a native Creation object snapshot."""
import struct
from pathlib import Path
from .formats import odf, decode_oix, parse_oin
from .protocol import string

ROOT_SET = 0x2000ffff
USER = 0x20003001
UNIT_BASE = 0x20003010
STATUS = 0x20003030
OBJECTIVE = 0x20003031
EFFECT_BASE = 0x20003100
SMOKE_IMAGE = 0x20003042

class Assets:
    def __init__(self, original):
        self.original = Path(original)
        self.definition = odf((self.original/'cocSc.ODF').read_bytes())
        self.types = {t['name']:t for t in self.definition['types']}
        self.objects = {o['name'].casefold():o for o in self.definition['objects']}
        # Four recovered maps refer to an absent interior-corner image.
        # Keep their files intact and substitute the nearest recovered corner at load time.
        self.objects['img - icor static']=self.objects['img - iwcr static']
        self.objects['img - qcor static']=self.objects['img - wcor static']
        self.objects['img - wh09 static']=self.objects['img - wh01 static']
        self.fields = {p['name']:p for t in self.definition['types'] for p in t['properties']}
        self.by_type = {}
        self.world = self.ref('World')
        self.hud = self.ref('_HG_CommandDialog_Global')
        self.map_files = {p.stem[:-4]:p for p in (self.original/'models/cocsc/oin').glob('*') if p.stem.lower().endswith('_map') and p.suffix.lower()=='.oix'}
        if not self.map_files:
            raise ValueError('Original map files not found')

    def ref(self, name):
        return self.objects[name.casefold()]['uid']

    def fields_for(self, name):
        if name not in self.by_type:
            t = self.types[name]
            result = dict(self.fields_for(self.definition['types'][t['parent']]['name'])) if t['parent']!=65535 else {}
            result.update({p['name']:p for p in t['properties']})
            self.by_type[name] = result
        return self.by_type[name]

    def read_map(self, name):
        path = self.map_files[name]
        data = parse_oin(decode_oix(path.read_text(encoding='cp1252')))
        scenario = next((p for p in path.parent.iterdir() if p.stem.casefold()==name.casefold()+'_1' and p.suffix.lower()=='.oix'), None)
        scenario_data = parse_oin(decode_oix(scenario.read_text(encoding='cp1252'))) if scenario else {'objects':[]}
        return data['objects'], scenario_data['objects']

    def encode_properties(self, obj, lookup, existing=False):
        result = bytearray()
        schema = self.fields_for(obj['type'])
        for name, value in obj['properties'].items():
            if name not in schema:
                continue
            prop = schema[name]; dt = prop['datatype']
            if existing and dt==4 and value==0:
                result += struct.pack('<HB',prop['id'],0)
                continue
            if dt in (1,2):
                packed = struct.pack('<h' if dt==1 else '<i', int(value))
            elif dt==3:
                packed = string(str(value))
            elif dt==4:
                ref = value['ref'] if isinstance(value,dict) else value if isinstance(value,int) else lookup[value.casefold()]['uid']
                packed = struct.pack('<I',ref)
            elif dt==5:
                packed = struct.pack('<f',float(value))
            elif dt==6:
                packed = struct.pack('<H',len(value))+b''.join(struct.pack('<I',v['ref']) for v in value)
            result += struct.pack('<H',prop['id']) + (b'\x01' if existing else b'') + packed
        return bytes(result)+b'\xff\xff'

    def model(self, username, game, side):
        new = [dict(uid=0x20003000,name='UserProc '+username,type='UserProcess',properties={'ClientArena':1}),
               dict(uid=USER,name=username,type='user',properties={'Player Type':'user','New World':self.world,'New World View':0})]
        for i, source in enumerate(game.map_objects):
            if 'type' not in source:
                continue
            p = dict(source['properties']);p['OwnerObjectSet'] = ROOT_SET
            new.append(dict(uid=0x20004000+i,name=source['name'],type=source['type'],properties=p))
        for unit in game.units:
            p = {'OwnerObjectSet':ROOT_SET,'Player Type':'Unit','x':round(unit.x),'y':round(unit.y),
                 'World':self.world if game.visible(side,unit) else 0,'Image':game.image(unit),'Width':1,'Height':1,'Direction':unit.direction,
                 'Helth':unit.health,'Pulses per frame':2,'Text':str(unit.index+1) if unit.side==side else '',
                 'Text Style':'Textstyle - Yellow10'}
            new.append(dict(uid=unit.uid,name='Soldier '+str(unit.uid),type='Unit',properties=p))
        new.append(dict(uid=STATUS,name='RestorationStatus',type='label',properties={
            'Player Type':'label','World':self.hud,'x':4,'y':109,'Text':game.status(side),'Text Style':'Textstyle - Yellow10','z':10000}))
        new.append(dict(uid=OBJECTIVE,name='RestorationObjective',type='TerrainLabel',properties={
            'World':self.world,'x':game.objective[0],'y':game.objective[1],'Width':1,'Height':1,
            'Player Type':'TerrainLabel','Text':'CONTROL POINT','Text Style':'Textstyle - Yellow10','z':10000}))
        # Reuse the smoke-only middle frames of the recovered explosion; no new art files.
        original_clip=self.objects['clip - exp2 action mag 8 e']['properties']
        smoke_frames={f'iFrame{i}':original_clip[f'iFrame{8+i}'] for i in range(8)}
        smoke_frames['NumFrames']=8
        new.extend([
            dict(uid=0x20003040,name='LocalSmokeClip',type='Misc_mag8_CLIP',properties=smoke_frames),
            dict(uid=0x20003041,name='LocalSmokeMag',type='MAG',properties={'e':0x20003040,'Facets':1}),
            dict(uid=SMOKE_IMAGE,name='LocalSmokeImage',type='IMAGE',properties={'mag 8':0x20003041}),
        ])
        for i in range(32):
            new.append(dict(uid=EFFECT_BASE+i,name=f'LocalEffect{i}',type='PLAYER',properties={
                'x':0,'y':0,'Width':1,'Height':1,'z':500,'Pulses per frame':2,'Image':'img - exp2 action'}))
        lookup = dict(self.objects);lookup.update({o['name'].casefold():o for o in new})
        data = struct.pack('<H',0)
        for o in new:
            data += struct.pack('<I',o['uid'])+string(o['name'])+string(o['type'])
        data += struct.pack('<I',0)
        for o in new:
            data += self.encode_properties(o,lookup)
        # The server owns visibility, so concealed enemies are removed from World per client.
        modifications = [dict(uid=self.world,type='WORLD',properties={'Line Of Sight Needed':0,'World Initial Top':140,'World Title':'Chain of Command - '+game.map_name}),
                         dict(uid=self.hud,type='WORLD',properties={'World Initial Height':140,'Height':135})]
        for obj in self.definition['objects']:
            p = obj['properties']
            if p.get('World',{}).get('ref') == self.hud:
                pos = {axis:int(p.get('transfer'+axis.upper(),p.get(axis+'_static',p.get(axis,0)))) for axis in ('x','y')}
                if obj['type']=='PromotionComponents' or obj['name'] in ('Play Again','Chat','InterfaceGroup_Promotion','InterfaceGroup_Dinamic','Reinitialize','Commander Assignment','Weapon Assignment'):
                    pos['World']=0
                if obj['name']=='LStageName':pos['Text']='Local match'
                modifications.append(dict(uid=obj['uid'],type=obj['type'],properties=pos))
        for o in modifications:
            data += struct.pack('<I',o['uid'])+self.encode_properties(o,lookup,existing=True)
        data += struct.pack('<I',0)
        return (string(username)+struct.pack('<IHHH',self.definition['header']['stamp'],0,0,0)
                +string('models\\cocsc\\map01.bmp')+struct.pack('<HH',0,0)+string('')+string('models\\cocsc\\defpal.bmp')
                +string('cocSc')+data+struct.pack('<IHH',0,0,0)+struct.pack('<HHHHIHH',3,0,0,1,100,0,0)+bytes(20))

    def hud_action(self,x,y):
        for obj in self.definition['objects']:
            p=obj['properties']
            if p.get('World',{}).get('ref')!=self.hud or obj['type'] not in ('InterfaceButton','ManageButton'):
                continue
            ox=int(p.get('transferX',p.get('x_static',0)));oy=int(p.get('transferY',0))
            if ox<=x<ox+p.get('Width',41) and oy<=y<oy+p.get('Height',17):
                return obj['name'], max(0,min(4,(oy-20)//17))
        if 20<=y<105 and x<55:
            return 'select',max(0,min(4,(y-20)//17))
        return None
