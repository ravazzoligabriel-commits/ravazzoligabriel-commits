# GitBoy daily recap

Turn one local day of accepted community commands into a portable HTML timeline. The report shows the player, GBA button, hold length, local timestamp and issue number. Point the tool at a folder of matching screenshots to add a downloadable GIF and an expandable capture for each covered command.

The generated interface is in Brazilian Portuguese. The tool runs offline and writes its reports to the directory you choose.

## Generate a report

Run from the root of this repository with Python 3.10 or newer. The profile already includes the command history in `assets/community/history.json`.

```sh
python tools/gitboy-recap/recap.py --events assets/community/history.json --date 2026-11-03 --timezone America/Sao_Paulo --out local-recaps
```

Open `local-recaps/recap-2026-11-03.html` in a browser. It includes a player filter, a leaderboard and a chronological command table. The adjacent JSON contains machine-readable totals. Omit `--date` to use today's date in the selected time zone. The default zone is `America/Sao_Paulo`.

### Include screenshots

Name each local capture after its issue, for example `123.png`. For several images from one command, use `123-001.png`, `123-002.png` and so on. PNG, JPEG and WebP are supported. Match captures to confirmed applied commands before placing them in the directory.

```sh
python -m pip install -r tools/gitboy-recap/requirements.txt
python tools/gitboy-recap/recap.py --events assets/community/history.json --date 2026-11-03 --frames-dir my-screenshots --out local-recaps --repo ravazzoligabriel-commits/ravazzoligabriel-commits
```

The HTML embeds the GIF and the available images. The same GIF is also saved as a separate file. Commands with a missing screenshot still appear in the timeline. Supply `--hold-ms` to adjust the viewing time per image, which defaults to 900 ms. A command's GBA frame count describes how long its button was held. The optional `--repo` argument enables clickable issue numbers.

### Input and day boundaries

The native input is a JSON list of event objects. An object containing an `events` list is also accepted. This synthetic record illustrates the format.

```json
[
  {
    "issue": 123,
    "created": "2026-11-03T15:20:00Z",
    "player": "example-player",
    "button": "LEFT",
    "duration": 12,
    "status": "applied"
  }
]
```

The tool counts records with `status` equal to `applied`. It converts the issue creation timestamp to the selected time zone before selecting the day. Identical accepted entries for the same issue count once. Conflicting entries produce an error. Hold duration must be an integer from 1 to 120. The plain HTML and JSON paths use the Python standard library. Optional image support uses Pillow. Systems without the IANA zone database can install `tzdata`.

## Run the tests

```sh
python -m unittest discover -s tools/gitboy-recap -v
```

The suite checks local midnight, ordering, duplicates, validation, HTML escaping, empty days, report replacement and recovery after a failed write. With Pillow installed, it also generates and checks a multiframe GIF using tiny drawn images from the test itself.
