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
let lastKey=0, lastTime=0;
Interceptor.attach(ptr('0x4a3f40'), {
    onEnter(a) {
        const key=a[0].toInt32()&65535, now=Date.now();
        if(key===lastKey && now-lastTime<150) return;
        lastKey=key;lastTime=now;send({type:'key',key});
    }
});
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
