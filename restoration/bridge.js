// Input glue for the missing zamCocSc_client module, Creation 1.50.0.621 only.
// No artwork, executable files, or external processes are modified.
function nameOf(p) { try { return p.add(4).readPointer().readCString(); } catch (_) { return ''; } }
Interceptor.attach(ptr('0x4a2250'), {
    onEnter(a) {
        const phase = a[0].toInt32();
        if (phase !== 0 && phase !== 1) return;
        send({type:'mouse',phase,button:a[1].toInt32(),modifiers:a[2].toInt32(),
              x:(a[3].toInt32()<<16)>>16,y:(a[4].toInt32()<<16)>>16,world:nameOf(a[7])});
    }
});
// Orders are issued through the recovered mouse controls.
// This global is the original DisableBrowser preference's fallback value.
// Avoid embedding a retired Internet Explorer lobby; do not write the registry.
ptr('0x55954c').writeU32(1);
Interceptor.attach(ptr('0x4f4154'), {
    onEnter(a) { this.browser=false; try { this.browser=a[0].readCString()==='Creation' && a[1].readCString()==='DisableBrowser'; } catch (_) {} },
    onLeave(r) { if(this.browser) r.replace(1); }
});
Process.setExceptionHandler(d => {
    if(d.type!=='system') send({type:'debug',exception:d.type,address:d.address.toString()});
    return false;
});

