#!/usr/bin/env python3
"""Render the five standalone SVG plates using only the Python standard library."""

import argparse
import hashlib
import json
import math
import random
import re
import sys
from datetime import date
from html import escape
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
ASSETS = LAB / 'assets'
JOURNAL = LAB / 'data' / 'saves.json'
MILESTONES = (1, 10, 25, 50, 100)
SERIF = "'Instrument Serif', Georgia, 'DejaVu Serif', serif"
SANS = "'Inter', 'DejaVu Sans', Arial, sans-serif"
MONO = "'IBM Plex Mono', 'DejaVu Sans Mono', Consolas, monospace"


def label(x, y, words, size, fill, family=SANS, weight=400, anchor='start', tracking=0, italic=False):
    style = ' font-style="italic"' if italic else ''
    return (f'<text x="{x:g}" y="{y:g}" fill="{fill}" font-family="{family}" font-size="{size:g}" '
            f'font-weight="{weight}" text-anchor="{anchor}" letter-spacing="{tracking:g}"{style}>{escape(str(words))}</text>')


def group(content, transform=''):
    return f'<g transform="{transform}">{content}</g>' if transform else f'<g>{content}</g>'


def signature(x, y, color, ink):
    mark = (f'<circle r="15" fill="none" stroke="{color}" stroke-width="1.2"/>'
            f'<path d="M-11,5 Q-5,-8 7,-6 Q3,4 -4,6 Q-1,-1 5,-5 Q-4,-1 -9,7 Z" fill="{color}"/>'
            f'<path d="M4,-10 Q9,-12 10,-9 Q8,-5 5,-4 Q7,-7 7,-8Z" fill="{color}"/>')
    return group(mark, f'translate({x},{y})') + label(x+26, y+5, 'SHIINA', 14, ink, MONO, 700, tracking=2.4)


def svg(name, description, height, drawing, definitions=''):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="{height}" '
            f'viewBox="0 0 1120 {height}" role="img" aria-labelledby="title desc">\n'
            f'  <title id="title">{escape(name)}</title>\n  <desc id="desc">{escape(description)}</desc>\n'
            f'  <defs>{definitions}</defs>\n  {drawing}\n</svg>\n')


def line(x1, y1, x2, y2, stroke, width=1, extra=''):
    return f'<path d="M{x1:g} {y1:g}L{x2:g} {y2:g}" fill="none" stroke="{stroke}" stroke-width="{width:g}" {extra}/>'


def circle(x, y, radius, fill, extra=''):
    return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:g}" fill="{fill}" {extra}/>'


def rect(x, y, width, height, fill, extra=''):
    return f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" fill="{fill}" {extra}/>'


def stars(width=690, height=480, count=125):
    rng = random.Random(136)
    dots = []
    for _ in range(count):
        x, y = rng.uniform(402, 402 + width), rng.uniform(21, height-20)
        radius = rng.choice((.55, .7, 1, 1.3))
        dots.append(circle(x, y, radius, '#a4d3d3', f'opacity="{rng.uniform(.15,.58):.2f}"'))
    return ''.join(dots)


# The order is physical. The circular radii, phases and body sizes are illustrative.
PLANETS = [
    ('Mercury', 34, -79, 3.6, '#d6c0ac', '#6e655b'),
    ('Venus', 57, 135, 5.8, '#edd69d', '#986c43'),
    ('Earth', 81, 18, 7.1, '#93dad9', '#2e677d'),
    ('Mars', 105, 220, 5.3, '#e8a58d', '#a45649'),
    ('Jupiter', 138, -48, 14.5, '#eac7a0', '#925f50'),
    ('Saturn', 173, 150, 11.9, '#f0d39e', '#a67557'),
    ('Uranus', 211, 36, 8.9, '#a8e2de', '#579393'),
    ('Neptune', 247, -152, 8.2, '#a3b6ed', '#525e9b'),
]


def orbit_point(radius, phase, tilt, cx, cy):
    phase = math.radians(phase)
    camera = math.radians(-11)
    x = radius * math.cos(phase)
    y = radius * math.sin(phase) * math.cos(math.radians(tilt))
    return cx + x*math.cos(camera) - y*math.sin(camera), cy + x*math.sin(camera) + y*math.cos(camera)


