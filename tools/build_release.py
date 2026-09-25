"""Build a portable Windows release without modifying the recovered installation."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--work',type=Path,required=True)
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    output=args.output.resolve();work=args.work.resolve();output.mkdir(parents=True,exist_ok=True);work.mkdir(parents=True,exist_ok=True)
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir','--name','ChainOfCommand',
                    '--distpath',str(output),'--workpath',str(work/'pyinstaller'),'--specpath',str(work),
                    '--add-data',str(root/'restoration/bridge.js')+';restoration','--icon',str(root/'original/chain.ico'),
                    '--collect-all','frida',str(root/'launch.py')],check=True,cwd=root)
    dest=output/'ChainOfCommand'
    shutil.copytree(root/'original',dest/'original',dirs_exist_ok=True,ignore=shutil.ignore_patterns('*.log','*.dmp','*.tmp'))
    shutil.copy2(root/'compat/wing32.dll',dest/'original/wing32.dll')
    for folder in ('restoration','compat','docs','tests','tools'):
        shutil.copytree(root/folder,dest/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.lib','*.obj'))
    for name in ('README.md','LICENSE','THIRD_PARTY_NOTICES.md','requirements.txt','launch.py','original-manifest.json'):
        shutil.copy2(root/name,dest/name)
    licenses=dest/'third-party-licenses';licenses.mkdir(exist_ok=True)
    for package in ('frida','pyinstaller'):
        distribution=importlib.metadata.distribution(package)
        for file in distribution.files or ():
            if any(word in str(file).lower() for word in ('license','copying','notice')) and distribution.locate_file(file).is_file():
                target=licenses/package/Path(str(file)).name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(distribution.locate_file(file),target)
    python_license=Path(sys.base_prefix)/'LICENSE.txt'
    if python_license.exists():shutil.copy2(python_license,licenses/'Python-LICENSE.txt')
    manifest={str(p.relative_to(dest)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.rglob('*')) if p.is_file()}
    (dest/'release-manifest.json').write_text(json.dumps(manifest,indent=2))
    archive=output/'ChainOfCommand-OriginalEngine-v0.1.0-Windows.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted(dest.rglob('*')):
            if path.is_file():z.write(path,path.relative_to(output))
    (output/'SHA256SUMS.txt').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
    print(archive)
if __name__=='__main__':main()
