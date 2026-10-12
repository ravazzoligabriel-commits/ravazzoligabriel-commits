"""Frame presentation around untouched, nearest-neighbor emulator pixels."""
import hashlib
import html
import json
from pathlib import Path
from urllib.parse import urlencode, quote
from PIL import Image, ImageDraw, ImageFont

BEGIN, END = '<!-- COMMUNITY-GBA:START -->', '<!-- COMMUNITY-GBA:END -->'

def leaderboard(ledger):
    """Rank the complete durable ledger, including turns older than public history."""
    players={}
    for record in ledger.values():
        if record['status']!='applied':
            continue
        login=record['player']
        identity=login.lower()
        if identity not in players:
            players[identity]=dict(player=login,commands=0,profile=f'https://github.com/{quote(login,safe="-")}')
        players[identity]['commands']+=1
    ranked=sorted(players.values(),key=lambda player:(-player['commands'],player['player'].lower()))[:10]
    return [dict(rank=rank,**player) for rank,player in enumerate(ranked,1)]

def control_art(assets):
    """Small transparent linked images work in GitHub's sanitized README HTML."""
    for button in ('UP','DOWN','LEFT','RIGHT','A','B','L','R','START','SELECT','CENTER','SPACE'):
        size=(120,44) if button in ('L','R') else (96,40) if button in ('START','SELECT') else (48,48)
        art=Image.new('RGBA',size,(0,0,0,0)); d=ImageDraw.Draw(art)
        if button!='SPACE':
            rect=(2,2,size[0]-3,size[1]-3)
            color='#7770a9' if button in ('A','B') else '#353b45'
            if button in ('A','B'):
                d.ellipse((2,5,45,47),fill='#171a20')
                d.ellipse(rect,fill=color,outline='#b3aad7',width=2)
            else:
                d.rounded_rectangle((2,5,size[0]-3,size[1]-1),radius=9,fill='#171a20')
                d.rounded_rectangle(rect,radius=9,fill=color,outline='#707987',width=2)
            arrows={'UP':[(24,12),(14,25),(34,25)],'DOWN':[(24,32),(14,19),(34,19)],
                    'LEFT':[(12,24),(25,14),(25,34)],'RIGHT':[(34,24),(21,14),(21,34)]}
            if button in arrows:
                d.polygon(arrows[button],fill='#e1e5ed')
            elif button=='CENTER':
                d.ellipse((16,16,32,32),fill='#262b33',outline='#525b68')
            else:
                font=ImageFont.load_default(size=24 if button in ('A','B') else 16)
                d.text((size[0]//2,size[1]//2),button,font=font,anchor='mm',fill='#f5f3ff')
        art.save(assets/f'control-{button.lower()}-v1.png')

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
    existing = sorted((p for p in assets.glob('console-*.png') if p.name!=name),
                      key=lambda p:(p.stat().st_mtime,p.name),reverse=True)
    for old in existing[1:]:
        old.unlink()
    last = session.data['last']
    player = html.escape(last['player']) if last else '—'
    action = ('Trainer setup' if last and last['button']=='Trainer setup' else
              f"{last['button']} · {last['duration']} frames" if last else 'Waiting for the first command')
    control_art(assets)
    controls={}
    prefix = '[gba]' if branch=='main' else '[gba-test]'
    default_frames = 12 if mode=='firered' else 60
    for button in ('UP','DOWN','LEFT','RIGHT','A','B','L','R','START','SELECT'):
        body=f'''## Send a FireRed command

**Button: {button} · Hold: {default_frames} frames**

### 1. Send the command
Click the green **Create / Submit new issue** button below. Opening this form alone does not send a command.

### 2. Close the Issue
On the Issue page that opens, click **Close issue** (or **Close with comment**). Closing it also triggers the game automation. Your command is processed once, even if both submission and closing trigger runs. If it is already closed, continue to the next step.

### 3. Return to the game
[Back to the profile — see the updated game](https://github.com/{repository.split('/')[0]}#pok%C3%A9mon-firered)

Refresh the profile after processing to see the change. Closing triggers processing immediately, but the workflow and image update may take a few minutes.

**No pull request, code changes or approval from the owner are needed.** Just submit this Issue.

Wait at least 30 seconds between commands from the same account. The command is read from the title; you can change its duration to 1–120 frames. Rejected commands may also be closed without changing the game.
'''
        url = f'https://github.com/{repository}/issues/new?' + urlencode(dict(title=f'{prefix} {button} {default_frames}',body=body))
        source=f'https://raw.githubusercontent.com/{repository}/{branch}/assets/community/control-{button.lower()}-v1.png'
        width=120 if button in ('L','R') else 96 if button in ('START','SELECT') else 48
        controls[button]=f'<a href="{html.escape(url,quote=True)}" title="Send {button}"><img src="{source}" alt="{button}" width="{width}" /></a>'
    def spacer(width):
        return f'<img src="https://raw.githubusercontent.com/{repository}/{branch}/assets/community/control-space-v1.png" alt="" width="{width}" height="1" />'
    center=f'<img src="https://raw.githubusercontent.com/{repository}/{branch}/assets/community/control-center-v1.png" alt="D-pad center" width="48" />'
    pad=f'''<p>{controls['L']}{spacer(176)}{controls['R']}</p>
<p>{spacer(48)}{controls['UP']}{spacer(248)}{controls['A']}{spacer(24)}<br />
{controls['LEFT']}{center}{controls['RIGHT']}{spacer(152)}{controls['B']}{spacer(72)}<br />
{spacer(48)}{controls['DOWN']}{spacer(320)}</p>
<p>{controls['SELECT']}{spacer(24)}{controls['START']}</p>'''
    title = 'POKÉMON FIRERED' if mode=='firered' else 'GBA PIXEL ADVENTURE'
    description = ('A real game of **Pokémon FireRed**, played together through GitHub. '
                   'Everyone controls the **same character and the same save**: each command continues the adventure where the last visitor left off.'
                   if mode=='firered' else 'A community GBA homebrew adventure with one shared save.')
    preview = '\nDevelopment preview: test turns run when the maintainer pushes engine changes. Automatic visitor turns activate after merging the PR.\n' if branch!='main' else ''
    image_url=f'https://raw.githubusercontent.com/{repository}/{branch}/assets/community/{name}'
    opening=(f'<img src="https://raw.githubusercontent.com/{repository}/{branch}/assets/community/header-firered-v1.svg" '
             'alt="Play FireRed together — a real GBA adventure on GitHub. One shared save. Everyone takes a turn." width="660" />'
             if mode=='firered' else description)
    leaders=leaderboard(session.data['ledger'])
    medals={1:'🥇',2:'🥈',3:'🥉'}
    ranking_rows='\n'.join(f"| {medals.get(entry['rank'],entry['rank'])} | [@{html.escape(entry['player'])}]({entry['profile']}) | **{entry['commands']}** |" for entry in leaders)
    if not ranking_rows:
        ranking_rows='| — | Be the first player! | 0 |'
    block=f'''{BEGIN}
<div align="center">

## {title}

{opening}

<img src="{image_url}" alt="Actual mGBA output in a graphite GBA frame" width="660" />

<sub>Latest game snapshot · Send a command, wait for processing, then refresh.</sub>

{preview}

**YOUR TURN — choose a button**

{pad}

| LAST ACTION | LAST PLAYER | COMMUNITY COMMANDS |
| :---: | :---: | :---: |
| {action} | {player} | {session.data['total']} |

[How to play](#how-to-play) · [Leaderboard](#global-leaderboard--top-10) · [About me](#gabriel-ravazzoli)

</div>

---

### Global leaderboard · Top 10

**Every turn counts.** The most active players in this shared adventure.

| Rank | Player | Accepted commands |
| :---: | :--- | ---: |
{ranking_rows}

<sub>All-time accepted commands · Updates automatically · Alphabetical tie-break · Up to 10 players</sub>

### How to play

{description}

> **Click a control → submit the prefilled Issue → click Close issue → return here and refresh.**
> One accepted command per account every 30 seconds. Processing may take a few minutes.

**No pull request needed.** Click **Create**, then **Close issue** on the next page. If it is already closed, just return here. Each command is processed only once.

<details>
<summary><strong>First time here? Open the step-by-step guide</strong></summary>

1. **Choose a button above.** It opens an Issue with the command already filled in.
2. Sign in to GitHub and click **Create / Submit new issue** to send it. Opening the Issue form alone does not send a command.
3. **Click Close issue** (or **Close with comment**) on the Issue page. Closing also triggers processing; if the automation already closed it, continue.
4. **[Return to the profile](https://github.com/{repository.split('/')[0]}#pok%C3%A9mon-firered) and refresh the page.** Processing may take a few minutes. Check the new screen before sending your next command.

You do not need to install an emulator or download the ROM. The game runs in the automation, and the README displays its output.
**Wait at least 30 seconds between commands from the same account.** Other visitors can also play and change the screen.

</details>

<details>
<summary><strong>Button guide &amp; command duration</strong></summary>

### What each button does in FireRed

| Button | Function |
| :--- | :--- |
| **↑ UP · ↓ DOWN · ← LEFT · → RIGHT** | Move the character and navigate menu options. |
| **A** | Confirm, talk, examine objects and advance dialogue. |
| **B** | Cancel, go back or close menus; also lets you run after obtaining the Running Shoes. |
| **START** | Open the main menu when available: Pokémon, Bag, Save and options. |
| **SELECT** | Use a registered item; on some screens, switch options, such as the name-entry keyboard. |
| **L / R** | Open FireRed's help with the default configuration; their behavior can change with the game's button settings. |

Each click holds the button for **{default_frames} frames** (about {default_frames/60:g} seconds). For a longer movement,
edit the number in the Issue title: for example, `{prefix} RIGHT 60`. Commands accept **1 to 120 frames**.
Some dialogues need more than one **A** command. Progress is saved automatically between commands.

</details>

[Command queue](https://github.com/{repository}/issues?q=is%3Aissue+is%3Aopen+%5Bgba%5D) · [Raw game screen](assets/community/screen.png) · [How the project works](docs/community-gba.md)

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
    (assets/'leaderboard.json').write_text(json.dumps(leaders,indent=2)+'\n')
    return public