// Keep the original MDI views docked inside a normal resizable game window.
// All handles are discovered inside this hash-checked process only.
const user32 = Process.getModuleByName('user32.dll');
// Figures 5-8 fill destination tiles; 9-12 draw their centered yellow pips.
// Use the recovered
// renderer's projected endpoints and clipped back-buffer DC, so camera rotation,
// zoom and scrolling apply exactly as they do to other world figures.
const gdi32=Process.getModuleByName('gdi32.dll');
function gdi(name,result,args){return new NativeFunction(gdi32.getExportByName(name),result,args,'stdcall');}
const selectObject=gdi('SelectObject','pointer',['pointer','pointer']);
const fillPolygon=gdi('Polygon','int',['pointer','pointer','int']);
const redBrush=gdi('CreateSolidBrush','pointer',['uint'])(0xff);
const captureBrush=gdi('CreateSolidBrush','pointer',['uint'])(0x808080);
const yellowBrush=gdi('CreateSolidBrush','pointer',['uint'])(0xffff);
const setRasterMode=gdi('SetROP2','int',['pointer','int']);
// Expand the marker's dirty rectangle as well as its painted area; otherwise
// a vertical diagonal has a one-pixel cache and clips away the red interior.
Interceptor.attach(ptr('0x47c2b2'),{
    onEnter(){
        const figure=this.context.ebp.sub(0x54).readPointer();
        const kind=figure.add(0x60).readS16();if(kind<5 || kind>13)return;
        const x=figure.add(0x64).readS32(),y=figure.add(0x68).readS32();
        const tx=figure.add(0x6c).readS32(),ty=figure.add(0x70).readS32();
        const dx=Math.abs(tx-x),dy=Math.abs(ty-y);
        if(kind===13){
            const rx=dx===0?dy:dx/2,ry=dx===0?dy/2:dx/4;
            figure.add(0x1c).writeS32(Math.floor(x-rx-2));figure.add(0x20).writeS32(Math.floor(y-ry-2));
            figure.add(0x28).writeS32(Math.ceil(rx*2+5));figure.add(0x2c).writeS32(Math.ceil(ry*2+5));return;
        }
        if(dx===0 && dy>0){
            figure.add(0x1c).writeS32(x-dy-2);figure.add(0x20).writeS32(Math.min(y,ty)-2);
            figure.add(0x28).writeS32(2*dy+5);figure.add(0x2c).writeS32(dy+5);
        }else if(dy===0 && dx>0){
            figure.add(0x1c).writeS32(Math.min(x,tx)-2);figure.add(0x20).writeS32(y-Math.ceil(dx/4)-2);
            figure.add(0x28).writeS32(dx+5);figure.add(0x2c).writeS32(Math.ceil(dx/2)+5);
        }
    }
});
Interceptor.attach(ptr('0x47b814'),{
    onEnter(){
        const stack=this.context.ebp,figure=stack.sub(0xdc).readPointer();
        const kind=figure.add(0x60).readS16();if(kind<5 || kind>13)return;
        const dc=stack.sub(0x54).readPointer().add(4).readPointer();
        const x=stack.sub(0x4c).readS32(),y=stack.sub(0x48).readS32();
        const tx=stack.sub(0x44).readS32(),ty=stack.sub(0x40).readS32();
        const dx=tx-x,dy=ty-y;if((dx!==0 && dy!==0) || (dx===0 && dy===0))return;
        const mx=(x+tx)/2,my=(y+ty)/2;
        const points=dx===0?[[x,y],[mx+Math.abs(dy),my],[tx,ty],[mx-Math.abs(dy),my]]:
            [[x,y],[mx,my+Math.abs(dx)/4],[tx,ty],[mx,my-Math.abs(dx)/4]];
        if(kind===13)points.forEach(p=>{p[0]+=x-mx;p[1]+=y-my;});
        const buffer=Memory.alloc(32);points.forEach((p,i)=>{buffer.add(i*8).writeS32(Math.round(p[0]));buffer.add(i*8+4).writeS32(Math.round(p[1]));});
        const previousRaster=setRasterMode(dc,13);
        const previous=selectObject(dc,kind===13?captureBrush:kind<9?redBrush:yellowBrush);
        if(kind<9 || kind===13)fillPolygon(dc,buffer,4);
        else{
            const count=kind-8;
            for(let i=0;i<count;i++){
                const px=Math.round(mx+(i-(count-1)/2)*5),py=Math.round(my),dot=Memory.alloc(32);
                [[px-1,py-1],[px+1,py-1],[px+1,py+1],[px-1,py+1]].forEach((p,j)=>{dot.add(j*8).writeS32(p[0]);dot.add(j*8+4).writeS32(p[1]);});
                fillPolygon(dc,dot,4);
            }
        }
        selectObject(dc,previous);setRasterMode(dc,previousRaster);
    }
});
for(const api of ['GetMessageA','GetMessageW','PeekMessageA','PeekMessageW']) {
    Interceptor.attach(user32.getExportByName(api),{
        onEnter(a){this.message=a[0];},
        onLeave(result){
            if(result.toInt32()<=0 || this.message.isNull())return;
            const message=this.message.add(4).readU32();
            if(message===0x20a || message===0x20e)this.message.add(4).writeU32(0);
        }
    });
}
function winapi(name, result, args) {
    return new NativeFunction(user32.getExportByName(name), result, args, 'stdcall');
}
const windowText = winapi('GetWindowTextW','int',['pointer','pointer','int']);
const className = winapi('GetClassNameW','int',['pointer','pointer','int']);
const windowPid = winapi('GetWindowThreadProcessId','uint',['pointer','pointer']);
const parentOf = winapi('GetParent','pointer',['pointer']);
const clientRect = winapi('GetClientRect','int',['pointer','pointer']);
const moveWindow = winapi('MoveWindow','int',['pointer','int','int','int','int','int']);
const getStyle = winapi('GetWindowLongW','long',['pointer','int']);
const setStyle = winapi('SetWindowLongW','long',['pointer','int','long']);
const setPosition = winapi('SetWindowPos','int',['pointer','pointer','int','int','int','int','uint']);
const showWindow = winapi('ShowWindow','int',['pointer','int']);
const setTitle = winapi('SetWindowTextW','int',['pointer','pointer']);
const enumWindows = winapi('EnumWindows','int',['pointer','pointer']);
const enumChildren = winapi('EnumChildWindows','int',['pointer','pointer','pointer']);
const sendWindowMessage=winapi('SendMessageW','long',['pointer','uint','uint','pointer']);
const loadImage=winapi('LoadImageW','pointer',['pointer','pointer','uint','int','int','uint']);
const setClassValue=winapi('SetClassLongW','uint',['pointer','int','long']);
const iconPath=Memory.allocUtf16String(typeof restorationIconPath==='string'?restorationIconPath:'');
const smallIcon=loadImage(ptr(0),iconPath,1,16,16,0x10);
const largeIcon=loadImage(ptr(0),iconPath,1,32,32,0x10);
const iconWindows=new Set();
const debriefWindows=new Set();
function replaceIcon(h) {
    if(iconWindows.has(h.toString()) || smallIcon.isNull() || largeIcon.isNull())return;
    iconWindows.add(h.toString());
    setClassValue(h,-14,largeIcon.toInt32());setClassValue(h,-34,smallIcon.toInt32());
    sendWindowMessage(h,0x80,0,smallIcon);sendWindowMessage(h,0x80,1,largeIcon);
}
function readWindow(h, fn) { const b=Memory.alloc(1024);fn(h,b,512);return b.readUtf16String(); }
function cleanTitle(text) {
    if (!/2am/i.test(text)) return text;
    if (/creation/i.test(text)) return 'Chain of Command - Community Restoration';
    return text.replace(/2am\s*(games?)?\s*[:\-]?\s*/ig,'').trim() || 'Chain of Command';
}
// Sanitize future title changes too, including the legacy chat window title.
for (const suffix of ['A','W']) {
    Interceptor.attach(user32.getExportByName('SetWindowText'+suffix), {
        onEnter(a) {
            if(a[1].isNull()) return;
            if(['edit','static','button'].includes(readWindow(a[0],className).toLowerCase()))return;
            const old=suffix==='W'?a[1].readUtf16String():a[1].readCString();
            const text=cleanTitle(old);
            if(text!==old) {this.title=suffix==='W'?Memory.allocUtf16String(text):Memory.allocAnsiString(text);a[1]=this.title;}
        }
    });
}
let frame=null, mdi=null, commandView=null, fieldView=null, fieldPane=null, lastLayout='';
const discoverChild=new NativeCallback((h,l)=>{
    const cls=readWindow(h,className), title=readWindow(h,windowText);
    if(cls==='MDIClient') mdi=h;
    if(fieldView && parentOf(h).equals(fieldView))fieldPane=h;
    if(title==='Choose a Command') commandView=h;
    if(title==='Mission-End Debriefing' && !debriefWindows.has(h.toString()) && frame) {
        debriefWindows.add(h.toString());
        const r=Memory.alloc(16);clientRect(frame,r);
        setStyle(h,-16,(getStyle(h,-16)|0x00c80000)&~0x01030000);
        setPosition(h,ptr(0),Math.max(0,Math.floor((r.add(8).readS32()-575)/2)),20,575,330,0x30);
    }
    if(title.startsWith('Chain of Command - ') && !parentOf(h).equals(ptr(0))) fieldView=h;
    if(/2am/i.test(title) && !['edit','static','button'].includes(cls.toLowerCase())) setTitle(h,Memory.allocUtf16String(cleanTitle(title)));
    if(cls.startsWith('Afx:'))replaceIcon(h);
    // The retired sponsor/browser strip has no use in local matches.
    if(frame && parentOf(h).equals(frame) && cls==='#32770') showWindow(h,0);
    return 1;
},'int',['pointer','pointer'],'stdcall');
const discoverFrame=new NativeCallback((h,l)=>{
    const p=Memory.alloc(4);windowPid(h,p);
    if(p.readU32()!==Process.id) return 1;
    const title=readWindow(h,windowText), cls=readWindow(h,className);
    replaceIcon(h);
    if(/2am/i.test(title))setTitle(h,Memory.allocUtf16String(cleanTitle(title)));
    if(cls.startsWith('Afx:') && parentOf(h).isNull()) {
        frame=h;
        const style=getStyle(h,-16), wanted=style|0x00040000|0x00010000;
        if(style!==wanted) {setStyle(h,-16,wanted);setPosition(h,ptr(0),0,0,0,0,0x37);}
        if(/2am/i.test(title))setTitle(h,Memory.allocUtf16String(cleanTitle(title)));
        enumChildren(h,discoverChild,ptr(0));
    }
    return 1;
},'int',['pointer','pointer'],'stdcall');
setInterval(()=>{
    enumWindows(discoverFrame,ptr(0));
    if(!frame || !mdi || !commandView || !fieldView) return;
    const r=Memory.alloc(16);clientRect(frame,r);
    const width=r.add(8).readS32(),height=r.add(12).readS32();
    if(width<1 || height<1)return;
    const key=[frame,mdi,commandView,fieldView,fieldPane,width,height,chatPanel].join(':');
    // MoveWindow is only called when geometry changes; avoid resetting animation each tick.
    if(key===lastLayout)return;
    lastLayout=key;
    const stacked=width<930,bar=stacked?260:140;
    moveWindow(mdi,0,0,width,height,1);
    // A maximized MDI child ignores a smaller height and covers its own scrollbar.
    if(getStyle(fieldView,-16)&0x01000000)sendWindowMessage(mdi,0x223,fieldView.toUInt32(),ptr(0));
    moveWindow(fieldView,0,0,width,Math.max(1,height-bar),1);
    if(fieldPane) {
        const inner=Memory.alloc(16);clientRect(fieldView,inner);
        moveWindow(fieldPane,0,0,inner.add(8).readS32(),inner.add(12).readS32(),1);
    }
    moveWindow(commandView,0,Math.max(0,height-bar),stacked?width:609,140,1);
    if(chatPanel) {
        const x=stacked?0:609,y=stacked?height-120:height-140,w=stacked?width:width-609,h=stacked?120:140;
        setPosition(chatPanel,ptr(0),x,Math.max(0,y),w,h,0x10);
        moveWindow(chatTranscript,6,31,Math.max(1,w-12),h-65,1);
        moveWindow(orderButton,6,3,80,24,1);moveWindow(channelButton,92,3,Math.max(90,w-190),24,1);moveWindow(roomButton,w-92,3,86,24,1);
        moveWindow(chatInput,6,h-29,Math.max(1,w-78),24,1);
        moveWindow(chatSend,Math.max(6,w-66),h-29,60,24,1);
        sendWindowMessage(chatTranscript,0xb7,0,ptr(0));
    }
},150);