def orb_image(tilt, height):
    cx, cy = 759, height/2 + 1
    ink, muted, green = '#edf5ea', '#b6c6c1', '#97d5c0'
    definitions = ('<linearGradient id="night" x2="1" y2="1" gradientUnits="objectBoundingBox">'
                   '<stop stop-color="#162327"/><stop offset=".55" stop-color="#101f28"/>'
                   '<stop offset="1" stop-color="#101922"/></linearGradient>'
                   '<radialGradient id="halo"><stop stop-color="#efc88f" stop-opacity=".35"/>'
                   '<stop offset=".25" stop-color="#eebd82" stop-opacity=".15"/>'
                   '<stop offset="1" stop-color="#e2c087" stop-opacity="0"/></radialGradient>'
                   '<radialGradient id="sun" cx="35%" cy="30%" r="76%">'
                   '<stop stop-color="#fff9d5"/><stop offset=".55" stop-color="#f3d291"/>'
                   '<stop offset="1" stop-color="#d49c64"/></radialGradient>')
    for index, (_, _, _, _, light, shade) in enumerate(PLANETS):
        definitions += (f'<radialGradient id="p{index}" cx="26%" cy="23%" r="90%">'
                        f'<stop stop-color="{light}"/><stop offset=".55" stop-color="{light}"/>'
                        f'<stop offset="1" stop-color="{shade}"/></radialGradient>')
    draw = [rect(0,0,1120,height,'url(#night)'), stars(height=height),
            rect(14,14,1092,height-28,'none','rx="4" stroke="#466260" stroke-opacity=".48"'),
            signature(54,51,green,ink), label(169,56,'/  OBSERVATORY',13,muted,MONO,tracking=1.2),
            line(44,83,353,83,'#496563'),
            label(42,171,'Orbit room',55,ink,SERIF),
            label(44,218,'Eight planets in one plane.',19,muted),
            label(44,247,'Follow the rings of Saturn.',19,muted),
            line(45,height-109,233,height-109,'#496563'),
            label(42,height-51,f'{tilt}°',39,'#f4cc99',SERIF),
            label(136,height-58,'FROM OVERHEAD',12,green,MONO,tracking=1.1)]
    axis_start = orbit_point(276,180,tilt,cx,cy)
    axis_end = orbit_point(276,0,tilt,cx,cy)
    draw.append(line(*axis_start,*axis_end,'#4f726e',.8,'stroke-dasharray="3 6"'))
    for index, (_, radius, _, _, _, _) in enumerate(PLANETS):
        vertical = radius * math.cos(math.radians(tilt))
        color = '#a5bdb1' if index == 5 else '#698383'
        draw.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{radius}" ry="{vertical:.2f}" transform="rotate(-11 {cx} {cy})" fill="none" stroke="{color}" stroke-width="{1.25 if index==5 else 1}" opacity="{.76 if index==5 else .69}"/>')
    draw.append(circle(cx,cy,62,'url(#halo)'))
    draw.append(circle(cx,cy,12,'url(#sun)'))
    for index,(name, radius, phase, size, light, _) in enumerate(PLANETS):
        px, py = orbit_point(radius,phase,tilt,cx,cy)
        if name == 'Saturn':
            draw.append(f'<ellipse cx="{px:.2f}" cy="{py:.2f}" rx="24" ry="6" transform="rotate(-24 {px:.2f} {py:.2f})" fill="none" stroke="#d7bd97" stroke-width="3"/>')
        draw.append(circle(px,py,size,f'url(#p{index})'))
        if name == 'Saturn':
            draw.append(f'<path d="M-24 0 A24 6 0 0 0 24 0" fill="none" stroke="#edcf9e" stroke-width="2.4" transform="translate({px:.2f} {py:.2f}) rotate(-24)"/>')
            tx, ty = px-37, py+42
            draw += [line(px-11,py+9,tx+17,ty-8,green,.9), line(tx-41,ty-8,tx+17,ty-8,green,.9), label(tx-42,ty+6,'SATURN',10.5,green,MONO,tracking=1)]
        if name == 'Jupiter':
            draw += [f'<clipPath id="js"><circle cx="{px:.2f}" cy="{py:.2f}" r="{size}"/></clipPath>',f'<g clip-path="url(#js)" stroke="#8f6756" stroke-width="2.1" opacity=".72"><path d="M{px-18:.1f} {py-7:.1f}q14 8 34 4 M{px-18:.1f} {py:.1f}q20 7 34 3 M{px-18:.1f} {py+7:.1f}q18 6 34 3" fill="none"/></g>']
    draw += [label(1070,58,'ORTHOGRAPHIC VIEW',11,muted,MONO,anchor='end',tracking=1.2),
             label(1070,height-44,'SCHEMATIC · FIXED PHASES',10.8,muted,MONO,anchor='end',tracking=.9)]
    return svg(f'Shiina’s orbit room at {tilt} degrees', f'Eight idealized circles and the same planets projected at {tilt} degrees from overhead. Geometric study with a highlighted Saturn.',height,''.join(draw),definitions)


