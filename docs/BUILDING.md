# Running and building the source

Players should use **CoC Restored+.exe** from the portable package. These instructions are for developers.

Put the recovered game files in `game` at the repository root. This folder is ignored by Git. Their hashes are recorded in `original-manifest.json`; do not edit the recovered files.

Create a Python environment and install the requirements:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python launch.py
```

Run the tests:

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
```

Install PyInstaller in the same environment, then build:

```powershell
python tools/build_release.py --output dist/restored --work build/package
```

The output contains **CoC Restored+.exe**, game data and its bundled runtime. Players do not need `launch.py` or Python. The package has no release number in its name.

The build creates a guarded `game/engine.exe`, renames the game definitions to `game/enginedata.odf`, and places graphics, `oin` and `sound` directly under `game/models`. The native bridge redirects the original embedded paths. The original files in the source tree remain unchanged.

`tools/runtime-exclusions.json` records the 268 audited files omitted from the player runtime, including duplicate maps, compressed sound copies, retired GameClub assets and development metadata. The build retains release documentation and license notices. It removes empty directories after applying exclusions. This replaces the earlier manual runtime cleanup with a repeatable build step.

`compat/wing32.dll` is the local graphics compatibility library. Rebuild it with `tools/build_wing.py --llvm <LLVM-bin-directory>` when needed.

The network compatibility identifier and recovered executable hash are internal checks. They are retained to prevent incompatible clients from connecting.
