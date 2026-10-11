"""Authenticated snapshots; a Git commit is the durable transaction boundary."""
import base64
import hashlib
import json
import os
import re
import zlib
from datetime import datetime
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

COMMAND = re.compile(r'\[gba\] (UP|DOWN|LEFT|RIGHT|A|B|L|R|START|SELECT)(?: (\d{1,3}))?\Z')
AAD = b'community-gba-session-v1'

def parse_command(title):
    match = COMMAND.fullmatch(title)
    if not match:
        raise ValueError('Use [gba] BUTTON or [gba] BUTTON FRAMES')
    frames = int(match[2] or '12')
    if not 1 <= frames <= 120:
        raise ValueError('Duration must be 1..120 frames')
    return match[1], frames

def key_from_env():
    key = base64.b64decode(os.environ['GBA_STATE_KEY'],validate=True)
    if len(key) != 32:
        raise ValueError('GBA_STATE_KEY must encode exactly 32 bytes')
    return key

def encode(snapshot, key):
    nonce = os.urandom(12)
    payload = zlib.compress(json.dumps(snapshot,sort_keys=True).encode())
    return nonce + AESGCM(key).encrypt(nonce,payload,AAD)

def decode(data, key):
    return json.loads(zlib.decompress(AESGCM(key).decrypt(data[:12],data[12:],AAD)))

class Session:
    def __init__(self, emulator, snapshot=None, boot_frames=120, release_frames=2):
        self.emulator = emulator
        self.release_frames = release_frames
        self.data = snapshot or dict(schema=1,rom=emulator.rom_hash,version=emulator.version,
                                     frames=0,total=0,ledger={},last=None)
        if snapshot:
            if snapshot['schema'] != 1 or snapshot['rom'] != emulator.rom_hash or snapshot['version'] != emulator.version:
                raise ValueError('Session ROM/emulator mismatch; explicit migration required')
            emulator.restore(base64.b64decode(snapshot['state']))
            self._restore_battery(base64.b64decode(snapshot['battery']))
            emulator.frames = snapshot['frames']
            # Preserve the last actual video callback alongside the savestate;
            # a queue sweep with no inputs must not advance the adventure.
            from PIL import Image
            emulator.image = Image.frombytes('RGB',(240,160),base64.b64decode(snapshot['video']))
        else:
            emulator.advanceFrames(boot_frames)

    def _battery(self):
        return self.emulator.battery()

    def _restore_battery(self, data):
        # libretro restores the SAVEDATA extension into mGBA's live save mask.
        # The redundant battery export verifies that restored SRAM agrees.
        if data != self.emulator.battery():
            raise ValueError('Snapshot battery content mismatch')

    def process(self, issue):
        event = str(issue['number'])
        if event in self.data['ledger']:
            return self.data['ledger'][event]
        record = dict(issue=issue['number'],player=issue['user']['login'],created=issue['created_at'])
        try:
            button,frames = parse_command(issue['title'])
        except ValueError as error:
            record.update(status='rejected',reason=str(error))
        else:
            instant = datetime.fromisoformat(issue['created_at'].replace('Z','+00:00')).timestamp()
            previous = [r for r in self.data['ledger'].values() if r['player']==record['player'] and r['status']=='applied']
            if previous and instant - max(datetime.fromisoformat(r['created'].replace('Z','+00:00')).timestamp() for r in previous) < 30:
                record.update(status='rejected',reason='One accepted command per player per 30 seconds')
            else:
                before,battery,frame_number = self.emulator.state(),self._battery(),self.emulator.frames
                old_image = self.emulator.image.copy()
                try:
                    self.emulator.holdButton(button,frames)
                    self.emulator.advanceFrames(self.release_frames)
                    # Assert serializability before committing metadata.
                    result = self.emulator.state()
                except Exception:
                    self.emulator.restore(before)
                    self._restore_battery(battery)
                    self.emulator.frames = frame_number
                    self.emulator.image = old_image
                    raise  # no ledger entry: retry after repairing the failure
                record.update(status='applied',button=button,duration=frames,
                              state_sha256=hashlib.sha256(result).hexdigest())
                self.data['total'] += 1
                self.data['last'] = record
        self.data['ledger'][event] = record
        return record

    def snapshot(self):
        return dict(self.data, frames=self.emulator.frames,
                    state=base64.b64encode(self.emulator.state()).decode(),
                    battery=base64.b64encode(self._battery()).decode(),
                    video=base64.b64encode(self.emulator.image.tobytes()).decode())