def studio():
    h=408
    ink, muted, red = '#2b292a','#5f5954','#9d4237'
    draw = [rect(0,0,1120,h,'#f2eade'),rect(14,14,1092,h-28,'none','rx="4" stroke="#b9ac9b"'),
            signature(54,51,red,ink),label(169,56,'/  PROJECT INDEX',13,muted,MONO,tracking=1.1),
            line(44,82,335,82,'#b7a995'),label(42,175,'Studio',60,ink,SERIF),label(42,238,'shelves',60,ink,SERIF,italic=True),
            label(45,294,'Pick a project by the',19,muted),label(45,323,'thing you want to do.',19,muted)]
    for idx,(x,title,kicker,bg,fg) in enumerate([(376,'BAD TAKE!','PLAY THE BUILD','#803e3d','#f5dda9'),(609,'Realorant','SEE THE RENDERER','#254e62','#d0e8dc'),(842,'SIGILO','WATCH THE RITUAL','#443346','#e6c290')]):
        y,w,height=56,207,237
        draw += [rect(x,y,w,height,bg),rect(x+9,y+9,w-18,height-18,'none',f'stroke="{fg}" stroke-opacity=".26"'),
                 label(x,330,title,25,ink,SERIF),label(x,354,kicker,10.5,red,MONO,700,tracking=.85)]
        art=[]
        if idx==0:
            art += ['<path d="M18 164L77 86l38 54 22-24 49 62H18Z" fill="#be705a"/><path d="M21 173l57-71 17 25-16-6-9 6z" fill="#efc18c"/>',
                    '<path d="M44 109l111-31 5 16-111 31z" fill="#f2d5a3"/><path d="M58 107l11-3-4 18-11 3zm28-8l11-3-4 18-11 3zm28-8l11-3-4 18-11 3zm28-8l11-3-4 18-11 3z" fill="#6d3837"/>',
                    '<path d="M48 127h113v54H48z" fill="#563137" stroke="#f2d5a3" stroke-width="2"/><path d="M59 141h91M59 151h57M59 167h34m12 0h46" stroke="#edc797"/>',circle(145,52,13,'#eac393')]
        elif idx==1:
            art += ['<path d="M14 180L86 121V73l-72-30zm179 0l-68-59V73l68-35z" fill="#366d7a"/>',
                    '<path d="M15 197l72-67h38l68 67z" fill="#468796"/><g fill="none" stroke="#b8dbc8" stroke-width="1.1"><path d="M18 185l68-64V70L18 44m169 136l-63-60V69l65-32M17 207l77-76m58 76l-39-76m-33 76l23-77m-73 43h145m-124-17h108m-91-13h76M41 65v90m18-83v62m99-89v106m20-117v135"/></g>',
                    '<path d="M84 122V87l38-1v36" stroke="#e8c88e" stroke-width="2" fill="none"/><path d="M97 107h13m-6-7v13" stroke="#f4d9a5" stroke-width="1.5"/>']
        else:
            art += [circle(104,117,66,'none','stroke="#9a8087" stroke-width="1"'),circle(104,117,54,'none','stroke="#c49383" stroke-width="1" stroke-dasharray="2 5"'),
                    '<path d="M104 32l43 84-43 88-44-87z" stroke="#dcaf83" stroke-width="1.5" fill="none"/><path d="M32 118l72-45 72 45-72 42z" fill="none" stroke="#b68b82"/>',
                    '<path d="M104 67l7 44 27 5-27 8-8 44-7-43-27-9 27-6z" fill="#e6bd90"/><circle cx="104" cy="117" r="9" fill="#874f5f"/><circle cx="104" cy="117" r="3" fill="#fae2a6"/>']
        draw.append(group(''.join(art),f'translate({x},{y})'))
    return svg('Shiina’s studio shelves','Original graphic emblems for a film-set game, a browser renderer and an occult pixel-art roguelite.',h,''.join(draw))


