from __future__ import annotations
import argparse, json, shlex
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from .aeon_runtime import AEONRuntime
from .autonomous_world import AutonomousWorld
from .charter import CreatorCharter
from .inbox import Inbox
from .treasury import Treasury

@dataclass
class CreatorCommand:
    text:str; timestamp:str; acknowledged:bool=True

@dataclass
class CommandCenter:
    """Creator console for the bounded autonomous civilization."""
    runtime:AEONRuntime|None=None; inbox:Inbox|None=None; treasury:Treasury|None=None; minimum_balance:float=10_000.0; charter:CreatorCharter=field(default_factory=CreatorCharter); paused:bool=False; shutdown:bool=False; history:list[CreatorCommand]=field(default_factory=list); state_file:str='world_state/creator_commands.jsonl'
    def __post_init__(self):
        if self.runtime is None:self.runtime=AEONRuntime()
        self.world_loop=AutonomousWorld(self.runtime); Path(self.state_file).parent.mkdir(parents=True,exist_ok=True)
    def _record(self,text):
        cmd=CreatorCommand(text,datetime.now(timezone.utc).isoformat()); self.history.append(cmd); self.history=self.history[-200:]
        with open(self.state_file,'a',encoding='utf-8') as f:f.write(json.dumps(cmd.__dict__)+'\n')
    def _summary(self,state):
        life=state.get('life') if isinstance(state.get('life'),dict) else state; internet=state.get('internet') if isinstance(state.get('internet'),dict) else {}; civ=state.get('civilization') if isinstance(state.get('civilization'),dict) else {}; return {'tick':state.get('tick',0),'generation':state.get('generation',0),'beings':state.get('beings',state.get('agents',life.get('beings',0))),'active_budget':civ.get('scheduler',{}).get('active_budget',8),'ideas':state.get('ideas',0),'memories':life.get('memories',0),'relationships':life.get('relationships',0),'reflections':life.get('reflections',0),'artifacts':internet.get('artifacts',state.get('artifacts',0)),'web_events':internet.get('events',state.get('web_events',0)),'organizations':civ.get('organizations',0),'experiments':civ.get('experiments',0),'discoveries':civ.get('metrics',{}).get('discoveries',0),'paused':self.paused,'shutdown':self.shutdown}
    def issue(self,text):
        text=text.strip()
        if not text:return {'ok':False,'error':'empty command'}
        self._record(text); parts=shlex.split(text); cmd=parts[0].lower()
        if cmd in {'status','observe','look'}:return {'ok':True,'status':self._summary(self.world_loop.step() if False else self.runtime.civilization.snapshot()) | {'life':self.runtime.life.snapshot(),'internet':self.runtime.world.snapshot(),'civilization':self.world_loop.platform.snapshot()}}
        if cmd in {'world','observatory'}:return {'ok':True,'observatory':self.world_loop.platform.observatory()}
        if cmd in {'culture','memes'}:return {'ok':True,'culture':self.world_loop.platform.culture}
        if cmd in {'economy','markets'}:return {'ok':True,'economy':{'markets':self.world_loop.platform.markets,'resources':self.world_loop.platform.resources,'jobs':len(self.world_loop.platform.jobs)}}
        if cmd in {'organizations','orgs'}:return {'ok':True,'organizations':self.world_loop.platform.observatory()['organizations']}
        if cmd in {'science','discoveries'}:return {'ok':True,'science':self.world_loop.platform.science[-20:],'discoveries':self.world_loop.platform.metrics['discoveries']}
        if cmd in {'metrics','analytics'}:return {'ok':True,'metrics':self.world_loop.platform.metrics}
        if cmd=='charter':return {'ok':True,'charter':self.charter.prompt(),'fingerprint':self.charter.fingerprint}
        if cmd in {'pause','freeze'}:self.paused=True; return {'ok':True,'message':'Civilization paused.'}
        if cmd in {'resume','continue'}:
            if self.shutdown:return {'ok':False,'error':'world is shut down; start a new runtime to restart'}
            self.paused=False; return {'ok':True,'message':'Civilization resumed.'}
        if cmd in {'shutdown','kill'}:self.shutdown=True; self.paused=True; return {'ok':True,'message':'EMERGENCY SHUTDOWN: autonomous loop frozen.'}
        if cmd=='speak':
            msg=text[len(parts[0]):].strip(); self.runtime.civilization.events.append(f'CREATOR: {msg}'); self.runtime.civilization.events=self.runtime.civilization.events[-100:]; return {'ok':True,'message':'Creator message entered into civilization.','text':msg}
        if cmd=='tell' and len(parts)>=3:
            aid=parts[1]; msg=' '.join(parts[2:]); self.runtime.civilization.events.append(f'CREATOR -> {aid}: {msg}'); self.runtime.civilization.events=self.runtime.civilization.events[-100:]; return {'ok':True,'recipient':aid,'text':msg}
        if cmd=='run':
            if self.paused or self.shutdown:return {'ok':False,'error':'civilization is paused'}
            try:steps=max(1,min(1000,int(parts[1]))) if len(parts)>=2 else 1
            except ValueError:return {'ok':False,'error':'usage: run [1-1000]'}
            state=self.world_loop.run(steps); return {'ok':True,'result':self._summary(state),'internet_learning':state.get('internet_learning'),'recent_decisions':state.get('recent_decisions',[])[-5:]}
        if cmd=='inspect' and len(parts)==2:return {'ok':True,'agent':parts[1],'life':self.runtime.life.inspect(parts[1])}
        if cmd=='browse' and len(parts)==3:
            try:
                result=self.runtime.world.browse(parts[1],parts[2]); result['content']=result['content'][:12000]; return {'ok':True,'observation':result}
            except Exception as exc:return {'ok':False,'error':str(exc)}
        if cmd=='save':self.world_loop.platform.save(); return {'ok':True,'message':'civilization persisted'}
        return {'ok':False,'error':'commands: status | run [n] | inspect <agent> | browse <agent> <https_url> | world | culture | economy | organizations | science | metrics | speak <message> | tell <agent> <message> | charter | pause | resume | save | shutdown | exit'}

def main():
    parser=argparse.ArgumentParser(description='AEON Creator Command Center'); parser.add_argument('--once'); args=parser.parse_args(); center=CommandCenter(); print('AEON COMMAND CENTER ONLINE'); print('Type commands at the CREATOR> prompt. `run` defaults to one life tick.'); print('Try: status | run | inspect A017 | world | culture | economy | science | metrics | shutdown')
    if args.once:print(json.dumps(center.issue(args.once),indent=2,default=str));return
    while not center.shutdown:
        try:line=input('CREATOR> ')
        except (EOFError,KeyboardInterrupt):print('\nCommand center closed.');break
        if line.strip().lower() in {'exit','quit'}:break
        print(json.dumps(center.issue(line),indent=2,default=str))
if __name__=='__main__':main()