// A local native message panel, backed by the restoration's room chat.
// Controls are created/updated on the game's UI thread, never the network reader.
let chatPanel=null,chatTranscript=null,chatInput=null,chatSend=null,pendingChat='';
let orderButton=null,channelButton=null,roomButton=null,roomState={},chatChannel='room',chatRecipient='';
const getFocus=winapi('GetFocus','pointer',[]);
function typingChat() {
    if(!chatInput)return false;
    const focus=getFocus();return focus.equals(chatInput)||focus.equals(chatTranscript);
}
const createWindow=winapi('CreateWindowExW','pointer',['uint','pointer','pointer','uint','int','int','int','int','pointer','pointer','pointer','pointer']);
const changeProcedure=winapi('SetWindowLongW','long',['pointer','int','long']);
const callProcedure=winapi('CallWindowProcW','long',['pointer','pointer','uint','uint','pointer']);
let originalPanelProc=null,originalInputProc=null;
let originalFieldProc=null;
const fieldProc=new NativeCallback((h,msg,w,l)=>{
    if(msg===0x20a || msg===0x20e)return 0;
    if(msg===0x46 && frame && !l.isNull()) {
        const r=Memory.alloc(16);clientRect(frame,r);
        const width=r.add(8).readS32(),height=r.add(12).readS32();
        if(!(l.add(24).readU32()&1))l.add(20).writeS32(Math.max(1,height-(width<930?260:140)));
    }
    return callProcedure(originalFieldProc,h,msg,w,l);
},'long',['pointer','uint','uint','pointer'],'stdcall');
function submitChat() {
    const b=Memory.alloc(2048);windowText(chatInput,b,1024);const text=b.readUtf16String().trim();
    if(text) {send({type:'chat',text:text.slice(0,240),channel:chatChannel,recipient:chatRecipient});setTitle(chatInput,Memory.allocUtf16String(''));}
}
const panelProc=new NativeCallback((h,msg,w,l)=>{
    if(msg===0x111 && (w>>>16)===0) {
        const id=w&65535;
        if(id===4001){submitChat();return 0;}
        if(id===4002){showOrders();return 0;}
        if(id===4003){chooseChannel();return 0;}
        if(id===4004){send({type:'ui',action:'room'});return 0;}
    }
    return callProcedure(originalPanelProc,h,msg,w,l);
},'long',['pointer','uint','uint','pointer'],'stdcall');
const inputProc=new NativeCallback((h,msg,w,l)=>{
    if(msg===0x100 && w===13) {submitChat();return 0;}
    if(msg===0x102 && w===13)return 0;
    return callProcedure(originalInputProc,h,msg,w,l);
},'long',['pointer','uint','uint','pointer'],'stdcall');
function createChat() {
    if(!frame || !commandView || !fieldView || chatPanel)return;
    originalFieldProc=ptr(changeProcedure(fieldView,-4,fieldProc.toInt32())>>>0);
    const cls=n=>Memory.allocUtf16String(n),empty=Memory.allocUtf16String('');
    chatPanel=createWindow(0,cls('STATIC'),empty,0x56000000,0,0,300,140,frame,ptr(0),Process.mainModule.base,ptr(0));
    if(chatPanel.isNull()) {chatPanel=null;return;}
    originalPanelProc=ptr(changeProcedure(chatPanel,-4,panelProc.toInt32())>>>0);
    chatTranscript=createWindow(0x200,cls('EDIT'),empty,0x50a00844,6,5,288,101,chatPanel,ptr(0),Process.mainModule.base,ptr(0));
    chatInput=createWindow(0x200,cls('EDIT'),empty,0x50800080,6,111,222,24,chatPanel,ptr(4000),Process.mainModule.base,ptr(0));
    chatSend=createWindow(0,cls('BUTTON'),cls('Send'),0x50010000,234,111,60,24,chatPanel,ptr(4001),Process.mainModule.base,ptr(0));
    orderButton=createWindow(0,cls('BUTTON'),cls('Orders'),0x50010000,6,3,80,24,chatPanel,ptr(4002),Process.mainModule.base,ptr(0));
    channelButton=createWindow(0,cls('BUTTON'),cls('Chat: Room'),0x50010000,92,3,110,24,chatPanel,ptr(4003),Process.mainModule.base,ptr(0));
    roomButton=createWindow(0,cls('BUTTON'),cls('Lobby'),0x50010000,208,3,86,24,chatPanel,ptr(4004),Process.mainModule.base,ptr(0));
    originalInputProc=ptr(changeProcedure(chatInput,-4,inputProc.toInt32())>>>0);
    sendWindowMessage(chatInput,0xc5,240,ptr(0));
    const stock=new NativeFunction(Process.getModuleByName('gdi32.dll').getExportByName('GetStockObject'),'pointer',['int'],'stdcall');
    const font=stock(17);
    for(const h of [chatTranscript,chatInput,chatSend,orderButton,channelButton,roomButton])sendWindowMessage(h,0x30,font.toUInt32(),ptr(1));
    lastLayout='';
}
function receiveChat() {
    recv('chat_display',message=>{pendingChat=message.text;receiveChat();});
}
receiveChat();
Interceptor.attach(user32.getExportByName('DispatchMessageA'),{
    onEnter(a) {
        // Consume vertical and horizontal wheel messages before MFC routes them
        // to a view or scrollbar. Explicit scrollbar dragging remains available.
        if(!a[0].isNull()) {
            const message=a[0].add(4).readU32();
            if(message===0x20a || message===0x20e)a[0].add(4).writeU32(0);
        }
        createChat();
        if(chatTranscript && pendingChat!==null) {
            setTitle(chatTranscript,Memory.allocUtf16String(pendingChat));
            sendWindowMessage(chatTranscript,0xb1,pendingChat.length,ptr(pendingChat.length));
            sendWindowMessage(chatTranscript,0xb7,0,ptr(0));pendingChat=null;
        }
    }
});

