#!/usr/bin/env python3
"""Recap local de um dia de comandos aplicados pelo GitBoy."""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

BUTTONS = {"UP", "DOWN", "LEFT", "RIGHT", "A", "B", "L", "R", "START", "SELECT"}
MONTHS = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
          "setembro", "outubro", "novembro", "dezembro")
FRAME_FILE = re.compile(r"([1-9]\d*)(?:-([0-9]+))?\.(png|jpe?g|webp)\Z", re.I)
REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")


@dataclass(frozen=True)
class Event:
    issue: int
    at: datetime
    player: str
    button: str
    frames: int


@dataclass
class Day:
    day: date
    zone: ZoneInfo
    events: list[Event]
    ignored: int


@dataclass
class Media:
    gif: bytes
    poster: bytes
    previews: dict[int, list[str]]
    count: int


def local_date(value: date) -> str:
    return f"{value.day} de {MONTHS[value.month - 1]} de {value.year}"


def integer(value: object, label: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{label} precisa ser um número inteiro.")
    return value


def instant(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("created precisa conter uma data ISO 8601.")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("created exige um fuso explícito, por exemplo 2026-11-03T12:00:00Z.")
    return result.astimezone(timezone.utc)


def read_day(path: Path, chosen: date, zone: ZoneInfo) -> Day:
    try:
        records = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON inválido em {path.name}, linha {error.lineno}.") from error
    if isinstance(records, dict):
        records = records.get("events")
    if not isinstance(records, list):
        raise ValueError("A entrada deve ser uma lista ou um objeto com a lista events.")
    accepted: dict[int, Event] = {}
    ignored = 0
    for number, item in enumerate(records, 1):
        try:
            if not isinstance(item, dict):
                raise ValueError("o registro precisa ser um objeto.")
            at = instant(item.get("created", item.get("timestamp")))
            if at.astimezone(zone).date() != chosen:
                continue
            status = item.get("status")
            if not isinstance(status, str) or not status.strip():
                raise ValueError("o registro precisa indicar status; comandos executados usam applied.")
            if status != "applied":
                ignored += 1
                continue
            issue = integer(item.get("issue"), "issue")
            frames = integer(item.get("duration", item.get("frames")), "duration")
            player, button = item.get("player"), item.get("button")
            if issue < 1:
                raise ValueError("issue deve ser positiva.")
            if not isinstance(player, str) or not player.strip() or any(ord(c) < 32 for c in player):
                raise ValueError("player precisa conter um nome legível.")
            if not isinstance(button, str) or button.upper() not in BUTTONS:
                raise ValueError("botão GBA desconhecido.")
            if not 1 <= frames <= 120:
                raise ValueError("o GitBoy aceita comandos de 1 a 120 frames.")
            event = Event(issue, at, player.strip(), button.upper(), frames)
            if issue in accepted and accepted[issue].player.casefold() == event.player.casefold():
                event = replace(event, player=accepted[issue].player)
            if issue in accepted and accepted[issue] != event:
                raise ValueError(f"a issue #{issue} tem dois comandos aplicados divergentes.")
            accepted[issue] = event
        except (ValueError, TypeError, OverflowError) as error:
            raise ValueError(f"Entrada {number}: {error}") from error
    events = sorted(accepted.values(), key=lambda event: (event.at, event.issue))
    names: dict[str, str] = {}
    for i, event in enumerate(events):
        display = names.setdefault(event.player.casefold(), event.player)
        if display != event.player:
            events[i] = replace(event, player=display)
    return Day(chosen, zone, events, ignored)


def locate_frames(directory: Path | None, events: list[Event]) -> dict[int, list[Path]]:
    if directory is None:
        return {}
    root = directory.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("--frames-dir precisa apontar para uma pasta.")
    ids = {event.issue for event in events}
    result: dict[int, dict[int, Path]] = defaultdict(dict)
    for item in sorted(root.iterdir(), key=lambda p: p.name):
        match = FRAME_FILE.fullmatch(item.name)
        if not match or int(match[1]) not in ids:
            continue
        if not item.is_file() or item.resolve().parent != root:
            raise ValueError(f"Captura fora da pasta informada ou inválida: {item.name}.")
        issue, order = int(match[1]), int(match[2] or 0)
        if order in result[issue]:
            raise ValueError(f"Duas capturas ocupam a posição {order} da issue #{issue}.")
        result[issue][order] = item
    return {i: [paths[k] for k in sorted(paths)] for i, paths in result.items()}


def data_uri(content: bytes, kind: str) -> str:
    return f"data:image/{kind};base64," + base64.b64encode(content).decode("ascii")


def png_bytes(image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def make_media(day: Day, files: dict[int, list[Path]], hold: int) -> Media | None:
    if not files:
        return None
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageOps
    except ImportError as error:
        raise ValueError("As capturas exigem Pillow. Instale com python -m pip install Pillow.") from error
    def font(size: int, bold: bool = False):
        try:
            return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)
        except OSError:
            return ImageFont.load_default(size=size)
    fonts = {k: font(s, b) for k, s, b in [
        ("brand", 25, True), ("title", 20, True), ("button", 35, True),
        ("label", 12, True), ("body", 16, False), ("small", 13, False)]}
    ink, purple, mint, grey, bright = "#151725", "#b5a7fc", "#91d9b9", "#b2b6c7", "#f4f2fa"
    frames, previews = [], defaultdict(list)
    poster = b""
    total = len(day.events)
    for number, event in enumerate(day.events, 1):
        paths = files.get(event.issue, [])
        for seq, path in enumerate(paths, 1):
            try:
                with Image.open(path) as src:
                    shot = src.convert("RGB")
                    shot = ImageOps.contain(shot, (480, 320), Image.Resampling.NEAREST)
            except (OSError, ValueError, Image.DecompressionBombError) as error:
                raise ValueError(f"Captura ilegível: {path.name}.") from error
            thumb = ImageOps.contain(shot, (240, 160), Image.Resampling.NEAREST)
            previews[event.issue].append(data_uri(png_bytes(thumb), "png"))
            card = Image.new("RGB", (722, 406), ink)
            draw = ImageDraw.Draw(card)
            draw.rounded_rectangle((15, 13, 37, 35), radius=5, fill=mint)
            draw.line((21, 24, 31, 24), fill=ink, width=3)
            draw.line((26, 19, 26, 29), fill=ink, width=3)
            draw.text((47, 8), "GitBoy", font=fonts["brand"], fill=bright)
            draw.text((145, 17), "RECAP DIÁRIO", font=fonts["label"], fill=purple)
            draw.text((706, 15), day.day.strftime("%d.%m.%Y"), anchor="ra", font=fonts["body"], fill=grey)
            draw.rounded_rectangle((12, 46, 501, 375), radius=7, fill="#303246", outline="#565970", width=1)
            draw.rectangle((17, 51, 496, 370), fill="#0d1019")
            card.paste(shot, (17+(480-shot.width)//2, 51+(320-shot.height)//2))
            x = 519
            draw.text((x, 61), f"COMANDO {number:02d} / {total:02d}", font=fonts["label"], fill=mint)
            draw.text((x, 90), event.button, font=fonts["button"], fill=bright)
            draw.text((x, 147), f"{event.frames} frames", font=fonts["title"], fill=purple)
            draw.line((x, 193, 701, 193), fill="#383c50", width=1)
            draw.text((x, 209), "JOGADOR", font=fonts["label"], fill=grey)
            handle = "@" + event.player
            # Divide nomes longos pela largura real do texto.
            lines = []
            while handle:
                end = 1
                while end < len(handle) and draw.textlength(handle[:end+1], font=fonts["body"]) <= 182:
                    end += 1
                lines.append(handle[:end]); handle = handle[end:]
            for offset, line in enumerate(lines[:3]):
                draw.text((x, 230 + offset * 18), line, font=fonts["body"], fill=bright)
            local = event.at.astimezone(day.zone)
            draw.text((x, 300), local.strftime("%H:%M:%S") + f"  ·  #{event.issue}", font=fonts["small"], fill=grey)
            if len(paths) > 1:
                draw.text((x, 329), f"Captura {seq}/{len(paths)}", font=fonts["small"], fill=mint)
            draw.rounded_rectangle((15, 389, 706, 394), radius=2, fill="#35394c")
            draw.rounded_rectangle((15, 389, 15+round(691*number/total), 394), radius=2, fill=mint)
            if not poster:
                poster = png_bytes(card)
            frames.append(card.quantize(colors=240, method=Image.Quantize.MEDIANCUT))
    gif = io.BytesIO()
    frames[0].save(gif, format="GIF", save_all=True, append_images=frames[1:], duration=hold,
                   loop=0, disposal=1, optimize=False)
    return Media(gif.getvalue(), poster, dict(previews), len(frames))


def summary(day: Day, capture_count: int, covered_commands: int) -> dict:
    players = Counter(e.player for e in day.events)
    return {"date": day.day.isoformat(), "timezone": day.zone.key, "commands": len(day.events),
            "players": len(players), "frames_held": sum(e.frames for e in day.events),
            "captures": capture_count, "commands_with_capture": covered_commands,
            "ignored_records": day.ignored,
            "leaderboard": [{"player": p, "commands": n} for p, n in sorted(players.items(), key=lambda item: (-item[1], item[0].casefold(), item[0]))]}


def table_html(day: Day, media: Media | None, repository: str | None) -> str:
    rows = []
    for item in day.events:
        local = item.at.astimezone(day.zone)
        issue = f"#{item.issue}"
        if repository:
            issue = f'<a href="https://github.com/{escape(repository)}/issues/{item.issue}" target="_blank" rel="noopener">{issue}</a>'
        shots = media.previews.get(item.issue, []) if media else []
        if shots:
            pictures = "".join(f'<img loading="lazy" width="240" alt="Captura {n} associada à issue {item.issue}" src="{src}">' for n, src in enumerate(shots, 1))
            label = "Ver captura" if len(shots) == 1 else f"Ver {len(shots)} capturas"
            capture = f'<details><summary>{label}</summary><div class="captures">{pictures}</div></details>'
        else:
            capture = 'Sem captura'
        rows.append(f'<tr data-player="{escape(item.player, quote=True)}"><td><time datetime="{item.at.isoformat()}">{local:%H:%M:%S}</time></td>'
                    f'<td class="handle">@{escape(item.player)}</td><td><kbd>{item.button}</kbd></td><td>{item.frames}</td><td>{issue}</td><td>{capture}</td></tr>')
    return "".join(rows)


@contextmanager
def output_lock(directory: Path):
    """Serializa a troca dos arquivos por processos da CLI no mesmo diretório."""
    if os.name == "nt":
        import msvcrt
        with (directory / ".gitboy-recap.lock").open("a+b") as handle:
            if not handle.tell():
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fd = os.open(directory, os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)


def write_artifacts(output: Path, artifacts: dict[Path, bytes], discard: list[Path]):
    with tempfile.TemporaryDirectory(dir=output, prefix=".gitboy-stage-") as temp:
        stage = Path(temp)
        for target, content in artifacts.items():
            (stage / target.name).write_bytes(content)
        with output_lock(output):
            previous: dict[Path, Path] = {}
            for target in (*artifacts, *discard):
                if target.is_symlink() or (target.exists() and not target.is_file()):
                    raise ValueError(f"O destino {target.name} precisa ser um arquivo comum.")
                if target.exists():
                    backup = stage / ("previous-" + target.name)
                    shutil.copyfile(target, backup)
                    previous[target] = backup
            changed = []
            try:
                for target in artifacts:
                    os.replace(stage / target.name, target)
                    changed.append(target)
                for target in discard:
                    if target.exists():
                        target.unlink()
                        changed.append(target)
            except OSError:
                for target in reversed(changed):
                    if target in previous:
                        os.replace(previous[target], target)
                    else:
                        target.unlink(missing_ok=True)
                raise


def generate(events: Path, chosen: date, zone: ZoneInfo, frames_dir: Path | None,
             output: Path, hold: int = 900, repository: str | None = None) -> tuple[dict, tuple[Path, ...]]:
    if not 20 <= hold <= 60000 or hold % 10:
        raise ValueError("--hold-ms precisa estar entre 20 e 60000, em múltiplos de 10 ms.")
    if repository and (not REPOSITORY.fullmatch(repository) or any(p in (".","..") for p in repository.split("/"))):
        raise ValueError("--repo deve ter o formato dono/repositorio.")
    day = read_day(events, chosen, zone)
    media = make_media(day, locate_frames(frames_dir, day.events), hold)
    stats = summary(day, media.count if media else 0, len(media.previews) if media else 0)
    html = page_html(day, stats, media, repository)
    output.mkdir(parents=True, exist_ok=True)
    base = "recap-" + chosen.isoformat()
    html_path, json_path, gif_path = (output/(base+suffix) for suffix in (".html",".json",".gif"))
    artifacts = {}
    if media:
        artifacts[gif_path] = media.gif
    artifacts[json_path] = (json.dumps(stats, ensure_ascii=False, indent=2)+"\n").encode("utf-8")
    artifacts[html_path] = html.encode("utf-8")
    write_artifacts(output, artifacts, [] if media else [gif_path])
    return stats, (html_path, json_path, gif_path) if media else (html_path, json_path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, required=True, help="Histórico JSON local")
    parser.add_argument("--date", type=date.fromisoformat, help="Data local AAAA-MM-DD, por padrão hoje")
    parser.add_argument("--timezone", default="America/Sao_Paulo", help="Fuso IANA do recap")
    parser.add_argument("--frames-dir", type=Path, help="Pasta com ISSUE.png ou ISSUE-001.png")
    parser.add_argument("--out", type=Path, required=True, help="Pasta para os resultados")
    parser.add_argument("--hold-ms", type=int, default=900, help="Tempo de exibição de cada captura no GIF")
    parser.add_argument("--repo", help="dono/repositorio para links públicos das issues")
    args = parser.parse_args(argv)
    try:
        zone = ZoneInfo(args.timezone)
        chosen = args.date or datetime.now(zone).date()
        stats, files = generate(args.events, chosen, zone, args.frames_dir, args.out, args.hold_ms, args.repo)
    except ZoneInfoNotFoundError:
        parser.exit(2, f"Fuso desconhecido: {args.timezone}. Verifique a base IANA ou instale tzdata.\n")
    except (OSError, ValueError) as error:
        parser.exit(2, f"Erro: {error}\n")
    print(f"{stats['commands']} comandos · {stats['players']} jogadores · {stats['frames_held']} frames pressionados · {stats['captures']} capturas.")
    for path in files:
        print(path)
    return 0

STYLE = """
:root{color-scheme:dark;--page:#111320;--card:#1b1e30;--line:#373b50;--text:#f1eff8;--muted:#bbc0d2;--violet:#b9aaff;--mint:#94dfbe;--sans:"DM Sans","Segoe UI",Arial,sans-serif;--mono:"IBM Plex Mono","Courier New",monospace}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 var(--sans);background:var(--page);color:var(--text)}
main,header>div,footer{width:min(1110px,92%);margin:auto}header{background:#171927;border-bottom:1px solid var(--line)}
header>div{display:flex;align-items:center;gap:13px;min-height:57px}.brand{font-size:25px;font-weight:850;letter-spacing:-.07em}.cross{display:inline-grid;place-items:center;width:24px;height:24px;border-radius:6px;color:#14241d;background:var(--mint);font-size:22px;font-weight:800;line-height:1}
.protocol{border-left:1px solid #40435b;padding-left:11px;color:var(--muted);font-size:12px}
h1,h2,p,figure{margin:0}h1{font-size:clamp(33px,5.2vw,66px);line-height:1.06;font-weight:650;letter-spacing:-.06em}h2{font-size:20px;line-height:1.2;letter-spacing:-.035em}
.intro{padding:27px 0 20px}.kicker{font:700 11px/1.4 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--mint);margin-bottom:7px}
.muted{font-size:13px;color:var(--muted);margin-top:8px}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));background:var(--card);border:1px solid var(--line);border-radius:8px;overflow:hidden}
.metric{padding:13px 16px}.metric+.metric{border-left:1px solid var(--line)}.metric strong{font:700 26px/1.2 var(--mono);color:var(--violet)}.metric span{display:block;color:var(--muted);font-size:12px}
.columns{display:grid;grid-template-columns:minmax(0,1.8fr) minmax(220px,1fr);gap:15px;margin:15px 0}
.box{background:var(--card);border:1px solid var(--line);border-radius:8px;overflow:hidden;min-width:0}
.head{padding:13px 16px;display:flex;align-items:center;justify-content:space-between;gap:10px}
.preview{display:block;width:100%;height:auto}
.caption{padding:11px 15px;font-size:12px;color:var(--muted);line-height:1.45}
button,select{font:inherit}button{cursor:pointer}.act{color:#17241d;background:var(--mint);border:0;border-radius:4px;font-size:12px;font-weight:750;padding:7px 10px}.act:hover{background:#b3f3d6}
a{color:var(--violet);text-underline-offset:3px}button:focus-visible,select:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid var(--mint);outline-offset:3px}
.rank{margin:0;padding:0 16px 11px;list-style:none}.rank li{padding:7px 0;border-top:1px solid var(--line)}
.rank-row,.table-head{display:flex;justify-content:space-between;align-items:center;gap:10px}.rank-row span{font-size:12px;overflow-wrap:anywhere}.rank-row strong{font:650 13px var(--mono);color:var(--mint)}
.rank-track{margin-top:4px;height:3px;background:#33364a;border-radius:3px}.rank-track i{height:100%;display:block;background:#8d83c7}
details>summary{color:var(--violet);cursor:pointer;font-size:12px;width:fit-content}
.more-rank{padding:0 16px 12px}.more-rank .rank{padding:7px 0 0}.empty{margin:0 16px 16px;color:var(--muted);font-size:13px}
.timeline{margin-bottom:18px}.table-head{padding:15px;flex-wrap:wrap}.table-head label{color:var(--muted);font-size:12px}
select{background:#262a40;color:var(--text);border:1px solid #4a4f68;padding:5px 8px;border-radius:4px;font-size:12px;max-width:min(255px,60vw)}
.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:13px;text-align:left;white-space:nowrap}
thead{font:600 10px/1.4 var(--sans);text-transform:uppercase;letter-spacing:.06em;color:#b4b9ce}
th,td{padding:9px 13px;border-top:1px solid var(--line);vertical-align:top}time,kbd,td:nth-child(4){font-family:var(--mono)}
kbd{display:inline-block;font-weight:700;font-size:11px;color:#dddbfa;background:#333349;border:1px solid #54516b;border-radius:4px;line-height:1.2;padding:3px 6px}
.captures{display:flex;flex-direction:column;gap:4px;padding:7px 0}.captures img{max-width:100%;image-rendering:pixelated}
.handle{font-weight:600}.hint{padding:0 15px 12px;font-size:12px;color:var(--muted)}
footer{font-size:11px;color:#989fb7;padding-bottom:18px}.blank{padding:25px 16px;background:#161928;line-height:1.5;font-size:14px;color:var(--muted)}
@media(max-width:700px){.columns{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,1fr)}.metric{padding:9px 13px}.metric:nth-child(3){border-left:0}.metric:nth-child(n+3){border-top:1px solid var(--line)}.kicker{font-size:10px}.intro{padding:20px 0 14px}.buttons{padding:6px}.head,.table-head{padding:12px}.rank li{padding:5px 0}}
"""

ACTIONS = """
const selector=document.getElementById("player-filter");
if(selector)selector.addEventListener("change",()=>{
  let count=0;
  for(const row of document.querySelectorAll("tbody tr")){
    row.hidden=Boolean(selector.value)&&row.dataset.player!==selector.value;
    if(!row.hidden)count++;
  }
  document.getElementById("shown").textContent=count;
});
const play=document.getElementById("play");
if(play){
  const img=document.getElementById("replay"),poster=img.src;
  let running=false;
  play.addEventListener("click",()=>{
    running=!running;
    img.src=running?play.dataset.gif:poster;
    play.setAttribute("aria-pressed",String(running));
    play.textContent=running?"Parar replay":"Reproduzir";
  });
}
"""


def page_html(day: Day, stats: dict, media: Media | None, repository: str | None) -> str:
    metrics = [(stats["commands"], "Comandos aplicados"), (stats["players"], "Jogadores"),
               (stats["frames_held"], "Frames pressionados"), (stats["captures"], "Capturas")]
    strip = "".join(f'<div class="metric"><strong>{v}</strong><span>{label}</span></div>' for v, label in metrics)
    leaderboard = stats["leaderboard"]
    top = leaderboard[0]["commands"] if leaderboard else 1
    def rank_items(entries):
        return "".join(f'<li><div class="rank-row"><span>@{escape(e["player"])}</span><strong>{e["commands"]}</strong></div>'
                       f'<div class="rank-track" aria-hidden="true"><i style="width:{100*e["commands"]/top:.2f}%"></i></div></li>'
                       for e in entries)
    ranking = f'<ol class="rank">{rank_items(leaderboard[:5])}</ol>'
    if len(leaderboard) > 5:
        ranking += f'<details class="more-rank"><summary>Ver os demais jogadores ({len(leaderboard)-5})</summary><ol start="6" class="rank">{rank_items(leaderboard[5:])}</ol></details>'
    if not leaderboard:
        ranking = '<p class="empty">Nenhum participante neste dia.</p>'
    if media:
        coverage = "1 captura cobre" if media.count == 1 else f"{media.count} capturas cobrem"
        command_word = "comando" if stats["commands"] == 1 else "comandos"
        action = (f'<button class="act" id="play" type="button" aria-pressed="false" data-gif="{data_uri(media.gif, "gif")}">Reproduzir</button>'
                  if media.count > 1 else "")
        gallery = (f'<div class="head"><h2>Replay do dia</h2>{action}</div>'
                   f'<img class="preview" id="replay" alt="Primeira captura do recap, com jogador, botão e duração" src="{data_uri(media.poster, "png")}">'
                   f'<figcaption class="caption">{coverage} {stats["commands_with_capture"]} de {stats["commands"]} {command_word}. '
                   'Cada quadro mostra a imagem disponível após o comando indicado.</figcaption>')
    else:
        gallery = '<div class="head"><h2>Replay do dia</h2></div><p class="blank">Nenhuma captura foi associada a este dia. Os comandos registrados aparecem na linha do tempo.</p>'
    opts = ['<option value="">Todos os jogadores</option>']
    for item in sorted(leaderboard, key=lambda k:k["player"].casefold()):
        name = escape(item["player"], quote=True)
        opts.append(f'<option value="{name}">@{name}</option>')
    select = '<label>Jogador <select id="player-filter">'+''.join(opts)+'</select></label>' if day.events else ""
    rows = table_html(day, media, repository)
    grid = (f'<div class="scroll"><table><thead><tr><th>Hora local</th><th>Jogador</th><th>Botão</th><th>Frames</th><th>Issue</th><th>Imagem</th></tr></thead><tbody>{rows}</tbody></table></div>'
            if rows else '<p class="empty">Nenhum comando aplicado no dia selecionado.</p>')
    ignored_label = "1 registro com outro status no dia." if day.ignored == 1 else f"{day.ignored} registros com outro status no dia."
    zone = escape(day.zone.key)
    source = f' · <a href="https://github.com/{escape(repository)}/issues" target="_blank" rel="noopener">Issues do projeto</a>' if repository else ""
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="color-scheme" content="dark"><title>GitBoy · Recap de {day.day:%d/%m/%Y}</title><style>{STYLE}</style></head><body>'
            '<header><div><span class="cross" aria-hidden="true">+</span><span class="brand">GitBoy</span><span class="protocol">Pokémon FireRed coletivo</span></div></header>'
            f'<main><section class="intro"><p class="kicker">Recap diário</p><h1>{local_date(day.day)}</h1><p class="muted">Comandos da comunidade no fuso {zone}.</p></section>'
            f'<section class="metrics" aria-label="Totais do dia">{strip}</section>'
            f'<div class="columns"><figure class="box">{gallery}</figure><section class="box"><div class="head"><h2>Quem jogou</h2></div>{ranking}</section></div>'
            f'<section class="box timeline"><div class="table-head"><h2>Linha do tempo</h2>{select}</div>'
            f'<p class="hint" role="status"><span id="shown">{len(day.events)}</span> de {len(day.events)} comandos aplicados. {ignored_label}</p>{grid}</section></main>'
            f'<footer>GitBoy · Recap local de {day.day:%d/%m/%Y}{source}</footer><script>{ACTIONS}</script></body></html>')


if __name__ == "__main__":
    sys.exit(main())
