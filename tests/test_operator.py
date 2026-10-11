import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from PIL import Image
from community.operator import apply_plan

class OperatorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source=Path(self.temp.name)/'state.enc'
        self.source.write_bytes(b'original private snapshot')
        self.path=Path(self.temp.name)/'plan.json'
        self.emulator=Mock(frames=100,image=Image.new('RGB',(240,160)))
        self.session=SimpleNamespace(emulator=self.emulator,data={'total':3,'ledger':{'32':{'status':'applied'}}})
        self.plan=dict(id='trainer',expected_snapshot_sha256=hashlib.sha256(self.source.read_bytes()).hexdigest(),
                      expected_video_sha256=hashlib.sha256(self.emulator.image.tobytes()).hexdigest(),steps=[['A',12,60]])

    def apply(self):
        self.path.write_text(json.dumps(self.plan))
        return apply_plan(self.session,self.source,self.path,'maintainer')

    def test_once_preserves_visitor_ledger(self):
        self.assertTrue(self.apply())
        self.assertFalse(self.apply())
        self.emulator.holdButton.assert_called_once_with('A',12)
        self.assertEqual(self.session.data['total'],3)
        self.assertEqual(self.session.data['ledger'],{'32':{'status':'applied'}})

    def test_changed_source_or_invalid_later_step_never_runs(self):
        self.source.write_bytes(b'new visitor turn')
        with self.assertRaises(ValueError): self.apply()
        self.plan['expected_snapshot_sha256']=hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.plan['steps'].append(['A',999,60])
        with self.assertRaises(ValueError): self.apply()
        self.emulator.holdButton.assert_not_called()

    def test_wrong_final_frame_never_records_completion(self):
        self.plan['expected_video_sha256']='0'*64
        with self.assertRaises(ValueError): self.apply()
        self.assertNotIn('operator_preparations',self.session.data)
        self.assertEqual(self.session.data['total'],3)