// Native mouse menus keep every restored action available without gameplay hotkeys.
const createMenu=winapi('CreatePopupMenu','pointer',[]);
const appendMenu=winapi('AppendMenuW','int',['pointer','uint','uint','pointer']);
const popupMenu=winapi('TrackPopupMenuEx','uint',['pointer','uint','int','int','pointer','pointer']);
const destroyMenu=winapi('DestroyMenu','int',['pointer']);
const getWindowRect=winapi('GetWindowRect','int',['pointer','pointer']);
function pickMenu(button,entries) {
    const menu=createMenu(),r=Memory.alloc(16);getWindowRect(button,r);
    entries.forEach((entry,i)=>appendMenu(menu,0,i+1,Memory.allocUtf16String(entry[0])));
    const choice=popupMenu(menu,0x100,r.readS32(),r.add(12).readS32(),chatPanel,ptr(0));
    destroyMenu(menu);return choice?entries[choice-1]:null;
}
function showOrders() {
    const entries=[['All four soldiers','all'],['Soldier 1','select0'],['Soldier 2','select1'],['Soldier 3','select2'],['Soldier 4','select3'],
        ['Walk to','walk'],['Run to','run'],['Assault','assault'],['Crawl to','crawl'],['Stop','stop'],['Stand','stand'],['Crouch','crouch'],['Prone','prone'],
        ['Fire at','fire'],['Face','face'],['Fragmentation grenade','grenade'],['Smoke grenade','smoke'],['Hold fire','hold'],['Fire at will','free'],
        ['Carry / put down wounded','carry'],['Center soldiers','center'],['Show capture point','objective'],['Cancel targeting','cancel'],['Withdraw selected soldiers','retreat']];
    if(roomState.owner && roomState.finished)entries.push(['Return to lobby for next match','lobby']);
    const picked=pickMenu(orderButton,entries);if(!picked)return;
    const action=picked[1];
    if(action==='all')send({type:'command',action:'select',indices:[0,1,2,3]});
    else if(action.startsWith('select'))send({type:'command',action:'select',indices:[Number(action.slice(6))]});
    else send({type:'command',action});
}
function chooseChannel() {
    const entries=[['Everyone in the room','room',''],['My team','team','']];
    for(const team of roomState.teams||[])for(const group of team.fireteams)if(group.player)entries.push(['Private: '+group.name,'whisper',group.player]);
    const picked=pickMenu(channelButton,entries);if(!picked)return;
    chatChannel=picked[1];chatRecipient=picked[2];setTitle(channelButton,Memory.allocUtf16String(picked[0]));
}
function receiveRoom() {recv('room_state',message=>{roomState=message.state;receiveRoom();});}
receiveRoom();


