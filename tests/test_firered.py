"""Run only when a private cartridge is explicitly supplied; no ROM fixtures."""
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from community.emulator import Emulator
from community.session import Session


@unittest.skipUnless(os.environ.get('FIRERED_ROM'), 'Private FireRed cartridge not provided')
class FireRedIntegrationTests(unittest.TestCase):
    def test_private_cartridge_boot_input_and_new_core_continuation(self):
        rom = Path(os.environ['FIRERED_ROM'])
        self.assertEqual(rom.read_bytes()[0xac:0xb0], b'BPRE')
        core = os.environ['MGBA_CORE']
        e = Emulator(core)
        try:
            e.loadGame(rom)
            session = Session(e, boot_frames=3600, release_frames=60)
            self.assertEqual(e.image.size, (240, 160))
            self.assertGreater(len(set(e.image.getdata())), 20)
            snapshot = session.snapshot()
            battery = e.battery()
            self.assertEqual(len(battery), 131072)
            issue = dict(number=1, title='[gba] START 12',
                         user={'login': 'integration-test'}, created_at='2026-10-11T00:00:00Z')
            session.process(issue)
            expected = hashlib.sha256(e.image.tobytes()).hexdigest()
            expected_battery = e.battery()
            e.close()
            e = Emulator(core)
            e.loadGame(rom)
            session = Session(e, snapshot, release_frames=60)
            self.assertEqual(e.battery(), battery)
            session.process(issue)
            self.assertEqual(hashlib.sha256(e.image.tobytes()).hexdigest(), expected)
            self.assertEqual(e.battery(), expected_battery)
            self.assertEqual(e.frames, 3672)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'battery.sav'
                e.persistSave(path)
                e.loadSave(path)
                self.assertEqual(e.battery(), expected_battery)
        finally:
            e.close()
