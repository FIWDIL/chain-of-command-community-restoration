"""Windows launcher for the preserved 32-bit Creation executable."""
import argparse
from pathlib import Path
import queue
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox
from restoration.assets import Assets
from restoration.client import Client
from restoration.server import MatchServer
from restoration.roster import MAX_SLOTS, default_pool

ROOT = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent


class Launcher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Chain of Command - Community Restoration')
        self.root.geometry('860x700'); self.root.minsize(790, 660)
        self.client = None; self.server = None
        self.assets = Assets(ROOT / 'original')
        box = ttk.Frame(self.root, padding=16); box.pack(fill='both', expand=True)
        ttk.Label(box, text='CHAIN OF COMMAND', font=('Segoe UI', 21, 'bold')).pack(anchor='w')
        ttk.Label(box, text='Original engine community restoration - experimental v0.2.0').pack(anchor='w', pady=(0, 12))
        self.tabs = ttk.Notebook(box); self.tabs.pack(fill='both', expand=True)
        setup = ttk.Frame(self.tabs, padding=12); battle = ttk.Frame(self.tabs, padding=12)
        self.tabs.add(setup, text='Match setup'); self.tabs.add(battle, text='Fireteams and orders')
        self.mode = tk.StringVar(value='offline'); self.map = tk.StringVar(value='AbbeyArden')
        self.host = tk.StringVar(value='127.0.0.1'); self.password = tk.StringVar()
        self.team_size = tk.IntVar(value=1); self.mg = tk.IntVar(value=1); self.smg = tk.IntVar(value=0)
        self.side = tk.StringVar(value='Auto'); self.pool_text = tk.StringVar()
        modes = ttk.Frame(setup); modes.pack(anchor='w')
        for label, value in [('Offline vs AI', 'offline'), ('Host direct connection', 'host'), ('Join host', 'join')]:
            ttk.Radiobutton(modes, text=label, value=value, variable=self.mode).pack(side='left', padx=(0, 15))
        form = ttk.Frame(setup); form.pack(fill='x', pady=14)
        rows = [('Original map', ttk.Combobox(form, textvariable=self.map, values=sorted(self.assets.map_files), state='readonly', width=30)),
                ('Fireteams per side (host)', ttk.Combobox(form, textvariable=self.team_size, values=list(range(1, MAX_SLOTS + 1)), state='readonly', width=30)),
                ('Machine guns per side (host)', ttk.Spinbox(form, textvariable=self.mg, from_=0, to=7, width=31)),
                ('SMGs per side (host)', ttk.Spinbox(form, textvariable=self.smg, from_=0, to=14, width=31)),
                ('Host IP (joining)', ttk.Entry(form, textvariable=self.host, width=33)),
                ('Side (joining)', ttk.Combobox(form, textvariable=self.side, values=['Auto', 'USA', 'Germany'], state='readonly', width=30)),
                ('Room password', ttk.Entry(form, textvariable=self.password, show='*', width=33))]
        for i, (label, widget) in enumerate(rows):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky='w', pady=6)
            widget.grid(row=i, column=1, sticky='w', padx=14)
        self.team_size.trace_add('write', self.resize_pool); self.resize_pool()
        ttk.Label(setup, textvariable=self.pool_text, wraplength=750).pack(anchor='w', pady=8)
        ttk.Label(setup, text='Each player commands four soldiers. At 7v7 there are 28 soldiers per side.\nVacant fireteams use AI. The host chooses when a direct-connect battle begins.', wraplength=750).pack(anchor='w', pady=8)
        ttk.Label(setup, text='Weapon pools are reconstructed defaults. Fireteam limits are 1 MG and 2 SMGs. Historical side-pool quantities could not be verified; both sides receive the quantities above.', wraplength=750).pack(anchor='w', pady=8)
        self.command = tk.StringVar(value='The original four-soldier command strip remains available in the game.')
        ttk.Label(battle, textvariable=self.command, wraplength=750).pack(anchor='w', pady=4)
        self.weapons = tk.StringVar()
        ttk.Label(battle, textvariable=self.weapons, wraplength=750).pack(anchor='w', pady=4)
        self.roster = ttk.Treeview(battle, columns=('usa', 'germany'), show='headings', height=7, selectmode='none')
        self.roster.heading('usa', text='USA'); self.roster.heading('germany', text='Germany')
        self.roster.column('usa', width=355); self.roster.column('germany', width=355)
        self.roster.pack(fill='x', pady=8)
        self.begin_button = ttk.Button(battle, text='Begin battle (fill vacant fireteams with AI)', command=lambda: self.order('start'), state='disabled')
        self.begin_button.pack(anchor='w', pady=8)
        cmds = ttk.Frame(battle); cmds.pack(fill='x', pady=8)
        commands = [('All four', 'select'), ('Walk [W]', 'walk'), ('Run [R]', 'run'), ('Assault [X]', 'assault'), ('Crawl [C]', 'crawl'), ('Stop [H]', 'stop'),
                    ('Stand [Z]', 'stand'), ('Crouch [V]', 'crouch'), ('Prone [P]', 'prone'), ('Fire at', 'fire'), ('Face [F]', 'face'), ('Center [Space]', 'center'),
                    ('Frag [G]', 'grenade'), ('Smoke [T]', 'smoke'), ('Hold fire [S]', 'hold'), ('Fire at will [E]', 'free'), ('Carry [B]', 'carry'), ('Objective [O]', 'objective')]
        for i, (label, action) in enumerate(commands):
            ttk.Button(cmds, text=label, command=lambda a=action: self.order(a)).grid(row=i//6, column=i%6, sticky='ew', padx=2, pady=2)
        for i in range(6): cmds.columnconfigure(i, weight=1)
        ttk.Label(battle, text='1-4 select your soldiers; A selects your fireteam. Right-click gives an order.\nEscape cancels targeting. Allies marked F2, F3, etc. belong to other fireteams.', wraplength=750).pack(anchor='w', pady=8)
        buttons = ttk.Frame(box); buttons.pack(fill='x', pady=10)
        self.start_button = ttk.Button(buttons, text='Open match', command=self.start); self.start_button.pack(side='left')
        ttk.Button(buttons, text='Close match', command=self.close_match).pack(side='left', padx=8)
        self.status = tk.StringVar(value='Direct connect uses TCP 1850 and 1851 on the host.')
        ttk.Label(box, textvariable=self.status, wraplength=800).pack(anchor='w')
        self.root.protocol('WM_DELETE_WINDOW', self.shutdown); self.root.after(100, self.poll)

    def resize_pool(self, *_):
        size = self.team_size.get(); pool = default_pool(size)
        self.mg.set(pool['MG']); self.smg.set(pool['SMG'])
        self.pool_text.set(f'{size}v{size}: {size*4} soldiers per side. Special weapons replace rifles and are spread automatically across fireteams.')

    def start(self):
        if self.client: return
        try:
            if self.mode.get() != 'join':
                self.server = MatchServer(self.assets, self.map.get(), offline=self.mode.get() == 'offline', password=self.password.get(),
                                          team_size=self.team_size.get(), pool={'MG': self.mg.get(), 'SMG': self.smg.get()})
                self.server.start()
            host = self.host.get() if self.mode.get() == 'join' else '127.0.0.1'
            side = {'Auto': 'auto', 'USA': 0, 'Germany': 1}[self.side.get()]
            self.client = Client(ROOT/'original', host, self.password.get(), side=side, owner_token=self.server.owner_token if self.server else '')
            info = self.client.start()
            self.start_button.configure(state='disabled'); self.tabs.select(1)
            self.status.set(f"Opening {info['map']} | {info['team_size']}v{info['team_size']} | {'USA' if info['side']==0 else 'Germany'} fireteam {info['slot']+1}")
        except Exception as exc:
            self.close_match(); messagebox.showerror('Unable to start', str(exc), parent=self.root)

    def order(self, action):
        if self.client: self.client.send(dict(type='command', action=action, indices=[0, 1, 2, 3]))

    def poll(self):
        if self.client:
            while True:
                try: event = self.client.events.get_nowait()
                except queue.Empty: break
                if event.get('type') == 'status':
                    self.status.set(event['text']); self.command.set(event['command']+'  '+event.get('notice', ''))
                    self.weapons.set(' | '.join(f"{u['index']+1}: {u['weapon']} ({u['ammo']}/{u['reserve']})" for u in event['units']))
                    info = self.client.info
                    self.begin_button.configure(state='normal' if info.get('owner') and not event['started'] else 'disabled')
                    entries = {(s['side'], s['slot']): s for s in event['roster']}
                    for slot in range(info['team_size']):
                        values = []
                        for side in (0, 1):
                            entry = entries[side, slot]; who = 'You' if (side, slot)==(info['side'], info['slot']) else entry['control']
                            values.append(f"Fireteam {slot+1}: {who} | {entry['active']}/4 active")
                        if self.roster.exists(str(slot)): self.roster.item(str(slot), values=values)
                        else: self.roster.insert('', 'end', iid=str(slot), values=values)
                elif event.get('type') == 'error': self.status.set(event['text'])
            if self.client.closed.is_set():
                self.close_match(); self.command.set('Match closed. Choose a mode to play again.')
        self.root.after(100, self.poll)

    def close_match(self):
        if self.client: self.client.close(); self.client = None
        if self.server: self.server.close(); self.server = None
        self.start_button.configure(state='normal'); self.begin_button.configure(state='disabled')
        for item in self.roster.get_children(): self.roster.delete(item)

    def shutdown(self):
        self.close_match(); self.root.destroy()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--smoke-test', type=int, metavar='SECONDS'); p.add_argument('--map', default='AbbeyArden')
    p.add_argument('--join'); p.add_argument('--host', action='store_true')
    p.add_argument('--team-size', type=int, choices=range(1, 8), default=1)
    p.add_argument('--side', choices=('auto', 'usa', 'germany'), default='auto')
    args = p.parse_args()
    if args.smoke_test:
        assets = Assets(ROOT/'original'); server = None; client = None
        try:
            if not args.join:
                server = MatchServer(assets, args.map, offline=not args.host, team_size=args.team_size); server.start()
            client = Client(ROOT/'original', args.join or '127.0.0.1', side={'auto': 'auto', 'usa': 0, 'germany': 1}[args.side], owner_token=server.owner_token if server else '')
            print(client.start(), flush=True)
            end = time.monotonic()+args.smoke_test
            while time.monotonic()<end and not client.closed.is_set():
                try: print(client.events.get(timeout=.5), flush=True)
                except queue.Empty: pass
            if server: print('SERVER ERRORS', server.errors, flush=True)
        finally:
            if client: client.close()
            if server: server.close()
    else: Launcher().root.mainloop()


if __name__ == '__main__': main()
