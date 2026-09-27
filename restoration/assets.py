"""Read original ODF/OIX data, then build a native Creation object snapshot."""
import struct
from pathlib import Path
from .formats import odf, decode_oix, parse_oin
from .protocol import string

ROOT_SET = 0x2000ffff
USER = 0x20003001
# Leave the HUD/smoke IDs at 0x3030-0x3042 untouched when allocating 56 soldiers.
UNIT_BASE = 0x20003200
STATUS = 0x20003030
OBJECTIVE = 0x20003031
OBJECTIVE_FLOOR = 0x20003032
OBJECTIVE_FLAG = 0x20003033
EXTRA_OBJECTIVE_BASE = 0x20003a00
DEPLOYMENT_BASE = 0x20003c00
EFFECT_BASE = 0x20003300
# Five flash/cloud pairs plus three smoke clouds for each of 56 soldiers.
EFFECT_COUNT = 728
SMOKE_IMAGE = 0x20003042
DESTINATION_BASE = 0x20003050
DESTINATION_EDGE_BASE = 0x20003060
DESTINATION_FILL_BASE = 0x20003800
DESTINATION_PIP_BASE = 0x20003820

class Assets:
    def __init__(self, original):
        self.original = Path(original)
        definition = self.original/'enginedata.odf'
        if not definition.is_file():definition = self.original/'cocSc.ODF'
        self.definition = odf(definition.read_bytes())
        self.types = {t['name']:t for t in self.definition['types']}
        self.objects = {o['name'].casefold():o for o in self.definition['objects']}
        # Four recovered maps refer to an absent interior-corner image.
        # Keep their files intact and substitute the nearest recovered corner at load time.
        self.objects['img - icor static']=self.objects['img - iwcr static']
        self.objects['img - qcor static']=self.objects['img - wcor static']
        self.objects['img - wh09 static']=self.objects['img - wh01 static']
        self.fields = {p['name']:p for t in self.definition['types'] for p in t['properties']}
        model = self.objects['model']['properties']
        self.grenade_range = float(model['INITMaxGranadeDistance'])
        self.grenade_radius = float(model['GranadeHitDistance'])
        self.grenade_counts = tuple(int(self.objects[name]['properties']['ArmamentGranade'])
                                   for name in ('_hg_unittile_american', '_hg_unittile_german'))
        self.ammo_limits = {self.objects[name]['properties']['Name']:int(self.objects[name]['properties']['AmmoMax$weapon'])
                            for name in ('aw_garand','gw_mauser','aw_bar','gw_mg42','aw_thompson','gw_mp40')}
        self.capture_images = tuple(self.objects['imageshop']['properties'][key]['ref']
                                    for key in ('USAVpImage','GermanyVpImage'))
        self.capture_flags = (self.ref("img - actl static"),self.ref("img - gctl static"))
        self.grenade_image = self.objects['imageshop']['properties']['GranadeExplosion$art']['ref']
        self.by_type = {}
        self.world = self.ref('World')
        self.hud = self.ref('_HG_CommandDialog_Global')
        self.hud_buttons=[o for o in self.definition['objects'] if o['type'] in ('InterfaceButton','ManageButton')
                          and o['properties'].get('World',{}).get('ref')==self.hud]
        # Prefer the main archive; the nested archive contains byte-identical
        # duplicates plus additional recovered maps and mission variants.
        self.model_root=self.original/('models' if (self.original/'models/oin').is_dir() else 'models/cocsc')
        folder=self.model_root/'oin'
        files={}
        for p in sorted(folder.rglob('*'),key=lambda p:(len(p.parts),p.name.casefold())):
            if p.suffix.lower()=='.oix':files.setdefault(p.name.casefold(),p)
        self.map_files={p.stem[:-4]:p for p in files.values() if p.stem.lower().endswith('_map')}
        self.missions={}
        for name,path in self.map_files.items():
            variants=sorted((p for p in files.values() if p.stem.casefold().startswith(name.casefold()+'_')
                             and p.stem[len(name)+1:].isdigit()),key=lambda p:int(p.stem[len(name)+1:]))
            if not variants:self.missions[name]=(path,None)
            for scenario in variants:
                number=int(scenario.stem[len(name)+1:])
                label=name if number==1 else f'{name} / Mission {number}'
                self.missions[label]=(path,scenario)
        if 'stonehouse.oix' in files:
            self.missions['StoneHouse / Alternate layout']=(files['stonehouse.oix'],files.get('stonehouse_1.oix'))
        selected={p for pair in self.missions.values() for p in pair if p}
        self.archive_unselected=sorted(str(p.relative_to(self.original)) for p in files.values() if p not in selected)
        if not self.map_files:raise ValueError('Original map files not found')
        self.motion_objects=[]
        self.motion_frames={}
        self.animation_lengths={}
        self.build_motion_frames()

    def build_motion_frames(self):
        # Use the recovered directional bitmaps, but advance locomotion on the
        # server clock. Native animation can restart on fractional position updates.
        uid=0x20008000
        names=sorted({v['name'].casefold() for side in (0,1) for v in self.unit_master(side).values()
                      if isinstance(v,dict) and v.get('name','').startswith('img - ')})
        for name in names:
            source=self.objects[name]
            if 'mag 8' not in source['properties']:continue
            mag=self.objects[source['properties']['mag 8']['name'].casefold()]
            clips={d:self.objects[v['name'].casefold()] for d,v in mag['properties'].items() if d in ('n','ne','e','se','s','sw','w','nw')}
            count=max(c['properties']['NumFrames'] for c in clips.values())
            self.animation_lengths[name]=count
            if count<=1:continue
            frames=[]
            for index in range(count):
                facets={'Facets':mag['properties']['Facets']}
                for direction,clip in clips.items():
                    p=clip['properties'];props={'NumFrames':1,'iFrame0':p[f"iFrame{index%p['NumFrames']}"]}
                    if 'z Offset' in p:props['z Offset']=p['z Offset']
                    self.motion_objects.append(dict(uid=uid,name=f'LocalMotionClip{uid}',type=clip['type'],properties=props))
                    facets[direction]=uid;uid+=1
                self.motion_objects.append(dict(uid=uid,name=f'LocalMotionMag{uid}',type='MAG',properties=facets));mag_uid=uid;uid+=1
                props={k:v for k,v in source['properties'].items() if k in ('z','x Offset','y Offset','Clip Has Z Offset')}
                props.update({'mag 8':mag_uid,'mag 1':mag_uid})
                self.motion_objects.append(dict(uid=uid,name=f'LocalMotionImage{uid}',type='IMAGE',properties=props))
                frames.append(uid);uid+=1
            self.motion_frames[name]=frames

    def unit_master(self, side):
        return self.objects['_hg_unitmaster_american' if side==0 else '_hg_unitmaster_german']['properties']

    def unit_image(self,game,unit):
        from .presentation import field
        state,elapsed=field(game,unit)
        name=self.unit_master(unit.side)[state]['name'].casefold()
        if name in self.motion_frames:
            frames=self.motion_frames[name]
            locomotion=state in ('UMImageStandingMo','UMImageWalking','UMImageProneMovin','UM_ImageWoundedCarring')
            speed=(10 if unit.mode=='run' else 6 if unit.mode=='crawl' else 8) if locomotion else 10
            return frames[int(elapsed*speed)%len(frames)]
        return self.ref(name)

    @staticmethod
    def unit_name(unit,side,slot,player_names):
        if (unit.side,unit.slot)==(side,slot) or unit.state in ('KIA','Retreated'):
            return ''
        name=player_names.get((unit.side,unit.slot),'')
        return '\x01'+name if name else ''

    @staticmethod
    def capture_ids(index):
        return (OBJECTIVE,OBJECTIVE_FLOOR,OBJECTIVE_FLAG) if index==0 else tuple(EXTRA_OBJECTIVE_BASE+(index-1)*3+i for i in range(3))

    def capture_floor_image(self, side):
        return 0 if side is None else self.capture_images[side]

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
        path,scenario=self.missions[name]
        data = parse_oin(decode_oix(path.read_text(encoding='cp1252')))
        scenario_data = parse_oin(decode_oix(scenario.read_text(encoding='cp1252'))) if scenario else {'objects':[]}
        # Legacy German-HQ floor records contain misspelled references.
        for obj in data['objects']:
            props=obj['properties']
            if props.get('terrain') in ('_HG_Evan','_Evan','_HG_NEvan'):props['terrain']='_HG_Even'
            if props.get('World')=='Worlds':props['World']='World'
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

    def model(self, username, game, side, slot=0, player_names=None):
        new = [dict(uid=0x20003000,name='UserProc '+username,type='UserProcess',properties={'ClientArena':1}),
               dict(uid=USER,name=username,type='user',properties={'Player Type':'user','New World':self.world,'New World View':0})]
        for i, source in enumerate(game.map_objects):
            if 'type' not in source:
                continue
            p = dict(source['properties']);p['OwnerObjectSet'] = ROOT_SET
            new.append(dict(uid=0x20004000+i,name=source['name'],type=source['type'],properties=p))
        new.extend(self.motion_objects)
        for unit in game.units:
            p = {'OwnerObjectSet':ROOT_SET,'Player Type':'Unit','x':round(unit.x),'y':round(unit.y),
                 'World':self.world if game.visible(side,unit) else 0,'Image':self.unit_image(game,unit),'Width':1,'Height':1,'Direction':unit.direction,'z':200,
                 'Helth':unit.health,'Pulses per frame':2,'Animation Loop':1,'No Animation Unless Moving':0,'High Res':1,'fx':unit.x,'fy':unit.y,
                 'Image1':f'img - dot{unit.number+1} static' if unit.side==side and unit.slot==slot and unit.active else 0,'Image2':0,
                 'Text':self.unit_name(unit,side,slot,player_names or {}),
                 'Text Style':'LocalPlayerNameStyle'}
            new.append(dict(uid=unit.uid,name='Soldier '+str(unit.uid),type='Unit',properties=p))
        new.append(dict(uid=STATUS,name='RestorationStatus',type='label',properties={
            'Player Type':'label','World':self.hud,'x':4,'y':109,'Text':game.status(side,slot),'Text Style':'Textstyle - Yellow10','z':10000}))
        for index,point in enumerate((game,*game.extra_objectives)):
            label,floor,flag=self.capture_ids(index)
            common={'World':self.world,'x':point.objective[0],'y':point.objective[1],'Width':1,'Height':1}
            new.append(dict(uid=label,name=f'CaptureLabel{index}',type='TerrainLabel',properties={
                **common,'Player Type':'TerrainLabel','Text':point.capture_status(),'Text Style':'Textstyle - Yellow10','z':10000}))
            new.append(dict(uid=floor,name=f'CaptureFloor{index}',type='PLAYER',properties={
                **common,'Player Type':'PLAYER','z':100,'Figure':13 if point.capture_owner is None else 0,
                'Figure Style':'LocalDestinationPipStyle','Image':self.capture_floor_image(point.capture_owner)}))
            new.append(dict(uid=flag,name=f'CaptureFlag{index}',type='PLAYER',properties={
                **common,'Player Type':'PLAYER','z':200,'Image':self.capture_flags[point.capture_owner] if point.capture_owner is not None else 0}))
        for index,(owner,x,y,img) in enumerate(game.deployment):
            new.append(dict(uid=DEPLOYMENT_BASE+index,name=f'DeploymentTile{index}',type='PLAYER',properties={
                'x':x,'y':y,'Width':1,'Height':1,'z':99,'Image':img,'World':0,'Player Type':'PLAYER'}))
        for number in range(4):
            new.append(dict(uid=DESTINATION_BASE+number,name=f'Destination{number+1}',type='PLAYER',properties={
                'Player Type':'PLAYER','Width':1,'Height':1,'z':199,
                'Image':0}))
            for edge in range(4):
                new.append(dict(uid=DESTINATION_EDGE_BASE+number*4+edge,name=f'DestinationEdge{number+1}_{edge}',type='PLAYER',properties={
                    'Player Type':'PLAYER','Width':1 if edge%2==0 else 0,'Height':0 if edge%2==0 else 1,
                    'z':198,'Figure':1,'Figure Style':'LocalDestinationStyle'}))
            new.append(dict(uid=DESTINATION_FILL_BASE+number,name=f'DestinationFill{number}',type='PLAYER',properties={
                'Player Type':'PLAYER','Width':1,'Height':1,'z':198,'Figure':5+number,'Figure Style':'LocalDestinationFillStyle'}))
            new.append(dict(uid=DESTINATION_PIP_BASE+number,name=f'DestinationPips{number}',type='PLAYER',properties={
                'Player Type':'PLAYER','Width':1,'Height':1,'z':199,'Figure':9+number,'Figure Style':'LocalDestinationPipStyle'}))
        new.extend([
            dict(uid=0x20003054,name='LocalDestinationPen',type='PENSTYLE',properties={'Pen Style':0,'Pen Width':2,'Pen Color':'Color - Red'}),
            dict(uid=0x20003055,name='LocalDestinationStyle',type='FIGURESTYLE',properties={'Pen StyleSet':'LocalDestinationPen'}),
            dict(uid=0x20003810,name='LocalDestinationFillPen',type='PENSTYLE',properties={'Pen Style':0,'Pen Width':3,'Pen Color':'Color - Red'}),
            dict(uid=0x20003811,name='LocalDestinationFillStyle',type='FIGURESTYLE',properties={'Pen StyleSet':'LocalDestinationFillPen'}),
            dict(uid=0x20003812,name='LocalPlayerNameStyle',type='TEXTSTYLE',properties={'Font Bold':1,'Font Size':9,'Color':'Color - Yellow','Font Family':'Arial','Text Format':41,'Grow With Zoom':0}),
            dict(uid=0x20003824,name='LocalDestinationPipPen',type='PENSTYLE',properties={'Pen Style':0,'Pen Width':1,'Pen Color':'Color - Yellow'}),
            dict(uid=0x20003825,name='LocalDestinationPipStyle',type='FIGURESTYLE',properties={'Pen StyleSet':'LocalDestinationPipPen'}),
        ])
        # Reuse the smoke-only middle frames of the recovered explosion; no new art files.
        original_clip=self.objects['clip - exp2 action mag 8 e']['properties']
        smoke_frames={f'iFrame{i}':original_clip[f'iFrame{8+i}'] for i in range(8)}
        smoke_frames['NumFrames']=8
        new.extend([
            dict(uid=0x20003040,name='LocalSmokeClip',type='Misc_mag8_CLIP',properties=smoke_frames),
            dict(uid=0x20003041,name='LocalSmokeMag',type='MAG',properties={'e':0x20003040,'Facets':1}),
            dict(uid=SMOKE_IMAGE,name='LocalSmokeImage',type='IMAGE',properties={'mag 8':0x20003041}),
        ])
        for i in range(EFFECT_COUNT):
            new.append(dict(uid=EFFECT_BASE+i,name=f'LocalEffect{i}',type='PLAYER',properties={
                'x':0,'y':0,'Width':1,'Height':1,'z':500,'Pulses per frame':2,'Image':self.grenade_image}))
        for uid,name,x,y,text in [(0x20003056,'DebriefScore',250,165,''),(0x20003057,'DebriefNote',12,255,'Campaign ranks and promotion points are not available.')]:
            new.append(dict(uid=uid,name=name,type='label',properties={'Player Type':'label','World':self.ref('EndGameScoring'),
                'x':x,'y':y,'z':2000,'Text':text,'Text Style':'Textstyle - Black10','Text Max Pixel Width':520}))
        for row in range(2):
            for column,x in enumerate((342,415,495)):
                new.append(dict(uid=0x20003058+row*3+column,name=f'DebriefPoints{row}_{column}',type='label',properties={'Player Type':'label','World':self.ref('EndGameScoring'),'x':x,'y':165+row*15,'z':2000,'Text':'--','Text Style':'Textstyle - Black10'}))
        lookup = dict(self.objects);lookup.update({o['name'].casefold():o for o in new})
        data = struct.pack('<H',0)
        for o in new:
            data += struct.pack('<I',o['uid'])+string(o['name'])+string(o['type'])
        data += struct.pack('<I',0)
        for o in new:
            data += self.encode_properties(o,lookup)
        # The server owns visibility, so concealed enemies are removed from World per client.
        # Align the American floor art's bitmap origin with the recovered flag/point.
        # This changes only the live model, never the original bitmap bytes.
        modifications = [dict(uid=self.ref('bmp - attl static mag 8 frame 0 e'),type='Misc_mag8_BITMAP',properties={'x Offset':-19,'y Offset':-55}),dict(uid=self.world,type='WORLD',properties={'Line Of Sight Needed':0,'World Initial Top':0,'World Resizable':1,'World Title':'Chain of Command - '+game.map_name}),
                         dict(uid=self.hud,type='WORLD',properties={'World Initial Height':140,'World Initial Top':440,'Height':135})]
        for number in range(1,5):
            modifications.append(dict(uid=self.ref(f'img - dot{number} static'),type='IMAGE',properties={'x Offset':1,'y Offset':0}))
        # Continuous locomotion clips must not stop between network position updates.
        for faction in ('a','g'):
            for motion in ('smo','swk','pmo'):
                obj=self.objects[f'img - {faction}{motion} action']
                modifications.append(dict(uid=obj['uid'],type='IMAGE',properties={'No Anim. Un. Move':0}))
        modifications.append(dict(uid=self.ref('EndGameScoring'),type='WORLD',properties={'World Title':'Mission-End Debriefing','Close Windows':0,'Height':280,'World Initial Height':330,'World Initial Width':575,'World Initial Scrolls':0}))
        for obj in self.definition['objects']:
            p = obj['properties']
            if p.get('World',{}).get('ref')==self.ref('EndGameScoring'):
                pos={axis:int(p.get('transfer'+axis.upper(),p.get(axis+'_static',p.get(axis,0)))) for axis in ('x','y')}
                if obj['type'] in ('PromotionComponents','listbox') or obj['name'] in ('Am_PP to Give','Gm_PP to Give','LDistributePP','LRunningMan','LED_GivePP','LED_PPDistribution','LED_GivePPBlink'):
                    pos['World']=self.ref('_HG_InvisibleWorld_Global')
                    if obj['type']=='listbox':
                        pos.update(WorldReal=self.ref('_HG_InvisibleWorld_Global'),Showable=0,Width=0,Height=0)
                modifications.append(dict(uid=obj['uid'],type=obj['type'],properties=pos))
            if p.get('World',{}).get('ref') == self.hud:
                pos = {axis:int(p.get('transfer'+axis.upper(),p.get(axis+'_static',p.get(axis,0)))) for axis in ('x','y')}
                if obj['type']=='UnitTileInfo':
                    # The missing client module used to reveal live soldier
                    # labels. Preserve their recovered positions and styles.
                    pos.update(Showable=1,z=199 if obj['name'].startswith('_HG_UnitTile_ShowWeapon') else 2000)
                if obj['type']=='PromotionComponents' or obj['name'] in ('Play Again','InterfaceGroup_Promotion','InterfaceGroup_Dinamic','Reinitialize'):
                    pos['World']=0
                if obj['name']=='LStageName':pos.update(Text=f'{game.team_size}v{game.team_size}',x=105)
                modifications.append(dict(uid=obj['uid'],type=obj['type'],properties=pos))
        for o in modifications:
            data += struct.pack('<I',o['uid'])+self.encode_properties(o,lookup,existing=True)
        data += struct.pack('<I',0)
        return (string(username)+struct.pack('<IHHH',self.definition['header']['stamp'],0,0,0)
                +string(str((self.model_root/'map01.bmp').relative_to(self.original)))+struct.pack('<HH',0,0)+string('')+string(str((self.model_root/'defpal.bmp').relative_to(self.original)))
                +string('cocSc')+data+struct.pack('<IHH',0,0,0)+struct.pack('<HHHHIHH',3,0,0,1,100,0,0)+bytes(20))

    def hud_action(self,x,y,finished=False):
        for obj in self.hud_buttons:
            if obj['name']=='Play Again' and not finished:continue
            if obj['name'].startswith('Rotate ') and finished:continue
            p=obj['properties']
            ox=int(p.get('transferX',p.get('x_static',0)));oy=int(p.get('transferY',0))
            if ox<=x<ox+p.get('Width',41) and oy<=y<oy+p.get('Height',17):
                return obj['name'], max(0,min(4,(oy-20)//17))
        if 20<=y<105 and x<55:
            return 'select',max(0,min(4,(y-20)//17))
        return None
