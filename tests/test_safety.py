"""Pure-Python safety regression tests; no private ROM or core required."""
import copy
import struct
import tempfile
import unittest
from pathlib import Path

from community.safety import (
    UnsafeSaveChange, backup_name, firered_trainer_id, protect_firered_save,
    recover_snapshot, save_turn_backups,
)
from community.session import Session


def save_with_trainer(trainer, counter=1, slot=0, offset=0):
    data = bytearray([0xFF] * (128 * 1024))
    sector = bytearray(4096)
    sector[:8] = b'PLAYER\xff\xff'
    sector[0xA:0xE] = trainer
    values = struct.unpack_from('<' + 'I' * (0xF24 // 4), sector)
    total = sum(values) & 0xFFFFFFFF
    checksum = ((total >> 16) + total) & 0xFFFF
    struct.pack_into('<HHII', sector, 0xFF4, 0, checksum, 0x08012025, counter)
    start = (slot * 14 + offset) * 4096
    data[start:start + 4096] = sector
    return bytes(data)


def session_snapshot(ids, total, last=None):
    ledger = {str(number): dict(issue=number, player='p', status='applied')
              for number in ids}
    return dict(schema=1, rom='same-rom', version='0.10.5',
                frames=total * 72, total=total, ledger=ledger, last=last,
                state='encrypted-in-production', video='private', battery='private')


class GameSafetyTests(unittest.TestCase):
    def test_trainer_id_from_valid_sector(self):
        trainer = b'\x01\x02\x03\x04'
        self.assertEqual(firered_trainer_id(save_with_trainer(trainer)), trainer)
        self.assertIsNone(firered_trainer_id(bytes(128 * 1024)))

    def test_newer_rotated_slot_and_checksum_verification(self):
        older = bytearray(save_with_trainer(b'ABCD', counter=3))
        newer = save_with_trainer(b'EFGH', counter=4, slot=1, offset=10)
        start = (14 + 10) * 4096
        older[start:start + 4096] = newer[start:start + 4096]
        self.assertEqual(firered_trainer_id(older), b'EFGH')
        older[start + 0xFF6] ^= 1
        self.assertEqual(firered_trainer_id(older), b'ABCD')

    def test_wraparound_save_counter(self):
        old = bytearray(save_with_trainer(b'ABCD', counter=0xFFFFFFFF))
        new = save_with_trainer(b'EFGH', counter=0, slot=1)
        old[14*4096:15*4096] = new[14*4096:15*4096]
        self.assertEqual(firered_trainer_id(old), b'EFGH')

    def test_preserve_same_trainer_and_allow_first_save(self):
        before = save_with_trainer(b'ABCD', counter=9)
        after = save_with_trainer(b'ABCD', counter=10)
        protect_firered_save(before, after)
        protect_firered_save(bytes(128 * 1024), after)

    def test_block_accidental_new_trainer(self):
        with self.assertRaises(UnsafeSaveChange):
            protect_firered_save(save_with_trainer(b'ABCD'),
                                 save_with_trainer(b'WXYZ'))

    def test_retains_only_latest_twenty_before_turn_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidates = [(i, f'encrypted-{i}'.encode()) for i in range(1, 28)]
            save_turn_backups(tmp, candidates)
            directory = Path(tmp) / '.community' / 'backups'
            entries = sorted(directory.iterdir())
            self.assertEqual(len(entries), 20)
            self.assertEqual(entries[0].name, backup_name(8))
            self.assertEqual(entries[-1].read_bytes(), b'encrypted-27')

    def test_restoration_tombstones_replayed_issues(self):
        before = session_snapshot([1], 1, last=dict(button='RIGHT', player='p', duration=12))
        current = session_snapshot([1, 2, 3], 3)
        rescued = recover_snapshot(current, before, 2, 'maintainer')
        self.assertEqual(rescued['total'], 1)
        self.assertEqual(rescued['frames'], before['frames'])
        self.assertEqual(rescued['last'], before['last'])
        self.assertEqual(rescued['ledger']['2']['status'], 'reverted')
        self.assertEqual(rescued['ledger']['3']['status'], 'reverted')
        self.assertEqual(rescued['ledger']['1']['status'], 'applied')
        # The normal queue's exactly-once check must not execute this Issue.
        stub = Session.__new__(Session)
        stub.data = rescued
        issue = dict(number=2, title='[gba] A', user=dict(login='p'),
                     created_at='2026-11-03T12:00:00Z')
        self.assertEqual(stub.process(issue)['status'], 'reverted')

    def test_rejects_divergent_and_wrong_session_checkpoints(self):
        current = session_snapshot([1, 2], 2)
        candidate = session_snapshot([1], 1)
        corrupted = copy.deepcopy(candidate)
        corrupted['rom'] = 'another-rom'
        with self.assertRaises(ValueError):
            recover_snapshot(current, corrupted, 2, 'maintainer')
        corrupted = copy.deepcopy(candidate)
        corrupted['ledger']['1']['player'] = 'impostor'
        with self.assertRaises(ValueError):
            recover_snapshot(current, corrupted, 2, 'maintainer')
        with self.assertRaises(ValueError):
            recover_snapshot(current, current, 2, 'maintainer')


if __name__ == '__main__':
    unittest.main()
