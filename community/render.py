"""Frame presentation around untouched, nearest-neighbor emulator pixels."""
import hashlib
import html
import json
from pathlib import Path
from urllib.parse import urlencode
from PIL import Image, ImageDraw, ImageFont

BEGIN, END = '<!-- COMMUNITY-GBA:START -->', '<!-- COMMUNITY-GBA:END -->'

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
    action = ('Preparação do treinador' if last and last['button']=='Trainer setup' else
              f"{last['button']} · {last['duration']} frames" if last else 'Aguardando o primeiro comando')
    control_art(assets)
    controls={}
    prefix = '[gba]' if branch=='main' else '[gba-test]'
    default_frames = 12 if mode=='firered' else 60
    for button in ('UP','DOWN','LEFT','RIGHT','A','B','L','R','START','SELECT'):
        url = f'https://github.com/{repository}/issues/new?' + urlencode(dict(title=f'{prefix} {button} {default_frames}',body=f'Confirme em Create / Submit new issue para enviar {button} ao jogo compartilhado. Aguarde o processamento e atualize o perfil.'))
        source=f'https://raw.githubusercontent.com/{repository}/{branch}/assets/community/control-{button.lower()}-v1.png'
        width=120 if button in ('L','R') else 96 if button in ('START','SELECT') else 48
        controls[button]=f'<a href="{html.escape(url,quote=True)}" title="Enviar {button}"><img src="{source}" alt="{button}" width="{width}" /></a>'
    def spacer(width):
        return f'<img src="https://raw.githubusercontent.com/{repository}/{branch}/assets/community/control-space-v1.png" alt="" width="{width}" height="1" />'
    center=f'<img src="https://raw.githubusercontent.com/{repository}/{branch}/assets/community/control-center-v1.png" alt="Centro do direcional" width="48" />'
    pad=f'''<p>{controls['L']}{spacer(176)}{controls['R']}</p>
<p>{spacer(48)}{controls['UP']}{spacer(248)}{controls['A']}{spacer(24)}<br />
{controls['LEFT']}{center}{controls['RIGHT']}{spacer(152)}{controls['B']}{spacer(72)}<br />
{spacer(48)}{controls['DOWN']}{spacer(320)}</p>
<p>{controls['SELECT']}{spacer(24)}{controls['START']}</p>'''
    title = 'POKÉMON FIRERED' if mode=='firered' else 'GBA PIXEL ADVENTURE'
    description = ('Uma partida real de **Pokémon FireRed**, jogada em comunidade pelo GitHub. '
                   'Todo mundo controla o **mesmo personagem e o mesmo save**: cada comando continua a aventura de onde o último visitante parou.'
                   if mode=='firered' else 'Uma aventura homebrew de GBA, jogada em comunidade com um único save compartilhado.')
    preview = '\nDevelopment preview: test turns run when the maintainer pushes engine changes. Automatic visitor turns activate after merging the PR.\n' if branch!='main' else ''
    image_url=f'https://raw.githubusercontent.com/{repository}/{branch}/assets/community/{name}'
    block=f'''{BEGIN}
<div align="center">

## {title}
**UMA AVENTURA · UM SAVE · TODA A COMUNIDADE**

{description}

A tela abaixo é a última imagem do jogo. Ela muda quando um comando é processado; atualize a página para ver o resultado.

<img src="{image_url}" alt="Actual mGBA output in a graphite GBA frame" width="660" />

{preview}

**CONTROLES — clique no botão que quer enviar**

{pad}

| ÚLTIMA AÇÃO | ÚLTIMO JOGADOR | COMANDOS DA COMUNIDADE |
| :---: | :---: | :---: |
| {action} | {player} | {session.data['total']} |

</div>

### Como jogar

1. **Escolha um botão acima.** Ele abre uma Issue com o comando já preenchido.
2. Entre na sua conta do GitHub e clique em **Create / Submit new issue** para confirmar o envio. Só abrir a Issue não envia o comando.
3. **Aguarde o processamento.** A automação executa o botão, salva o progresso e fecha a Issue. Isso pode levar alguns minutos.
4. **Volte ao perfil e atualize a página.** Veja a nova tela antes de enviar o próximo comando.

Não precisa instalar um emulador nem baixar a ROM. O jogo roda na automação, e o README mostra seu resultado.
**Espere pelo menos 30 segundos entre comandos da mesma conta.** Outros visitantes também podem jogar e mudar a tela.

### O que cada botão faz no FireRed

| Botão | Função |
| :--- | :--- |
| **↑ UP · ↓ DOWN · ← LEFT · → RIGHT** | Mover o personagem e navegar pelas opções dos menus. |
| **A** | Confirmar, conversar, examinar objetos e avançar diálogos. |
| **B** | Cancelar, voltar ou fechar menus; também permite correr depois de obter os Running Shoes. |
| **START** | Abrir o menu principal quando disponível: Pokémon, Bag, Save e opções. |
| **SELECT** | Usar um item registrado; em algumas telas, alternar opções, como o teclado do nome. |
| **L / R** | Abrir a ajuda do FireRed na configuração padrão; o efeito pode mudar conforme a opção de botões do jogo. |

Cada clique segura o botão por **{default_frames} frames** (cerca de {default_frames/60:g} segundo). Para um movimento mais longo,
edite o número no título da Issue: por exemplo, `{prefix} RIGHT 60`. São aceitos **1 a 120 frames** por comando.
Alguns diálogos precisam de mais de um comando **A**. O progresso fica salvo automaticamente entre comandos.

[Fila de comandos](https://github.com/{repository}/issues?q=is%3Aissue+is%3Aopen+%5Bgba%5D) · [Tela original](assets/community/screen.png) · [Como o projeto funciona](docs/community-gba.md)

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