def validate_journal(journal):
    item=journal['community']
    date.fromisoformat(item['as_of'])
    if type(item['accepted_commands']) is not int or item['accepted_commands']<0:
        raise ValueError('accepted_commands must be a nonnegative integer')
    if not re.fullmatch('[0-9a-f]{40}',item['readme_blob']):
        raise ValueError('readme_blob must be the source Git blob SHA')
    games=journal['personal']
    if len(games)!=2:
        raise ValueError('This two-drawer plate requires exactly two personal saves')
    for game in games:
        goals,done=game['goals'],game['done']
        if len(goals)!=3 or len(set(goals))!=3 or not all(isinstance(g,str) and g for g in goals):
            raise ValueError('Provide three distinct named goals per save')
        if done is not None and (not isinstance(done,list) or len(set(done))!=len(done) or not set(done)<=set(goals)):
            raise ValueError('done must be null or a list of distinct goal names from goals')


def save_room(journal):
    item=journal['community']
    total=item['accepted_commands']
    next_goal=next((point for point in MILESTONES if point>total),None)
    h=420
    ink, muted, peach, mint = '#f5eced','#d1bec9','#f8bb9d','#b4dfcd'
    draw = [rect(0,0,1120,h,'#271e2b'),rect(14,14,1092,h-28,'none','rx="4" stroke="#654d61"'),
            signature(54,51,peach,ink),label(169,56,'/  GAME JOURNAL',13,muted,MONO,tracking=1.1),
            line(44,82,342,82,'#70596a'),label(42,169,'Save room',53,ink,SERIF),
            label(44,218,'A shared run and two',19,muted),label(44,247,'personal save files.',19,muted),
            label(45,361,'OBSERVED '+item['as_of'],12,mint,MONO,tracking=1),line(386,43,386,h-41,'#624f61'),
            label(426,74,'POKÉMON FIRERED',13,peach,MONO,700,tracking=1.3),label(424,146,str(total),60,ink,SERIF),
            label(426,169,'accepted commands',15,muted),label(1068,83,'COMMUNITY SAVE',11,muted,MONO,anchor='end',tracking=.95)]
    xx=[623,718,814,910,1008]
    rail_y=152
    draw.append(line(xx[0],rail_y,xx[-1],rail_y,'#73596d',3))
    fraction=0
    for i,(a,b) in enumerate(zip(MILESTONES,MILESTONES[1:])):
        if a<=total<b:
            fraction=xx[i]+(xx[i+1]-xx[i])*(total-a)/(b-a)
            break
    if total>=MILESTONES[-1]: fraction=xx[-1]
    if fraction:
        draw.append(line(xx[0],rail_y,fraction,rail_y,peach,3))
    for x,step in zip(xx,MILESTONES):
        reached=total>=step
        draw += [circle(x,rail_y,7.5,peach if reached else '#271e2b',f'stroke="{peach if reached else muted}" stroke-width="1.8"'),label(x,rail_y+26,str(step),12,ink if reached else muted,MONO,anchor='middle')]
    note=(f'{next_goal-total} more to checkpoint {next_goal}' if next_goal is not None else 'All five community checkpoints reached')
    draw.append(label(1068,203,note,13.5,peach,SANS,anchor='end'))
    draw += [line(426,227,1068,227,'#694f63'),label(426,262,'PERSONAL SAVES',11.7,mint,MONO,700,tracking=1.1)]
    for i,game in enumerate(journal['personal']):
        x=426+327*i
        done=game['done']
        draw += [label(x,307,game['game'],25,ink,SERIF),label(x,347,'—  Unreported' if done is None else f'{len(done)} / {len(game["goals"])} recorded',15,muted)]
        for j,goal in enumerate(game['goals']):
            draw.append(rect(x+j*40,363,33,4,mint if done is not None and goal in done else '#685667'))
    return svg('Shiina’s save room', f'FireRed has {total} accepted community commands as observed on {item["as_of"]}. '+ '; '.join(f'{g["game"]}: '+('unreported' if g['done'] is None else f'{len(g["done"])} of {len(g["goals"])} chosen checkpoints') for g in journal['personal'])+'.',h,''.join(draw))


