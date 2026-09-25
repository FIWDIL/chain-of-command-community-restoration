"""Build the four-export x86 GDI shim with LLVM. No Windows SDK headers required."""
import argparse
from pathlib import Path
import subprocess
import tempfile

def main():
    p=argparse.ArgumentParser();p.add_argument('--llvm',type=Path,required=True);args=p.parse_args()
    root=Path(__file__).resolve().parents[1];compat=root/'compat'
    clang=args.llvm/'clang.exe';lld=args.llvm/'lld.exe'
    def run(*cmd):subprocess.run([str(x) for x in cmd],check=True)
    with tempfile.TemporaryDirectory(prefix='coc-wing-') as temp:
        temp=Path(temp);lib=temp/'gdi32.lib';obj=temp/'wing32.obj'
        run(lld,'-flavor','link','/lib',f'/def:{compat/"gdi32.def"}','/machine:x86',f'/out:{lib}')
        run(clang,'--target=i686-pc-windows-msvc','-c','-O2','-fno-stack-protector',compat/'wing32.c','-o',obj)
        aliases=[f'/alternatename:__imp__{name}@{n}=__imp__{name}' for name,n in [('CreateCompatibleDC',4),('CreateDIBSection',24),('BitBlt',36),('CreateHalftonePalette',4),('DeleteDC',4)]]
        run(lld,'-flavor','link','/dll','/noentry','/nodefaultlib','/machine:x86',f'/def:{compat/"wing32.def"}',f'/out:{compat/"wing32.dll"}',f'/implib:{temp/"wing32.lib"}',obj,lib,*aliases)
if __name__=='__main__':main()
