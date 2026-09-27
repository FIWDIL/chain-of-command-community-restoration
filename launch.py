"""Windows launcher for the preserved 32-bit Creation executable."""
import argparse
import json
from pathlib import Path
import queue
import sys
import time
import threading
import socket
import tkinter as tk
from tkinter import ttk, messagebox
from restoration.assets import Assets
from restoration.client import Client
from restoration.server import MatchServer
from restoration.roster import MAX_SLOTS, default_pool
from restoration.simulation import WEAPONS

ROOT = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent


class Launcher:
    def __init__(self):
        self.root=tk.Tk();self.root.title('CoC Restored+')
        self.root.iconbitmap(str(Path(__file__).parent/'restoration/community.ico'))
        self.root.resizable(False,False)
        self.client=None;self.server=None;self.busy=False;self.shutting_down=False
        self.jobs=queue.Queue();self.last_lobby=None;self.started=False;self.launching=False;self.ready=False;self.finished=False;self.room_state={};self.draft=None
        self.assets=Assets(ROOT/'game')
        self.mode=tk.StringVar(value='offline');self.map=tk.StringVar(value='AbbeyArden')
        self.host=tk.StringVar(value='127.0.0.1');self.password=tk.StringVar();self.name=tk.StringVar(value='Player')
        self.side=tk.StringVar(value='USA');self.team_size=tk.IntVar(value=1);self.mg=tk.IntVar(value=1);self.smg=tk.IntVar(value=0)
        self.box=ttk.Frame(self.root,padding=16);self.box.pack(fill='both',expand=True)
        ttk.Label(self.box,text='CoC Restored+',font=('Segoe UI',18,'bold')).pack(pady=(0,12))
        modes=ttk.Frame(self.box);modes.pack()
        self.radios=[]
        for text,value in [('Offline vs CPU','offline'),('Host','host'),('Join','join')]:
            button=ttk.Radiobutton(modes,text=text,value=value,variable=self.mode,command=self.render_mode)
            button.pack(side='left',padx=10);self.radios.append(button)
        self.form=ttk.Frame(self.box);self.form.pack(pady=12,fill='x')
        self.form.columnconfigure(1,weight=1);self.fields={}
        rows=[('map','Map',ttk.Combobox(self.form,textvariable=self.map,values=sorted(self.assets.missions),state='readonly')),
              ('name','Player name',ttk.Entry(self.form,textvariable=self.name)),
              ('side','Side',ttk.Combobox(self.form,textvariable=self.side,values=['USA','Germany'],state='readonly')),
              ('team_size','Fireteams per side',ttk.Combobox(self.form,textvariable=self.team_size,values=list(range(1,MAX_SLOTS+1)),state='readonly')),
              ('mg','Machine guns per side',ttk.Spinbox(self.form,textvariable=self.mg,from_=0,to=7)),
              ('smg','SMGs per side',ttk.Spinbox(self.form,textvariable=self.smg,from_=0,to=14)),
              ('host','Host IP',ttk.Entry(self.form,textvariable=self.host)),
              ('password','Room password',ttk.Entry(self.form,textvariable=self.password,show='*'))]
        for index,(key,label,widget) in enumerate(rows):
            text=ttk.Label(self.form,text=label);self.fields[key]=(text,widget,index)
        self.fields['map'][1].bind('<<ComboboxSelected>>',self.change_map)
        self.fields['side'][1].bind('<<ComboboxSelected>>',self.change_side)
        self.fields['team_size'][1].bind('<<ComboboxSelected>>',self.resize_pool)
        self.connection_info=tk.StringVar()
        self.address_label=ttk.Label(self.box,textvariable=self.connection_info,justify='left',wraplength=520)
        self.lobby=ttk.Frame(self.box)
        self.roster=ttk.Treeview(self.lobby,show='tree',height=7,selectmode='browse')
        scroll=ttk.Scrollbar(self.lobby,orient='vertical',command=self.roster.yview)
        self.roster.configure(yscrollcommand=scroll.set)
        self.roster.grid(row=0,column=0,sticky='nsew');scroll.grid(row=0,column=1,sticky='ns')
        self.lobby.columnconfigure(0,weight=1)
        chatbox=ttk.LabelFrame(self.lobby,text='Messages',padding=6);chatbox.grid(row=1,column=0,columnspan=2,sticky='ew',pady=(8,0))
        self.messages=tk.Text(chatbox,height=5,width=55,wrap='word',state='disabled',font=('Segoe UI',9))
        self.messages.grid(row=0,column=0,columnspan=2,sticky='ew');chatbox.columnconfigure(0,weight=1)
        self.message=tk.StringVar();entry=ttk.Entry(chatbox,textvariable=self.message)
        entry.grid(row=1,column=0,sticky='ew',pady=(6,0));entry.bind('<Return>',lambda _:self.send_chat())
        ttk.Button(chatbox,text='Send',command=self.send_chat).grid(row=1,column=1,padx=(6,0),pady=(6,0))
        self.recipient=tk.StringVar(value='Everyone');self.chat_targets={}
        self.recipient_box=ttk.Combobox(chatbox,textvariable=self.recipient,values=['Everyone','My team'],state='readonly')
        self.recipient_box.grid(row=2,column=0,sticky='ew',pady=(6,0))
        ttk.Button(chatbox,text='Ignore / unignore',command=self.ignore_player).grid(row=2,column=1,padx=(6,0),pady=(6,0))
        self.tools=ttk.Frame(self.box);self.tools.pack(pady=(0,6))
        ttk.Button(self.tools,text='Equipment',command=self.equipment_dialog).pack(side='left',padx=3)
        ttk.Button(self.tools,text='Commanders',command=self.commander_dialog).pack(side='left',padx=3)
        ttk.Button(self.tools,text='Match history',command=self.history_dialog).pack(side='left',padx=3)
        self.return_button=ttk.Button(self.tools,text='Return to lobby',command=lambda:self.client.send({'type':'command','action':'lobby'}) if self.client else None)
        self.buttons=ttk.Frame(self.box);self.buttons.pack(pady=(6,0))
        self.open_button=ttk.Button(self.buttons,command=self.open_lobby)
        self.leave_button=ttk.Button(self.buttons,command=self.close_match)
        self.start_button=ttk.Button(self.buttons,text='Start match',command=self.start_match)
        self.render_mode()
        self.root.protocol('WM_DELETE_WINDOW',self.shutdown);self.root.after(100,self.poll)

    def render_mode(self):
        mode=self.mode.get();connected=self.client is not None
        layout=(mode,connected,self.busy,self.started,self.launching,self.ready,self.finished)
        if layout==getattr(self,'last_layout',None):return
        self.last_layout=layout
        visible={'map','team_size','mg','smg'} if mode=='offline' else ({'map','name','side','team_size','mg','smg','password'} if mode=='host' else {'name','side','host','password'})
        if connected:visible={'map','side'} if mode in ('host','offline') else {'side'}
        self.address_label.pack_forget()
        if mode=='host':
            try:addresses=sorted({item[4][0] for item in socket.getaddrinfo(socket.gethostname(),None,socket.AF_INET) if not item[4][0].startswith('127.')})
            except OSError:addresses=[]
            ip=', '.join(addresses) or '127.0.0.1 (this computer only)'
            lobby_port=self.server.control_port if self.server else 1851
            game_port=self.server.game_port if self.server else 1850
            self.connection_info.set(f'Host IP: {ip}\nLobby port: {lobby_port}    Game port: {game_port} (TCP)')
            self.address_label.pack(before=self.buttons,fill='x',pady=(0,8))
        row=0
        for key,(label,widget,_) in self.fields.items():
            label.grid_remove();widget.grid_remove()
            if key in visible:
                label.grid(row=row,column=0,sticky='w',padx=(0,16),pady=4)
                widget.grid(row=row,column=1,sticky='ew',pady=4);row+=1
                enabled=not self.busy and (not connected or (key in ('side','map') and not self.started and not self.launching))
                widget.configure(state=('readonly' if isinstance(widget,ttk.Combobox) else 'normal') if enabled else 'disabled')
        for radio in self.radios:radio.configure(state='disabled' if connected or self.busy else 'normal')
        for button in (self.open_button,self.leave_button,self.start_button):button.pack_forget()
        if mode!='offline':
            self.open_button.configure(text='Open lobby' if mode=='host' else 'Join lobby',state='disabled' if connected or self.busy else 'normal')
            self.leave_button.configure(text='Close lobby' if mode=='host' else 'Leave lobby',state='normal' if connected and not self.busy else 'disabled')
            self.open_button.pack(side='left',padx=4);self.leave_button.pack(side='left',padx=4)
        can_start=not self.busy and ((mode=='offline' and not connected) or (connected and not self.started and not self.launching and (mode in ('host','offline') or not self.ready)))
        self.start_button.configure(state='normal' if can_start else 'disabled');self.start_button.pack(side='left',padx=4)
        if connected:self.lobby.pack(fill='x',before=self.buttons,pady=(0,8))
        else:self.lobby.pack_forget()
        self.return_button.pack_forget()
        if connected and self.started and self.client.info.get('owner'):self.return_button.pack(side='left',padx=3)
        self.root.update_idletasks()
        self.root.geometry(f"560x{self.box.winfo_reqheight()}")

    def resize_pool(self,*_):
        pool=default_pool(self.team_size.get());self.mg.set(pool['MG']);self.smg.set(pool['SMG'])

    def change_side(self,*_):
        if self.client:self.client.send({'type':'side','side':0 if self.side.get()=='USA' else 1})

    def open_lobby(self):self.connect(False)

    def connect(self,offline):
        if self.client or self.busy:return
        try:
            config=dict(mode=self.mode.get(),map=self.map.get(),name=self.name.get(),host=self.host.get(),password=self.password.get(),
                        side=0 if self.side.get()=='USA' else 1,size=self.team_size.get(),
                        pool={'MG':self.mg.get(),'SMG':self.smg.get()})
        except (ValueError,tk.TclError):messagebox.showerror('Invalid options','Enter whole numbers for the weapon pools.',parent=self.root);return
        self.busy=True;self.render_mode()
        def work():
            server=None;client=None
            try:
                if config['mode']!='join':
                    server=MatchServer(self.assets,config['map'],offline=offline,password=config['password'],team_size=config['size'],pool=config['pool'],state_dir=ROOT/'saves')
                    if self.draft and self.draft.game.team_size==config['size'] and self.draft.game.pool==config['pool']:
                        server.commanders=dict(self.draft.commanders)
                        for unit,source in zip(server.game.units,self.draft.game.units):
                            unit.weapon=source.weapon;unit.ammo=WEAPONS[unit.weapon]['magazine'];unit.reserve=WEAPONS[unit.weapon]['reserve']
                    server.start()
                client=Client(ROOT/'game',config['host'] if config['mode']=='join' else '127.0.0.1',config['password'],
                              side=config['side'],owner_token=server.owner_token if server else '',name=config['name'],lobby=not offline)
                client.start()
                if self.shutting_down:
                    client.close()
                    if server:server.close()
                else:self.jobs.put(('connected',client,server))
            except Exception as exc:
                if client:client.close()
                if server:server.close()
                self.jobs.put(('error',str(exc),None))
        threading.Thread(target=work,daemon=True).start()

    def start_match(self):
        if self.mode.get()=='offline' and not self.client:self.connect(True)
        elif self.client:self.client.send({'type':'command','action':'start'})

    def send_chat(self):
        text=self.message.get().strip()
        if self.client and text:
            choice=self.recipient.get();channel='team' if choice=='My team' else 'whisper' if choice in self.chat_targets else 'room'
            self.client.send({'type':'chat','text':text[:240],'channel':channel,'recipient':self.chat_targets.get(choice,'')});self.message.set('')

    def show_chat(self):
        self.messages.configure(state='normal');self.messages.delete('1.0','end')
        for event in self.client.chat_history:self.messages.insert('end',f"{event['sender']}{' ['+event['channel']+']' if event.get('channel') else ''}: {event['text']}\n")
        self.messages.configure(state='disabled');self.messages.see('end')

    def poll(self):
        while not self.jobs.empty():
            kind,value,server=self.jobs.get()
            self.busy=False
            if kind=='connected':self.client=value;self.server=server
            elif kind=='error':messagebox.showerror('Unable to connect',value,parent=self.root)
            elif kind=='opened':pass
            self.render_mode()
        if self.client:
            while self.client:
                try:event=self.client.events.get_nowait()
                except queue.Empty:break
                kind=event.get('type')
                if kind=='lobby':
                    self.room_state=event;self.finished=event.get('finished',False)
                    self.map.set(event['map'])
                    self.chat_targets={'Private: '+g['name']:g['player'] for t in event['teams'] for g in t['fireteams'] if g['player'] and g['player']!=self.client.info['username']}
                    self.recipient_box.configure(values=['Everyone','My team']+list(self.chat_targets))
                    if self.recipient.get() not in ['Everyone','My team']+list(self.chat_targets):self.recipient.set('Everyone')
                    self.started=event['started'];self.launching=event['launching'];self.ready=event['ready']
                    self.side.set('USA' if event['side']==0 else 'Germany')
                    if event['teams']!=self.last_lobby:
                        self.last_lobby=event['teams']
                        self.roster.delete(*self.roster.get_children())
                        for team in event['teams']:
                            parent=self.roster.insert('', 'end',text=team['name'],open=True)
                            def add_group(group,under):
                                fireteam=self.roster.insert(under,'end',iid=f"group-{team['side']}-{group['slot']}",text=f"Fireteam {group['slot']+1}"+(' - mission commander' if group.get('commander') is None else ''),open=True)
                                text=group['name']+(' (host)' if group['host'] else '')+(' - ready' if group['ready'] else '')
                                if group['player']==self.client.info['username']:text+=' (you)'
                                self.roster.insert(fireteam,'end',text=text)
                                for child in team['fireteams']:
                                    if child.get('commander')==group['slot']:add_group(child,fireteam)
                            for group in team['fireteams']:
                                if group.get('commander') is None:add_group(group,parent)
                    self.render_mode()
                elif kind=='return_lobby':
                    self.started=False;self.launching=False;self.finished=False;self.ready=False;self.busy=False;self.last_lobby=None;self.map.set(event['map']);self.render_mode();self.show_room()
                elif kind=='ui' and event.get('action')=='room':self.show_room()
                elif kind=='ui' and event.get('action')=='equipment':self.show_room();self.equipment_dialog()
                elif kind=='ui' and event.get('action')=='commanders':self.show_room();self.commander_dialog()
                elif kind=='assignment':self.side.set('USA' if event['side']==0 else 'Germany')
                elif kind in ('chat','chat_history'):self.show_chat()
                elif kind=='launch' and not self.client.game_open and not self.busy:
                    self.busy=True;self.render_mode();client=self.client
                    def open_game():
                        try:client.open_game();self.jobs.put(('opened',None,None))
                        except Exception as exc:self.jobs.put(('error',str(exc),None));client.close()
                    threading.Thread(target=open_game,daemon=True).start()
                elif kind=='game_closed':
                    self.show_room();self.render_mode()
                elif kind=='notice':messagebox.showinfo('Lobby',event['text'],parent=self.root)
                elif kind=='error':messagebox.showerror('Connection',event['text'],parent=self.root)
            if self.client and self.client.closed.is_set():self.close_match()
        if not self.shutting_down:self.root.after(100,self.poll)

    def show_room(self):
        self.root.deiconify();self.root.lift();self.root.focus_force()

    def change_map(self,*_):
        if self.client:self.client.send({'type':'map','map':self.map.get()})

    def ignore_player(self):
        target=self.chat_targets.get(self.recipient.get())
        if not self.client or not target:
            messagebox.showinfo('Messages','Choose a private-message recipient first.',parent=self.root);return
        self.client.send({'type':'ignore','player':target,'ignored':target not in self.room_state.get('ignored',[])})
        messagebox.showinfo('Messages','Ignore setting changed for this player.',parent=self.root)

    def preparation(self):
        if self.busy or self.launching:
            messagebox.showinfo('Match setup','Return to the lobby after the match to change assignments.',parent=self.root);return None
        if self.client:return self.room_state
        if self.mode.get()=='join':
            messagebox.showinfo('Match setup','Join a lobby before changing assignments.',parent=self.root);return None
        try:
            size=self.team_size.get();pool={'MG':self.mg.get(),'SMG':self.smg.get()}
            if not self.draft or self.draft.game.team_size!=size or self.draft.game.pool!=pool:
                self.draft=MatchServer(self.assets,self.map.get(),offline=False,team_size=size,pool=pool)
            session=dict(side=0,slot=0,owner=True,username='Setup',ready=False,ignored=set())
            return self.draft.lobby_snapshot(session)
        except (ValueError,tk.TclError) as exc:
            messagebox.showerror('Match setup',str(exc),parent=self.root);return None

    def assignment_window(self,title,state):
        window=tk.Toplevel(self.root);window.title(title);window.transient(self.root);window.resizable(False,False)
        window.iconbitmap(str(Path(__file__).parent/'restoration/community.ico'))
        # Let the native button's mouse release finish before raising its viewer.
        def raise_viewer():
            if window.winfo_exists():window.lift();window.focus_force()
        window.after(150,raise_viewer)
        body=ttk.Frame(window,padding=14);body.pack(fill='both',expand=True)
        side=tk.StringVar(value='USA' if state['side']==0 else 'Germany')
        slot=tk.IntVar(value=state['slot']+1)
        ttk.Label(body,text='Side').grid(row=0,column=0,sticky='w',pady=4)
        sides=ttk.Combobox(body,textvariable=side,values=['USA','Germany'],state='readonly',width=25);sides.grid(row=0,column=1,pady=4)
        ttk.Label(body,text='Fireteam').grid(row=1,column=0,sticky='w',pady=4)
        slots=ttk.Combobox(body,textvariable=slot,values=list(range(1,len(state['teams'][0]['fireteams'])+1)),state='readonly',width=25);slots.grid(row=1,column=1,pady=4)
        if self.started:
            ttk.Label(window,text='View only during a match. Change assignments in the lobby.',padding=8).pack()
        return window,body,side,slot,sides,slots

    def equipment_dialog(self):
        state=self.preparation()
        if not state:return
        window,body,side,slot,sides,slots=self.assignment_window('Assign weapons',state)
        choices=[]
        for number in range(4):
            ttk.Label(body,text=f'Soldier {number+1}').grid(row=number+2,column=0,sticky='w',padx=(0,15),pady=4)
            value=tk.StringVar();choices.append(value)
            ttk.Combobox(body,textvariable=value,values=['Rifle','MG','SMG'],state='readonly',width=25).grid(row=number+2,column=1,pady=4)
        def refresh(*_):
            current=self.room_state if self.client else self.draft.lobby_snapshot(dict(side=0,slot=0,owner=True,username='Setup',ready=False))
            team=current['teams'][0 if side.get()=='USA' else 1]
            for value,weapon in zip(choices,team['fireteams'][slot.get()-1]['weapons']):value.set('MG' if weapon in ('BAR','MG42') else 'SMG' if weapon in ('Thompson','MP40') else 'Rifle')
        def apply():
            event=dict(type='equipment',side=0 if side.get()=='USA' else 1,slot=slot.get()-1,weapons=[v.get() for v in choices])
            if self.client:self.client.send(event)
            else:
                session=dict(owner=True,side=0,slot=0,outgoing=queue.Queue())
                self.draft.assign_weapons(session,event)
                if not session['outgoing'].empty():messagebox.showinfo('Equipment',session['outgoing'].get()['text'],parent=window)
        sides.bind('<<ComboboxSelected>>',refresh);slots.bind('<<ComboboxSelected>>',refresh);refresh()
        ttk.Label(body,text='Weapons come from the side stockpile. Return weapons to rifles before moving them to another fireteam.',wraplength=350).grid(row=6,column=0,columnspan=2,pady=10)
        ttk.Button(body,text='Apply',command=apply,state='disabled' if self.started or self.launching else 'normal').grid(row=7,column=0,columnspan=2)

    def commander_dialog(self):
        state=self.preparation()
        if not state:return
        if self.client and not self.client.info['owner']:
            messagebox.showinfo('Commanders','The host assigns the command hierarchy.',parent=self.root);return
        window,body,side,slot,sides,slots=self.assignment_window('Assign commanders',state)
        commander=tk.StringVar();options=['Mission commander']+[f'Fireteam {i+1}' for i in range(len(state['teams'][0]['fireteams']))]
        ttk.Label(body,text='Reports to').grid(row=2,column=0,sticky='w',padx=(0,15),pady=4)
        ttk.Combobox(body,textvariable=commander,values=options,state='readonly',width=25).grid(row=2,column=1,pady=4)
        def refresh(*_):
            current=self.room_state if self.client else self.draft.lobby_snapshot(dict(side=0,slot=0,owner=True,username='Setup',ready=False))
            leader=current['teams'][0 if side.get()=='USA' else 1]['fireteams'][slot.get()-1]['commander']
            commander.set('Mission commander' if leader is None else f'Fireteam {leader+1}')
        def apply():
            event=dict(type='commander',side=0 if side.get()=='USA' else 1,slot=slot.get()-1,commander=None if commander.get()=='Mission commander' else int(commander.get().split()[-1])-1)
            if self.client:self.client.send(event)
            else:
                session=dict(owner=True,outgoing=queue.Queue());self.draft.set_commander(session,event)
                messagebox.showinfo('Commanders',session['outgoing'].get()['text'] if not session['outgoing'].empty() else 'Commander assigned.',parent=window)
        sides.bind('<<ComboboxSelected>>',refresh);slots.bind('<<ComboboxSelected>>',refresh);refresh()
        ttk.Button(body,text='Apply',command=apply,state='disabled' if self.started or self.launching else 'normal').grid(row=3,column=0,columnspan=2,pady=10)

    def history_dialog(self):
        window=tk.Toplevel(self.root);window.title('Match history');window.transient(self.root)
        view=ttk.Treeview(window,columns=('map','result','duration'),show='headings',height=12)
        for name,title in [('map','Map'),('result','Result'),('duration','Seconds')]:view.heading(name,text=title);view.column(name,width=150)
        view.pack(fill='both',expand=True,padx=12,pady=12)
        try:records=json.loads((ROOT/'saves/match-history.json').read_text(encoding='utf-8'))
        except (OSError,ValueError):records=[]
        for record in reversed(records if isinstance(records,list) else []):
            view.insert('','end',values=(record.get('map',''),{-1:'Draw',0:'USA won',1:'Germany won'}.get(record.get('winner'),''),record.get('duration','')))
        ttk.Label(window,text='Records saved on this host computer. Original ranks and promotion points are not inferred.').pack(padx=12,pady=(0,12))

    def close_match(self):
        if self.client:self.client.close();self.client=None
        if self.server:self.server.close();self.server=None
        self.last_lobby=None;self.started=False;self.launching=False;self.ready=False;self.finished=False;self.room_state={}
        self.roster.delete(*self.roster.get_children());self.message.set('')
        self.messages.configure(state='normal');self.messages.delete('1.0','end');self.messages.configure(state='disabled')
        self.render_mode()

    def shutdown(self):
        self.shutting_down=True;self.close_match();self.root.destroy()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--smoke-test', type=int, metavar='SECONDS'); p.add_argument('--map', default='AbbeyArden')
    p.add_argument('--join'); p.add_argument('--host', action='store_true')
    p.add_argument('--team-size', type=int, choices=range(1, 8), default=1)
    p.add_argument('--side', choices=('auto', 'usa', 'germany'), default='auto')
    args = p.parse_args()
    if args.smoke_test:
        assets = Assets(ROOT/'game'); server = None; client = None
        try:
            if not args.join:
                server = MatchServer(assets, args.map, offline=not args.host, team_size=args.team_size); server.start()
            client = Client(ROOT/'game', args.join or '127.0.0.1', side={'auto': 'auto', 'usa': 0, 'germany': 1}[args.side], owner_token=server.owner_token if server else '')
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