def refresh_community(profile, as_of):
    raw=profile.read_bytes()
    text=raw.decode('utf-8')
    match=re.search(r'<!-- COMMUNITY-GBA:START -->(.*?)<!-- COMMUNITY-GBA:END -->',text,re.DOTALL)
    if not match:
        raise ValueError('Cannot locate the community block in the supplied profile')
    lines=match.group(1).splitlines()
    for i,row in enumerate(lines[:-2]):
        headers=[col.strip().upper() for col in row.strip().strip('|').split('|')]
        if 'COMMUNITY COMMANDS' not in headers:
            continue
        cells=[col.strip() for col in lines[i+2].strip().strip('|').split('|')]
        value=cells[headers.index('COMMUNITY COMMANDS')].replace('**','').replace(',','')
        if not value.isdecimal():
            raise ValueError('The public table has no accepted numeric total')
        header=b'blob '+str(len(raw)).encode()+b'\0'
        return {'as_of':as_of, 'accepted_commands':int(value), 'readme_blob':hashlib.sha1(header+raw).hexdigest()}
    raise ValueError('No COMMUNITY COMMANDS column found in the public profile')


def journal_markdown(source, journal):
    community = journal['community']
    observed = community['as_of']
    total = community['accepted_commands']
    shared = f'On **{observed}**, the public counter recorded **{total} accepted commands**.'
    rows = ['| Game | Recorded | Chosen checkpoints |', '| --- | --- | --- |']
    for game in journal['personal']:
        goals, done = game['goals'], game['done']
        state = 'Unreported' if done is None else f'{len(done)} / {len(goals)}'
        cells = [f'**{goal}** ✓' if done and goal in done else goal for goal in goals]
        rows.append(f'| {game["game"]} | {state} | {" · ".join(cells)} |')
    for name, replacement in [('SHARED', shared), ('PERSONAL', '\n'.join(rows))]:
        start = f'<!-- SHIINA-{name}-SNAPSHOT:START -->'
        end = f'<!-- SHIINA-{name}-SNAPSHOT:END -->'
        if source.count(start) != 1 or source.count(end) != 1 or source.index(start) > source.index(end):
            raise ValueError(f'Missing or repeated journal markers for {name}')
        left = source.index(start) + len(start)
        right = source.index(end)
        source = source[:left] + '\n' + replacement + '\n' + source[right:]
    return source


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',type=Path,help='A local original profile README containing the public FireRed table')
    parser.add_argument('--as-of',type=date.fromisoformat,help='Date when the supplied profile was observed (YYYY-MM-DD)')
    parser.add_argument('--check',action='store_true',help='Compare the committed plates to a fresh render')
    args=parser.parse_args()
    if bool(args.profile)!=bool(args.as_of):
        parser.error('Use --profile and --as-of together')
    if args.check and args.profile:
        parser.error('--check verifies the current journal; refresh and verify separately')
    journal=json.loads(JOURNAL.read_text(encoding='utf-8'))
    if args.profile:
        journal['community']=refresh_community(args.profile,args.as_of.isoformat())
    validate_journal(journal)
    plates={'orbit-inclined.svg':orb_image(55,422),'orbit-overhead.svg':orb_image(0,600),
            'orbit-edge.svg':orb_image(78,399),'studio.svg':studio(),'save-room.svg':save_room(journal)}
    lab_readme = LAB / 'README.md'
    source = lab_readme.read_text(encoding='utf-8')
    updated = journal_markdown(source,journal)
    if args.check:
        stale=[name for name,content in plates.items() if not (ASSETS/name).exists() or (ASSETS/name).read_text(encoding='utf-8')!=content]
        if source != updated:
            stale.append('README.md journal')
        if stale:
            sys.exit('Regenerate '+', '.join(stale))
        print('All five SVG plates match the journal and renderer.')
        return
    if args.profile:
        JOURNAL.write_text(json.dumps(journal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if source != updated:
        lab_readme.write_text(updated,encoding='utf-8')
    ASSETS.mkdir(exist_ok=True)
    for name,content in plates.items():
        (ASSETS/name).write_text(content,encoding='utf-8')
    print('Rendered five local SVG plates.')


if __name__=='__main__':
    main()
