"""Windows entry point. The game itself is the preserved 32-bit Creation executable."""
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

ROOT=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent

class Launcher:
    def __init__(self):
        self.root=tk.Tk();self.root.title('Chain of Command - Community Restoration');self.root.geometry('800x595')
        self.root.minsize(720,530);self.client=None;self.server=None
        self.assets=Assets(ROOT/'original')
        box=ttk.Frame(self.root,padding=18);box.pack(fill='both',expand=True)
        ttk.Label(box,text='CHAIN OF COMMAND',font=('Segoe UI',21,'bold')).pack(anchor='w')
        ttk.Label(box,text='Original engine community restoration - experimental',font=('Segoe UI',10)).pack(anchor='w',pady=(0,15))
        self.mode=tk.StringVar(value='offline');self.map=tk.StringVar(value='AbbeyArden');self.host=tk.StringVar(value='127.0.0.1');self.password=tk.StringVar()
        self.support=tk.StringVar(value='MG')
        modes=ttk.Frame(box);modes.pack(anchor='w')
        for label,value in [('Offline vs AI','offline'),('Host direct connection','host'),('Join host','join')]:
            ttk.Radiobutton(modes,text=label,value=value,variable=self.mode).pack(side='left',padx=(0,18))
        form=ttk.Frame(box);form.pack(fill='x',pady=12)
        ttk.Label(form,text='Original map').grid(row=0,column=0,sticky='w',pady=4)
        ttk.Combobox(form,textvariable=self.map,values=sorted(self.assets.map_files),state='readonly',width=30).grid(row=0,column=1,sticky='w',padx=10)
        ttk.Label(form,text='Host IP (joining)').grid(row=1,column=0,sticky='w',pady=4);ttk.Entry(form,textvariable=self.host,width=33).grid(row=1,column=1,sticky='w',padx=10)
        ttk.Label(form,text='Room password').grid(row=2,column=0,sticky='w',pady=4);ttk.Entry(form,textvariable=self.password,show='*',width=33).grid(row=2,column=1,sticky='w',padx=10)
        ttk.Label(form,text='Fourth soldier').grid(row=3,column=0,sticky='w',pady=4)
        ttk.Combobox(form,textvariable=self.support,values=['MG','SMG'],state='readonly',width=30).grid(row=3,column=1,sticky='w',padx=10)
        ttk.Label(box,text='USA vs Germany, four soldiers per player. The host chooses the map.').pack(anchor='w')
        buttons=ttk.Frame(box);buttons.pack(fill='x',pady=12)
        self.start_button=ttk.Button(buttons,text='Start game',command=self.start);self.start_button.pack(side='left')
        ttk.Button(buttons,text='Close match',command=self.close_match).pack(side='left',padx=8)
        self.status=tk.StringVar(value='Select soldiers with 1-4; A selects everyone. Right-click the map to give an order.')
        ttk.Label(box,textvariable=self.status,wraplength=700).pack(anchor='w',pady=(3,8))
        self.command=tk.StringVar(value='Original command bar and keyboard controls are available in the game.')
        ttk.Label(box,textvariable=self.command,wraplength=700).pack(anchor='w')
        cmds=ttk.Frame(box);cmds.pack(fill='x',pady=8)
        commands=[('All','select'),('Walk [W]','walk'),('Run [R]','run'),('Assault [X]','assault'),('Crawl [C]','crawl'),('Stop [H]','stop'),
                  ('Stand [Z]','stand'),('Crouch [V]','crouch'),('Prone [P]','prone'),('Fire at','fire'),('Face [F]','face'),('Center [Space]','center'),
                  ('Frag [G]','grenade'),('Smoke [T]','smoke'),('Hold fire [S]','hold'),('Fire at will [E]','free'),('Carry / put down [B]','carry'),('Objective [O]','objective')]
        for i,(label,action) in enumerate(commands):
            ttk.Button(cmds,text=label,command=lambda a=action:self.order(a)).grid(row=i//6,column=i%6,sticky='ew',padx=2,pady=2)
        for i in range(6):cmds.columnconfigure(i,weight=1)
        ttk.Label(box,text='Escape cancels a targeting order. Arrow keys scroll the original map.\nDirect connect uses TCP 1850 and 1851 on the host.',wraplength=700).pack(anchor='w')
        self.root.protocol('WM_DELETE_WINDOW',self.shutdown);self.root.after(100,self.poll)

    def start(self):
        if self.client:return
        try:
            if self.mode.get()!='join':
                self.server=MatchServer(self.assets,self.map.get(),offline=self.mode.get()=='offline',password=self.password.get());self.server.start()
            host=self.host.get() if self.mode.get()=='join' else '127.0.0.1'
            self.client=Client(ROOT/'original',host,self.password.get(),support=self.support.get());info=self.client.start()
            self.start_button.configure(state='disabled');self.status.set('Opening original client on '+info['map'])
        except Exception as exc:self.close_match();messagebox.showerror('Unable to start',str(exc),parent=self.root)

    def order(self,action):
        if self.client:self.client.send(dict(type='command',action=action,indices=[0,1,2,3]))

    def poll(self):
        if self.client:
            while True:
                try:event=self.client.events.get_nowait()
                except queue.Empty:break
                if event.get('type')=='status':self.status.set(event['text']);self.command.set(event['command']+'  '+event.get('notice',''))
                elif event.get('type')=='error':self.status.set(event['text'])
            if self.client.closed.is_set():self.close_match();self.command.set('Match closed. Choose a mode to play again.')
        self.root.after(100,self.poll)

    def close_match(self):
        if self.client:self.client.close();self.client=None
        if self.server:self.server.close();self.server=None
        self.start_button.configure(state='normal')

    def shutdown(self):self.close_match();self.root.destroy()

def main():
    p=argparse.ArgumentParser();p.add_argument('--smoke-test',type=int,metavar='SECONDS');p.add_argument('--map',default='AbbeyArden');p.add_argument('--join');p.add_argument('--host',action='store_true')
    args=p.parse_args()
    if args.smoke_test:
        assets=Assets(ROOT/'original');server=None;client=None
        try:
            if not args.join:server=MatchServer(assets,args.map,offline=not args.host);server.start()
            client=Client(ROOT/'original',args.join or '127.0.0.1');print(client.start(),flush=True)
            end=time.monotonic()+args.smoke_test
            while time.monotonic()<end and not client.closed.is_set():
                try:print(client.events.get(timeout=.5),flush=True)
                except queue.Empty:pass
            if server:print('SERVER ERRORS',server.errors,flush=True)
        finally:
            if client:client.close()
            if server:server.close()
    else:Launcher().root.mainloop()

if __name__=='__main__':main()
