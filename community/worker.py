"""Trusted workflow entry point. Untrusted issue text never reaches a shell."""
import argparse
import os
import subprocess
from pathlib import Path
from community.emulator import Emulator
from community.github import GitHub
from community.session import Session,decode,encode,key_from_env
from community.render import render

def git(root,*args):
    return subprocess.run(['git','-C',str(root),*args],check=True,capture_output=True,text=True).stdout.strip()

def commit(root,paths,message,branch):
    git(root,'add','--',*paths)
    if not git(root,'diff','--cached','--name-only'):
        return
    git(root,'-c','user.name=community-gba[bot]','-c','user.email=community-gba@users.noreply.github.com','commit','-m',message)
    # A rejected push fails the transaction. Never force; next run starts from
    # the durable branch head and safely replays uncommitted issue IDs.
    git(root,'push','origin',f'HEAD:refs/heads/{branch}')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--core',required=True)
    parser.add_argument('--rom',required=True)
    parser.add_argument('--state-root',default='.')
    parser.add_argument('--state-branch',default=None)
    parser.add_argument('--branch',required=True)
    parser.add_argument('--mode',choices=['homebrew','firered'],default='homebrew')
    parser.add_argument('--publish',action='store_true')
    parser.add_argument('--operator-plan',help='Private, reviewed maintainer input sequence')
    parser.add_argument('--canary',action='store_true',help='Development [gba-test] Issue queue; isolated branch state')
    args=parser.parse_args()
    root=Path.cwd(); state_root=Path(args.state_root).resolve()
    if args.mode=='firered' and state_root==root:
        raise ValueError('FireRed requires a separate PRIVATE state repository')
    repo=os.environ['GITHUB_REPOSITORY']
    api=GitHub(repo,os.environ['GH_TOKEN'])
    key=key_from_env()
    state_file='.community/canary.enc' if args.canary else '.community/session.enc'
    path=state_root/state_file
    previous=decode(path.read_bytes(),key) if path.exists() else None
    emulator=Emulator(args.core)
    try:
        emulator.loadGame(args.rom)
        session=Session(emulator,previous,
                        boot_frames=3600 if args.mode=='firered' else 120,
                        release_frames=60 if args.mode=='firered' else 2)
        prepared=False
        if args.operator_plan:
            if args.canary or args.mode!='firered' or args.branch!='main' or os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch':
                raise ValueError('Operator preparation requires explicit default-branch manual dispatch')
            from community.operator import apply_plan
            prepared=apply_plan(session,path,args.operator_plan,os.environ['GITHUB_ACTOR'])
        if args.canary:
            if args.branch=='main':
                raise ValueError('Canary runs must use a development branch')
            queue=api.queue('[gba-test]')
            queue=[dict(i,title='[gba]'+i['title'][10:]) for i in queue]
        else:
            queue=api.queue()
        # Persistent issues are the queue, not workflow pending slots. A batch
        # has at most 50 turns; scheduled sweeps eventually drain a burst.
        pending=[i for i in queue if str(i['number']) not in session.data['ledger']][:50]
        for issue in pending:
            session.process(issue)
        if pending or previous is None or prepared:
            path.parent.mkdir(parents=True,exist_ok=True)
            temp=path.with_suffix('.tmp')
            temp.write_bytes(encode(session.snapshot(),key)); temp.replace(path)
        render(root,emulator,session,repo,args.branch,args.mode)
        if args.publish:
            if state_root!=root:
                # Save the pending public presentation privately first. If
                # public push fails, next run rebuilds it from committed state.
                commit(state_root,[state_file],'Persist community GBA turns',args.state_branch or 'main')
                paths=['README.md','assets/community']
            else:
                paths=['README.md','assets/community',state_file]
            commit(root,paths,f'Update community GBA screen ({session.data["total"]} turns)',args.branch)
            for issue in queue:
                if str(issue['number']) in session.data['ledger']:
                    api.close(issue['number'])
        print(f'mGBA verified: {session.data["total"]} accepted turns; {len(pending)} new queue items')
    finally:
        emulator.close()

if __name__=='__main__':
    main()
