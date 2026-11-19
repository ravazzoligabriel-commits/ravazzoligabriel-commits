import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import recap

ROOT = Path(__file__).resolve().parent
DAY = date(2026, 11, 3)
ZONE = ZoneInfo("America/Sao_Paulo")


class ReportParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.images, self.scripts = [], [], 0

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == "tr" and "data-player" in data:
            self.rows.append(data["data-player"])
        if tag == "img":
            self.images.append(data.get("src", ""))
        if tag == "script":
            self.scripts += 1


def event(issue, timestamp, name="Ana", button="A", duration=12, status="applied"):
    return dict(issue=issue, created=timestamp, player=name, button=button,
                duration=duration, status=status)


class RecapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input = self.root / "input.json"
        self.out = self.root / "saida"

    def write(self, events):
        self.input.write_text(json.dumps(events), encoding="utf-8")

    def make(self, frames=None):
        return recap.generate(self.input, DAY, ZONE, frames, self.out)

    def test_fuso_ordem_rejeitados_e_duplicados(self):
        a = event(2, "2026-11-03T03:01:00Z")
        b = event(6, "2026-11-04T02:59:00Z", name="ANA", button="B", duration=120)
        c = event(3, "2026-11-04T03:00:00Z")
        self.write({"events":[b, c, a, a, event(1, "2026-11-03T02:59:00Z"),
                              {"created":"2026-11-03T13:00:00Z", "status":"rejected"}]})
        day = recap.read_day(self.input, DAY, ZONE)
        self.assertEqual([v.issue for v in day.events], [2, 6])
        self.assertEqual(day.ignored, 1)
        self.assertEqual(recap.summary(day, 0, 0)["players"], 1)
        self.assertEqual(recap.summary(day, 0, 0)["frames_held"], 132)

    def test_aliases_e_entrada_sem_fuso(self):
        self.write([{"issue":1,"timestamp":"2026-11-03T12:00:00-03:00",
                     "player":"P","button":"left","frames":6,"status":"applied"}])
        self.assertEqual(recap.read_day(self.input, DAY, ZONE).events[0].button, "LEFT")
        self.write([event(1, "2026-11-03T12:00:00")])
        with self.assertRaisesRegex(ValueError, "fuso"):
            self.make()

    def test_dados_divergentes_e_comando_invalido(self):
        a = event(6, "2026-11-03T10:00:00Z")
        self.write([a, dict(a, duration=24)])
        with self.assertRaisesRegex(ValueError, "divergentes"):
            self.make()
        for edit in ({"duration":0}, {"duration":121}, {"duration":True}, {"button":"TURBO"}, {"status":None}):
            self.write([dict(a, **edit)])
            with self.assertRaises(ValueError):
                self.make()

    def test_pagina_sem_midia_escapa_texto_e_cobre_dia_vazio(self):
        name = '<script>nome & "teste"</script>'
        self.write([event(7, "2026-11-03T12:00:00Z", name=name)])
        stats, paths = self.make()
        parsed = ReportParser()
        parsed.feed(paths[0].read_text())
        self.assertEqual(parsed.rows, [name])
        self.assertEqual(parsed.scripts, 1)
        self.assertEqual(parsed.images, [])
        self.assertEqual(stats["captures"], 0)
        self.write([])
        stats, paths = self.make()
        self.assertEqual(stats["commands"], 0)
        self.assertIn("Nenhum comando aplicado", paths[0].read_text())

    def test_quadros_locais_em_ordem_e_sem_ambiguidade(self):
        self.write([event(7, "2026-11-03T12:00:00Z")])
        events = recap.read_day(self.input, DAY, ZONE).events
        for name in ["7-10.png","7-02.png","7.png","8.png","console.png","jogo.sav"]:
            (self.root/name).touch()
        frames = recap.locate_frames(self.root, events)
        self.assertEqual([p.name for p in frames[7]], ["7.png", "7-02.png", "7-10.png"])
        (self.root/"7-2.jpg").touch()
        with self.assertRaisesRegex(ValueError, "posição"):
            recap.locate_frames(self.root, events)

    def test_erro_na_troca_restaura_resultado_anterior(self):
        self.write([event(6, "2026-11-03T10:00:00Z")])
        _, previous = self.make()
        originals = {p: p.read_bytes() for p in previous}
        self.write([event(9, "2026-11-03T10:00:00Z", name="Outro")])
        replace = os.replace
        def fail_html(source, target):
            if Path(source).name.startswith("recap-") and Path(target).suffix == ".html":
                raise OSError("falha de teste")
            return replace(source, target)
        with patch("recap.os.replace", side_effect=fail_html):
            with self.assertRaises(OSError):
                self.make()
        self.assertEqual(originals, {p:p.read_bytes() for p in previous})

    def test_recursos_multimidia_com_imagens_sinteticas(self):
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            self.skipTest("Instale Pillow para testar a saída GIF.")
        self.write([
            event(101, "2026-11-03T13:00:00Z", name="Mika", button="A", duration=12),
            event(102, "2026-11-03T13:03:00Z", name="Sol", button="LEFT", duration=24),
            event(103, "2026-11-03T13:06:00Z", name="Mika", button="B", duration=6),
            {"issue":104, "created":"2026-11-03T13:08:00Z", "status":"rejected"},
        ])
        captures = self.root / "capturas"
        captures.mkdir()
        # Quadrados coloridos criados pelo teste. Cada imagem tem uma associação conhecida.
        for index, filename in enumerate(("101.png", "103-01.png", "103-02.png")):
            image = Image.new("RGB", (48, 32), (32, 44, 58))
            ImageDraw.Draw(image).rectangle((index*5, 4, index*5+12, 16), fill=(230, 169, 55))
            image.save(captures / filename)
        state, files = self.make(captures)
        self.assertEqual([state[k] for k in ("commands","players","frames_held","captures","commands_with_capture","ignored_records")],
                         [3,2,42,3,2,1])
        with Image.open(files[2]) as gif:
            self.assertEqual((gif.size, gif.n_frames), ((722, 406), 3))
        parsed = ReportParser()
        parsed.feed(files[0].read_text())
        self.assertEqual(parsed.rows, ["Mika", "Sol", "Mika"])
        self.assertTrue(all(x.startswith("data:image/png;base64,") for x in parsed.images))
        self.assertEqual(len(parsed.images), 4)
        self.make()
        self.assertFalse(files[2].exists())

    def test_cli_sem_dependencias_para_resumo_de_texto(self):
        self.write([event(6,"2026-11-03T10:00:00Z")])
        args = [sys.executable, "-S", str(ROOT/"recap.py"), "--events", str(self.input),
                "--date", DAY.isoformat(), "--out", str(self.out)]
        if os.name == 'nt':
            self.skipTest("Instalações de Windows podem depender de tzdata em site-packages.")
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.out/"recap-2026-11-03.html").is_file())


if __name__ == "__main__":
    unittest.main()
