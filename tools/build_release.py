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
from guard_engine import guarded_engine

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--work',type=Path,required=True)
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    output=args.output.resolve();work=args.work.resolve();output.mkdir(parents=True,exist_ok=True);work.mkdir(parents=True,exist_ok=True)
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir','--name','CoC Restored+',
                    '--distpath',str(output),'--workpath',str(work/'pyinstaller'),'--specpath',str(work),
                    '--add-data',str(root/'restoration/bridge.js')+';restoration',
                    '--add-data',str(root/'restoration/community.ico')+';restoration','--icon',str(root/'restoration/community.ico'),
                    '--collect-all','frida',str(root/'launch.py')],check=True,cwd=root)
    dest=output/'CoC Restored+'
    shutil.copytree(root/'game',dest/'game',dirs_exist_ok=True,ignore=shutil.ignore_patterns('*.log','*.dmp','*.tmp'))
    # Reproduce the audited player-file cleanup without touching preserved inputs.
    exclusions=json.loads((root/'tools/runtime-exclusions.json').read_text())
    for name in exclusions:
        path=(dest/name).resolve()
        if not path.is_relative_to(dest.resolve()) or Path(name).parts[0] not in ('game','_internal'):
            raise ValueError('Invalid runtime exclusion: '+name)
        if path.is_file():path.unlink()
    for path in sorted(dest.rglob('*'),key=lambda p:len(p.parts),reverse=True):
        if path.is_dir() and not any(path.iterdir()):path.rmdir()
    shutil.copy2(root/'compat/wing32.dll',dest/'game/wing32.dll')
    (dest/'game/engine.exe').write_bytes(guarded_engine((root/'game/creation.exe').read_bytes()))
    (dest/'game/creation.exe').unlink()
    (dest/'game/cocSc.ODF').rename(dest/'game/enginedata.odf')
    model_folder=dest/'game/models/cocsc'
    for child in model_folder.iterdir():shutil.move(str(child),str(model_folder.parent/child.name))
    model_folder.rmdir()
    for name in ('README.md','LICENSE','THIRD_PARTY_NOTICES.md','original-manifest.json'):
        shutil.copy2(root/name,dest/name)
    shutil.copytree(root/'docs',dest/'docs',dirs_exist_ok=True)
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
    archive=output/'CoC Restored+-Windows.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted(dest.rglob('*')):
            if path.is_file():z.write(path,path.relative_to(output))
    (output/'SHA256SUMS.txt').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
    print(archive)
if __name__=='__main__':main()
