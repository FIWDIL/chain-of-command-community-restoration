import struct,collections

def odf(data):
 pos=0
 def read(fmt):
  nonlocal pos
  v=struct.unpack_from('<'+fmt,data,pos);pos+=struct.calcsize('<'+fmt)
  return v[0] if len(v)==1 else v
 def string():
  nonlocal pos
  n=read('B')
  if n==255:
   n=read('H')
   if n==65535:n=read('I')
  v=data[pos:pos+n].decode('cp1252',errors='replace');pos+=n;return v
 stamp,nt,no=read('IHH');types=[]
 for i in range(nt):
  name=string();parent,flags,total=read('HHH')
  types.append(dict(id=i,name=name,parent=parent,flags=flags,total_properties=total))
 for t in types:
  props=[]
  for _ in range(read('H')):
   name=string();dt,flags,pid=read('BIH')
   assert dt in range(1,7)
   props.append(dict(name=name,datatype=dt,flags=flags,id=pid,reference_type=read('H') if dt in (4,6) else None))
  t['properties']=props
 objects=[]
 while True:
  tid=read('H')
  if tid==65535:
   assert read('B')==0;break
  assert tid<nt
  name=string();uid=read('I');objects.append(dict(type_id=tid,type=types[tid]['name'],name=name,uid=uid))
 def propmap(tid):
  t=types[tid];p=propmap(t['parent']) if t['parent']!=65535 else {}
  p.update({x['id']:x for x in t['properties']});return p
 maps={t['id']:propmap(t['id']) for t in types};lookup={o['uid']:o for o in objects}
 for _ in objects:
  o=lookup[read('I')];props={}
  while True:
   pid=read('H')
   if pid==65535:break
   p=maps[o['type_id']][pid];dt=p['datatype']
   if dt==1:v=read('h')
   elif dt==2:v=read('i')
   elif dt==3:v=string()
   elif dt==4:v={'ref':read('I')}
   elif dt==5:v=read('f')
   elif dt==6:v=[{'ref':read('I')} for _ in range(read('H'))]
   props[p['name']]=v
  o['properties']=props
 trailer_marker=read('I');trailer=string();assert pos==len(data),(pos,len(data))
 for o in objects:
  for v in o['properties'].values():
   for r in (v if isinstance(v,list) else [v]):
    if isinstance(r,dict) and 'ref' in r:r['name']=lookup.get(r['ref'],{}).get('name')
 return dict(header=dict(stamp=stamp,type_count=nt,object_id_limit=no),types=types,objects=objects,trailer_marker=trailer_marker,trailer=trailer,bytes_consumed=pos)

def decode_oix(text):
 out=[]
 for n,line in enumerate(text.splitlines()):
  if line.startswith('='):
   h=line[1:];assert len(h)%2==0
   line=bytes((int(h[i],16)|(int(h[i+1],16)<<4))^((i//2+n)&255) for i in range(0,len(h),2)).decode('cp1252')
  out.append(line)
 return '\n'.join(out)

def parse_oin(text):
 objects={};commands=collections.Counter();other=[]
 for line in text.splitlines():
  if not line or line.startswith(';'):continue
  parts=line.split(',',3);cmd=parts[0];commands[cmd]+=1
  if cmd=='ADDOBJ':
   _,typ,name=parts;objects.setdefault(name,{'name':name,'properties':{}})['type']=typ
  elif cmd=='ADDPROP':
   _,name,prop,value=parts;objects.setdefault(name,{'name':name,'properties':{}})['properties'][prop]=value
  else:other.append(line)
 return dict(commands=dict(commands),objects=list(objects.values()),other_commands=other)
