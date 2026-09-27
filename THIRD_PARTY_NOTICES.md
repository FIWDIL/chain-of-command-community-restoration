# Third-party notices

Original Chain of Command / Creation executables and game data remain the property of their respective copyright holders. This notice does not place the original work in the public domain.

Frida 17.18.0 supplies process-local input compatibility. Its Python bindings and core runtime use the wxWindows Library Licence 3.1, based on the GNU Library GPL with an additional binary-distribution exception. Source and build instructions are available from [Frida](https://github.com/frida/frida/tree/17.18.0), [frida-python](https://github.com/frida/frida-python), and [frida-core](https://github.com/frida/frida-core). No Frida binaries are modified. The packaged runtime remains a separately replaceable shared library; source execution using your own compatible Frida build is supported. License texts are included under `third-party-licenses` in the binary release.

The portable launcher bundles CPython 3.12 and Tcl/Tk under their respective upstream licenses. Python's license is included with the release; Tcl/Tk license files remain in the packaged runtime. PyInstaller 6.19.0 packages the application using its GPL bootloader exception; its notices are also included. Other runtime component notices remain with the runtime files. The new WinG compatibility DLL is this project's MIT-licensed implementation; no Microsoft WinG redistributable is required by the release.
