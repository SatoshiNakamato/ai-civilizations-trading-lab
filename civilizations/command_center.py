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
    text: str
    timestamp: str
    acknowledged: bool = True

@dataclass
class CommandCenter:
    """Interactive Creator console. Run `python -m civilizations.command_center`."""
    runtime: AEONRuntime | None = None
    inbox: Inbox | None = None
    treasury: Treasury | None = None
    minimum_balance: float = 10_000.0
    charter: CreatorCharter = field(default_factory=CreatorCharter)
    paused: bool = False
    shutdown: bool = False
    history: list[CreatorCommand] = field(default_factory=list)
    state_file: str = 'world_state/creator_commands.jsonl'

    def __post_init__(self):
        if self.runtime is None:
            self.runtime = AEONRuntime()
        self.world_loop = AutonomousWorld(self.runtime)
        Path(self.state_file).parent.mkdir(parents=True, exist_ok=True)

    def _record(self, text):
        cmd=CreatorCommand(text, datetime.now(timezone.utc).isoformat())
        self.history.append(cmd)
        with open(self.state_file,'a',encoding='utf-8') as f:
            f.write(json.dumps(cmd.__dict__)+'\n')

    def issue(self, text):
        text=text.strip()
        if not text: return {'ok':False,'error':'empty command'}
        self._record(text)
        parts=shlex.split(text); cmd=parts[0].lower() if parts else ''
        if cmd in {'status','observe','look'}: return {'ok':True,'status':self.status()}
        if cmd=='charter': return {'ok':True,'charter':self.charter.prompt(),'fingerprint':self.charter.fingerprint}
        if cmd in {'pause','freeze'}: self.paused=True; return {'ok':True,'message':'Civilization paused.'}
        if cmd in {'resume','continue'}:
            if self.shutdown: return {'ok':False,'error':'world is shut down; start a new runtime to restart'}
            self.paused=False; return {'ok':True,'message':'Civilization resumed.'}
        if cmd in {'shutdown','kill'}:
            self.shutdown=True; self.paused=True; return {'ok':True,'message':'EMERGENCY SHUTDOWN: autonomous loop frozen.'}
        if cmd=='speak':
            msg=text[len(parts[0]):].strip(); self.runtime.civilization.events.append(f'CREATOR: {msg}')
            return {'ok':True,'message':'Creator message entered into civilization.','text':msg}
        if cmd=='tell' and len(parts)>=3:
            aid=parts[1]; msg=' '.join(parts[2:]); self.runtime.civilization.events.append(f'CREATOR -> {aid}: {msg}')
            return {'ok':True,'recipient':aid,'text':msg}
        if cmd=='run' and len(parts)>=2:
            if self.paused or self.shutdown: return {'ok':False,'error':'civilization is paused'}
            try: steps=max(1,min(1000,int(parts[1])))
            except ValueError: return {'ok':False,'error':'usage: run <1-1000>'}
            return {'ok':True,'state':self.world_loop.run(steps)}
        if cmd=='inspect' and len(parts)==2:
            return {'ok':True,'agent':parts[1],'life':self.runtime.life.inspect(parts[1])}
        if cmd=='browse' and len(parts)==3:
            try:
                result=self.runtime.world.browse(parts[1],parts[2]); result['content']=result['content'][:12000]
                return {'ok':True,'observation':result}
            except Exception as exc: return {'ok':False,'error':str(exc)}
        return {'ok':False,'error':'commands: status | charter | speak <message> | tell <agent> <message> | run <n> | inspect <agent> | browse <agent> <https_url> | pause | resume | shutdown | exit'}

    def status(self):
        state=self.runtime.civilization.snapshot()
        state.update({'paused':self.paused,'shutdown':self.shutdown,'creator':self.charter.creator_name,'charter_fingerprint':self.charter.fingerprint,'commands':len(self.history),'life':self.runtime.life.snapshot(),'internet':self.runtime.world.snapshot()})
        if self.treasury is not None: state['treasury']=round(self.treasury.balance,2)
        return state

def main():
    parser=argparse.ArgumentParser(description='AEON Creator Command Center')
    parser.add_argument('--once',help='execute one command and exit')
    args=parser.parse_args(); center=CommandCenter()
    print('AEON COMMAND CENTER ONLINE')
    print('IMPORTANT: type commands at the CREATOR> prompt, not at the Termux $ prompt.')
    print('Try: status  |  run 1  |  inspect A017  |  speak hello  |  shutdown')
    if args.once:
        print(json.dumps(center.issue(args.once),indent=2,default=str)); return
    while not center.shutdown:
        try: line=input('CREATOR> ')
        except (EOFError,KeyboardInterrupt): print('\nCommand center closed.'); break
        if line.strip().lower() in {'exit','quit'}: break
        print(json.dumps(center.issue(line),indent=2,default=str))

if __name__=='__main__': main()
