import base64
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from community.emulator import Emulator, BUTTONS
from community.session import Session, encode, decode, parse_command
from community.render import render
from homebrew.build import build

class RealEmulatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        build(self.root/'demo.gba')
        self.e = Emulator(os.environ['MGBA_CORE'])
        self.e.loadGame(self.root/'demo.gba')
        self.s = Session(self.e)

    def tearDown(self):
        self.e.close()
        self.temp.cleanup()

    def issue(self,number=1,button='RIGHT',player='visitor',time='2026-10-11T00:00:00Z'):
        return dict(number=number,title=f'[gba] {button} 24',user={'login':player},created_at=time)

    def pixels(self):
        return hashlib.sha256(self.e.image.tobytes()).hexdigest()

    def test_actual_input_changes_frame_and_battery(self):
        before=self.pixels(); battery=self.s._battery()
        result=self.s.process(self.issue())
        self.assertEqual(result['status'],'applied')
        self.assertNotEqual(self.pixels(),before)
        self.assertNotEqual(self.s._battery()[:3],battery[:3])
        self.assertEqual(self.e.frames,146)

    def test_deterministic_replay_from_same_state(self):
        state=self.e.state(); battery=self.s._battery()
        self.e.holdButton('RIGHT',24); self.e.advanceFrames(2)
        first=self.pixels()
        self.e.restore(state); self.s._restore_battery(battery)
        self.e.holdButton('RIGHT',24); self.e.advanceFrames(2)
        self.assertEqual(first,self.pixels())

    def test_reload_in_new_core_continues_session(self):
        self.s.process(self.issue())
        snapshot=self.s.snapshot(); battery=self.s._battery()
        self.e.close()
        self.e=Emulator(os.environ['MGBA_CORE']); self.e.loadGame(self.root/'demo.gba')
        self.s=Session(self.e,snapshot)
        self.assertEqual(battery,self.s._battery())
        self.assertEqual(self.s.data['total'],1)
        self.s.process(self.issue(2,'LEFT','other'))
        self.assertNotEqual(self.s._battery()[:3],battery[:3])
        self.assertEqual(self.s.data['total'],2)

    def test_duplicate_issue_is_exactly_once(self):
        first=self.s.process(self.issue()); frames=self.e.frames; state=self.e.state()
        self.assertEqual(self.s.process(self.issue()),first)
        self.assertEqual(frames,self.e.frames)
        self.assertEqual(state,self.e.state())

    def test_snapshot_ledger_is_independent_of_future_turns(self):
        snapshot = self.s.snapshot()
        self.s.process(self.issue())
        self.assertEqual(snapshot['ledger'], {})
        self.assertEqual(snapshot['total'], 0)
        self.assertIsNone(snapshot['last'])

    def test_conflicting_commands_are_serial(self):
        self.s.process(self.issue(1,'RIGHT','one'))
        right=self.s._battery()
        self.s.process(self.issue(2,'LEFT','two'))
        self.assertLess(self.s._battery()[1],right[1])
        self.assertEqual(self.s.data['total'],2)

    def test_invalid_input_never_changes_emulator(self):
        state=self.e.state()
        for n,title in enumerate(('[gba] A 0','[gba] A 121','[gba] RIGHT; rm -rf /','[gba] A\nUP','[gba] A $(whoami)'),1):
            issue=self.issue(n); issue['title']=title
            self.assertEqual(self.s.process(issue)['status'],'rejected')
        self.assertEqual(state,self.e.state())

    def test_rate_limit_survives_snapshot(self):
        self.s.process(self.issue())
        restored=Session(self.e,self.s.snapshot())
        self.assertEqual(restored.process(self.issue(2,'LEFT'))['status'],'rejected')
        self.assertEqual(restored.process(self.issue(3,'LEFT',time='2026-10-11T00:00:31Z'))['status'],'applied')

    def test_failure_restores_state_battery_and_frame(self):
        before=self.e.state(); battery=self.s._battery(); frames=self.e.frames; pixels=self.pixels()
        original=self.e.holdButton
        def fail(button,n):
            original(button,n)
            raise RuntimeError('injected after real input')
        self.e.holdButton=fail
        with self.assertRaises(RuntimeError):
            self.s.process(self.issue())
        self.assertEqual(before,self.e.state())
        self.assertEqual(battery,self.s._battery())
        self.assertEqual(frames,self.e.frames)
        self.assertEqual(pixels,self.pixels())
        self.assertFalse(self.s.data['ledger'])

    def test_battery_export_import(self):
        path=self.root/'save.sav'
        result=self.e.persistSave(path)
        self.assertEqual(result['bytes'],32768)
        self.s.process(self.issue())
        self.e.loadSave(path)
        self.assertEqual(self.s._battery(),path.read_bytes())

    def test_all_ten_buttons_and_bounded_frames(self):
        for button in BUTTONS:
            self.e.pressButton(button)
        for value in (0,121,-1,True,'12'):
            with self.assertRaises(ValueError):
                self.e.holdButton('A',value)
        with self.assertRaises(ValueError):
            self.e.advanceFrames(3601)

    def test_closed_core_fails_safely(self):
        self.e.close()
        self.e.close()
        for operation in (lambda:self.e.advanceFrames(1), lambda:self.e.state(),
                          lambda:self.e.restore(b''), lambda:self.e.loadGame(self.root/'demo.gba')):
            with self.assertRaises(ValueError):
                operation()

    def test_authenticated_snapshot_rejects_corruption_and_mismatch(self):
        key=bytes(range(32)); snapshot=self.s.snapshot()
        data=encode(snapshot,key)
        self.assertEqual(snapshot,decode(data,key))
        with self.assertRaises(Exception):
            decode(data[:-1]+bytes([data[-1]^1]),key)
        with self.assertRaises(Exception):
            decode(data,bytes(32))
        snapshot['rom']='wrong'
        with self.assertRaises(ValueError):
            Session(self.e,snapshot)

    def test_renderer_preserves_profile_and_versions_real_screen(self):
        original='# My profile\n\nExisting content.\n'
        (self.root/'README.md').write_text(original)
        render(self.root,self.e,self.s,'owner/repo','main')
        text=(self.root/'README.md').read_text(encoding='utf-8')
        self.assertIn(original,text)
        self.assertIn('Create / Submit new issue',text)
        self.assertNotIn('PALLET TOWN',text)
        first=list((self.root/'assets/community').glob('console-*.png'))[0].name
        self.s.process(self.issue())
        render(self.root,self.e,self.s,'owner/repo','main')
        self.assertEqual((self.root/'README.md').read_text(encoding='utf-8').count(original),1)
        self.assertEqual(len(list((self.root/'assets/community').glob('console-*.png'))),2)
        self.assertNotEqual(first, max((self.root/'assets/community').glob('console-*.png'),key=lambda p:p.stat().st_mtime).name)

if __name__=='__main__':
    unittest.main()
