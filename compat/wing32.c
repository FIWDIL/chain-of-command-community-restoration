/* Only the four WinG functions imported by Creation 1.50.0.621.
 * App-local compatibility shim, using the Windows GDI DIB implementation.
 * No Microsoft DLL is copied and no Windows directory is modified. */
typedef void *H;
#define API __stdcall
#define IMPORT __declspec(dllimport)
IMPORT H API CreateCompatibleDC(H);
IMPORT H API CreateDIBSection(H,const void*,unsigned,void**,H,unsigned long);
IMPORT int API BitBlt(H,int,int,int,int,H,int,int,unsigned long);
IMPORT H API CreateHalftonePalette(H);
IMPORT int API DeleteDC(H);
H API WinGCreateDC(void) { return CreateCompatibleDC((H)0); }
H API WinGCreateBitmap(H dc, const void *info, void **bits) {
    return CreateDIBSection(dc,info,0,bits,(H)0,0);
}
int API WinGBitBlt(H dest,int x,int y,int width,int height,H source,int sx,int sy) {
    return BitBlt(dest,x,y,width,height,source,sx,sy,0x00cc0020);
}
H API WinGCreateHalftonePalette(void) {
    H dc=CreateCompatibleDC((H)0), palette=CreateHalftonePalette(dc);
    if(dc) DeleteDC(dc);
    return palette;
}
