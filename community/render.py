"""Frame presentation around untouched, nearest-neighbor emulator pixels."""
import hashlib
import html
import json
from pathlib import Path
from urllib.parse import urlencode
from PIL import Image, ImageDraw, ImageFont

BEGIN, END = '<!-- COMMUNITY-GBA:START -->', '<!-- COMMUNITY-GBA:END -->'

def render(root, emulator, session, repository, branch, mode='homebrew'):
    root = Path(root)
    assets = root/'assets'/'community'
    assets.mkdir(parents=True,exist_ok=True)
    raw = assets/'screen.png'
    emulator.captureScreenshot(raw)
    frame = Image.new('RGB',(880,660),'#191c20')
    draw = ImageDraw.Draw(frame)
    font = ImageFont.load_default(size=19)
    small = ImageFont.load_default(size=14)
    draw.rounded_rectangle((18,18,862,642),radius=42,fill='#292d32',outline='#45494e',width=2)
    draw.rounded_rectangle((58,58,822,590),radius=18,fill='#111316')
    draw.text((80,31),'COMMUNITY ADVENTURE',font=small,fill='#bd666c')
    draw.text((702,31),'mGBA / GBA',font=small,fill='#a2a8ad')
    frame.paste(emulator.image.resize((720,480),Image.Resampling.NEAREST),(80,80))
    draw.text((314,605),'GAME BOY ADVANCE',font=font,fill='#bbc0c5')
    screen_hash = hashlib.sha256(raw.read_bytes()).hexdigest()
    name = f'console-{screen_hash[:16]}.png'
    frame.save(assets/name)
    # A changing filename gives Camo/CDN a new URL. Retain current and previous.
    existing = sorted(assets.glob('console-*.png'),key=lambda p:p.stat().st_mtime,reverse=True)
    for old in existing[2:]:
        old.unlink()
    last = session.data['last']
    player = html.escape(last['player']) if last else '—'
    action = f"{last['button']} · {last['duration']} frames" if last else 'Boot / waiting for first command'
    controls=[]
    for button in ('UP','DOWN','LEFT','RIGHT','A','B','L','R','START','SELECT'):
        url = f'https://github.com/{repository}/issues/new?' + urlencode(dict(title=f'[gba] {button} 12',body='Submit this Issue to add one turn to the shared adventure. The title is the command; the body is ignored.'))
        controls.append(f'[{button}]({url})')
    title = 'POKÉMON FIRERED' if mode=='firered' else 'GBA PIXEL ADVENTURE'
    status = 'FireRed · private cartridge installation' if mode=='firered' else 'Open homebrew demo · FireRed cartridge not installed'
    image_url=f'https://raw.githubusercontent.com/{repository}/{branch}/assets/community/{name}'
    block=f'''{BEGIN}
<div align="center">

## {title}
**COMMUNITY ADVENTURE**

<img src="{image_url}" alt="Actual mGBA output in a graphite GBA frame" width="660" />

{status}

{' · '.join(controls[:4])}

{' · '.join(controls[4:])}

| LAST ACTION | CURRENT PLAYER | TOTAL COMMANDS |
| :---: | :---: | :---: |
| {action} | {player} | {session.data['total']} |

</div>

One shared save. Click a button, sign in to GitHub, then **submit the prefilled Issue**.
Each turn holds a button for 12 emulated frames; edit the title for 1–120 frames.
Wait for processing and refresh this page. The image is a snapshot, not live video.
One accepted command per player per 30 seconds. Actions can take minutes.

[Raw emulator pixels](assets/community/screen.png) · [Command queue](https://github.com/{repository}/issues?q=is%3Aissue+is%3Aopen+%5Bgba%5D) · [How it works](docs/community-gba.md)

{END}'''
    readme=root/'README.md'
    text=readme.read_text(encoding='utf-8')
    if BEGIN in text:
        start=text.index(BEGIN); end=text.index(END,start)+len(END)
        text=text[:start]+block+text[end:]
    else:
        text=block+'\n\n---\n\n'+text
    readme.write_text(text,encoding='utf-8')
    public=dict(emulator.getSessionState(),rom_sha256=None,total=session.data['total'],
                last=last,screen_sha256=screen_hash,mode=mode)
    (assets/'status.json').write_text(json.dumps(public,indent=2)+'\n')
    (assets/'history.json').write_text(json.dumps(list(session.data['ledger'].values())[-200:],indent=2)+'\n')
    return public

