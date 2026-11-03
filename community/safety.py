"""FireRed save identity guard and private encrypted turn checkpoints.

Only encrypted snapshots are written. No ROM, SRAM or game state is public.
"""
import copy
import struct
from datetime import datetime, timezone
from pathlib import Path

BACKUP_LIMIT = 20
SECTOR_SIZE = 4096
SAVEBLOCK2_SIZE = 0xF24
SIGNATURE = 0x08012025


class UnsafeSaveChange(ValueError):
    """A recorded FireRed trainer was replaced by a different trainer."""


def _sector0(save, slot):
    """Return (counter, trainer_id) only for a valid FireRed SaveBlock2 sector."""
    for position in range(slot * 14 * SECTOR_SIZE, (slot + 1) * 14 * SECTOR_SIZE, SECTOR_SIZE):
        sector = save[position:position + SECTOR_SIZE]
        section_id, checksum, signature, counter = struct.unpack_from('<HHII', sector, 0xFF4)
        if section_id != 0 or signature != SIGNATURE:
            continue
        words = struct.unpack_from('<' + 'I' * (SAVEBLOCK2_SIZE // 4), sector)
        total = sum(words) & 0xFFFFFFFF
        if ((total >> 16) + total) & 0xFFFF != checksum:
            continue
        name = sector[:8]
        if not name or all(byte in (0, 0xFF) for byte in name):
            continue
        return counter, sector[0xA:0xE]
    return None


def firered_trainer_id(save):
    """Read trainer ID from newest checksum-valid battery-save slot, if any."""
    if len(save) != 128 * 1024:
        return None
    first, second = _sector0(save, 0), _sector0(save, 1)
    if first is None and second is None:
        return None
    if first is None:
        return second[1]
    if second is None:
        return first[1]
    # Serial number arithmetic handles the 32-bit save counter wrap.
    newest = second if 0 < ((second[0] - first[0]) & 0xFFFFFFFF) < 0x80000000 else first
    return newest[1]


def protect_firered_save(before, after):
    original, current = firered_trainer_id(before), firered_trainer_id(after)
    if original is not None and current is not None and original != current:
        raise UnsafeSaveChange('Trainer identity changed; the shared save was protected')


def backup_name(issue_number):
    if type(issue_number) is not int or issue_number <= 0:
        raise ValueError('Backup issue ID must be a positive integer')
    return f'turn-{issue_number:012d}.enc'


def save_turn_backups(state_root, candidates, limit=BACKUP_LIMIT):
    """Store pre-turn encrypted snapshots on the PRIVATE state checkout only."""
    if type(limit) is not int or limit < 1:
        raise ValueError('Invalid backup limit')
    if not candidates:
        return
    directory = Path(state_root) / '.community' / 'backups'
    directory.mkdir(parents=True, exist_ok=True)
    for number, encrypted in candidates:
        target = directory / backup_name(number)
        temporary = target.with_suffix('.tmp')
        temporary.write_bytes(encrypted)
        temporary.replace(target)
    existing = sorted(directory.glob('turn-*.enc'))
    for old in existing[:-limit]:
        old.unlink()


def recover_snapshot(current, restored, turn_number, actor):
    """Restore game state while retaining durable ledger tombstones.

    Entries processed after the checkpoint are kept as 'reverted', preventing
    GitHub's historical Issue queue from replaying destructive commands.
    """
    if current is None or restored is None:
        raise ValueError('Recovery requires the current session and a checkpoint')
    if (restored['schema'], restored['rom'], restored['version']) != (
            current['schema'], current['rom'], current['version']):
        raise ValueError('Checkpoint belongs to a different session or emulator')
    if str(turn_number) in restored['ledger']:
        raise ValueError('Checkpoint is not from before the requested turn')
    if not isinstance(actor, str) or not actor:
        raise ValueError('Recovery actor is required')
    # The restored history must genuinely precede the present ledger.
    for number, record in restored['ledger'].items():
        if current['ledger'].get(number) != record:
            raise ValueError('Checkpoint ledger diverges from current game history')
    if restored['total'] > current['total']:
        raise ValueError('Recovery would advance the turn counter')
    result = copy.deepcopy(restored)
    for number, record in current['ledger'].items():
        if number not in result['ledger']:
            tombstone = copy.deepcopy(record)
            if tombstone['status'] == 'applied':
                tombstone['status'] = 'reverted'
                tombstone['reason'] = f'Restored checkpoint before Issue #{turn_number}'
            result['ledger'][number] = tombstone
    history = copy.deepcopy(current.get('recoveries', []))
    history.append(dict(issue=turn_number, actor=actor,
                        at=datetime.now(timezone.utc).isoformat(),
                        reverted=sum(r['status'] == 'reverted' for r in result['ledger'].values())))
    result['recoveries'] = history[-20:]
    return result