// A leading control byte identifies owner labels, without matching player names
// against unrelated map labels. Center measured text over the soldier's head.
const textExtent=gdi('GetTextExtentPoint32A','int',['pointer','pointer','int','pointer']);
Interceptor.attach(ptr('0x47bbe0'),{onEnter(){
    const bp=this.context.ebp,text=bp.sub(0xd8).readPointer(),count=bp.sub(0xd4).readS32();
    if(count<2 || text.readU8()!==1)return;
    const reg=bp.sub(0xdc).readPointer(),dc=bp.sub(0x70).readPointer().add(4).readPointer();
    const size=Memory.alloc(8);if(!textExtent(dc,text.add(1),count-1,size))return;
    const scale=reg.add(0x78).readPointer().add(0x4c).readS16()/8;
    const width=size.readS32(),height=size.add(4).readS32();
    const center=bp.sub(0x88).readS32()+55*scale,bottom=bp.sub(0x84).readS32()+40*scale;
    bp.sub(0x88).writeS32(Math.round(center-width/2));bp.sub(0x80).writeS32(Math.round(center+width/2)+1);
    bp.sub(0x84).writeS32(Math.round(bottom-height));bp.sub(0x7c).writeS32(Math.round(bottom));
    bp.sub(0xd8).writePointer(text.add(1));bp.sub(0xd4).writeS32(count-1);
}});
