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
    parser.add_argument('--canary',action='store_true',help='Owner-only synthetic API test, no public issues consumed')
    args=parser.parse_args()
    root=Path.cwd(); state_root=Path(args.state_root).resolve()
    if args.mode=='firered' and state_root==root:
        raise ValueError('FireRed requires a separate PRIVATE state repository')
    repo=os.environ['GITHUB_REPOSITORY']
    api=GitHub(repo,os.environ['GH_TOKEN'])
    key=key_from_env()
    path=state_root/'.community'/'session.enc'
    previous=decode(path.read_bytes(),key) if path.exists() else None
    emulator=Emulator(args.core)
    try:
        emulator.loadGame(args.rom)
        session=Session(emulator,previous)
        if args.canary:
            if args.branch=='main':
                raise ValueError('Canary runs must use a development branch')
            queue=[dict(number=900000001,title='[gba] RIGHT 24',user={'login':'integration-test'},created_at='2026-10-11T00:00:00Z'),
                   dict(number=900000002,title='[gba] A 12',user={'login':'integration-test-2'},created_at='2026-10-11T00:01:00Z')]
        else:
            queue=api.queue()
        # Persistent issues are the queue, not workflow pending slots. A batch
        # has at most 50 turns; scheduled sweeps eventually drain a burst.
        pending=[i for i in queue if str(i['number']) not in session.data['ledger']][:50]
        for issue in pending:
            session.process(issue)
        path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix('.tmp')
        temp.write_bytes(encode(session.snapshot(),key)); temp.replace(path)
        render(root,emulator,session,repo,args.branch,args.mode)
        if args.publish:
            if state_root!=root:
                # Save the pending public presentation privately first. If
                # public push fails, next run rebuilds it from committed state.
                commit(state_root,['.community/session.enc'],'Persist community GBA turns',args.state_branch or 'main')
                paths=['README.md','assets/community']
            else:
                paths=['README.md','assets/community','.community/session.enc']
            commit(root,paths,f'Update community GBA screen ({session.data["total"]} turns)',args.branch)
            if not args.canary:
                for issue in queue:
                    if str(issue['number']) in session.data['ledger']:
                        api.close(issue['number'])
        print(f'mGBA verified: {session.data["total"]} accepted turns; {len(pending)} new queue items')
    finally:
        emulator.close()

if __name__=='__main__':
    main()
