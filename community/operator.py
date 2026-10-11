"""Explicit maintainer preparation, replayed once from an exact private snapshot."""
import hashlib
import json
from pathlib import Path
from community.emulator import BUTTONS

def apply_plan(session, snapshot_path, plan_path, actor):
    plan=json.loads(Path(plan_path).read_text())
    identifier=plan['id']
    if not isinstance(identifier,str) or not 1 <= len(identifier) <= 100:
        raise ValueError('Invalid operator plan identifier')
    completed=session.data.get('operator_preparations',{})
    if identifier in completed:
        return False
    if hashlib.sha256(Path(snapshot_path).read_bytes()).hexdigest()!=plan['expected_snapshot_sha256']:
        raise ValueError('Operator plan source changed; regenerate from current session')
    steps=plan['steps']
    if not isinstance(steps,list) or not 1 <= len(steps) <= 1000:
        raise ValueError('Invalid operator plan length')
    duration=0
    for step in steps:
        if not isinstance(step,list) or len(step)!=3:
            raise ValueError('Invalid operator step')
        button,hold,release=step
        if button not in (*BUTTONS,'WAIT') or type(hold)!=int or type(release)!=int or not 1<=hold<=120 or not 1<=release<=3600:
            raise ValueError('Invalid operator input')
        duration+=(hold if button!='WAIT' else 0)+release
    if duration>100000:
        raise ValueError('Operator frame budget exceeded')
    expected=plan['expected_video_sha256']
    if not isinstance(expected,str) or len(expected)!=64:
        raise ValueError('Missing final framebuffer digest')
    emulator=session.emulator
    for button,hold,release in steps:
        if button!='WAIT':
            emulator.holdButton(button,hold)
        emulator.advanceFrames(release)
    if hashlib.sha256(emulator.image.tobytes()).hexdigest()!=expected:
        raise ValueError('Operator final framebuffer differs from reviewed preview; state not published')
    completed=dict(completed)
    completed[identifier]=dict(frames=emulator.frames,actor=actor,video_sha256=expected)
    session.data['operator_preparations']=completed
    session.data['last']=dict(button='Trainer setup',duration=duration,player=actor,status='applied')
    return True
