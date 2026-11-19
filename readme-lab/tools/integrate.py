#!/usr/bin/env python3
"""Prepare the lab block or integrate it into a local profile README."""

import argparse
import difflib
import re
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
START = '<!-- SHIINA-LAB:START -->'
END = '<!-- SHIINA-LAB:END -->'
PROTECTED = ('COMMUNITY-GBA', 'BAD-TAKE', 'CURRENTLY-BUILDING')


def profile_block():
    sample = (LAB / 'README.md').read_text(encoding='utf-8').strip()
    # The exact same chapter names keep their section anchors in the profile.
    sample = re.sub(r'(?m)^(#{1,2}) ', r'\1# ', sample)
    sample = re.sub(r'\]\((assets/|data/)', r'](readme-lab/\1', sample)
    return '\n'.join((START, sample, END))


def locate_section(text, start, end):
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError(f'Expected one complete block between {start} and {end}')
    left = text.index(start)
    right = text.index(end) + len(end)
    if right - len(end) < left:
        raise ValueError(f'Closing marker precedes {start}')
    return left, right


def integrate(raw):
    original = raw.decode('utf-8')
    newline = '\r\n' if '\r\n' in original else '\n'
    protected = [locate_section(original, f'<!-- {name}:START -->', f'<!-- {name}:END -->') for name in PROTECTED]
    sorted_blocks = sorted(protected)
    if any(beg < prev_end for (_, prev_end), (beg, _) in zip(sorted_blocks, sorted_blocks[1:])):
        raise ValueError('Existing managed sections overlap')
    block = profile_block().replace('\n', newline)
    if START in original or END in original:
        left, right = locate_section(original, START, END)
        if any(left < end and start < right for start, end in protected):
            raise ValueError('The lab overlaps an existing managed section')
        merged = original[:left] + block + original[right:]
    else:
        # Preserve every byte of the original, including trailing blank lines.
        gap = '' if original.endswith(newline * 2) else newline if original.endswith(newline) else newline*2
        merged = original + gap + '---' + newline*2 + block + newline
    return merged.encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('readme', nargs='?', type=Path, help='Local README.md of the actual profile')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--block', action='store_true', help='Print the ready-to-append Markdown block')
    mode.add_argument('--write', action='store_true', help='Update the supplied local README')
    args = parser.parse_args()
    if args.block:
        print(profile_block())
        return
    if args.readme is None:
        parser.error('Choose --block or provide the path to the profile README')
    if args.readme.resolve() == LAB / 'README.md':
        parser.error('Supply the profile root README, which contains the existing sections')
    try:
        current = args.readme.read_bytes()
        updated = integrate(current)
    except (OSError, ValueError) as err:
        sys.exit(str(err))
    if updated == current:
        print('The local profile already contains this version of the lab.')
        return
    if args.write:
        # Refuse a stale update if the file changed during preview preparation.
        if args.readme.read_bytes() != current:
            sys.exit('The local profile changed while preparing the update. Re-run on the latest content.')
        args.readme.write_bytes(updated)
        print(f'Integrated the lab in {args.readme}.')
    else:
        report = difflib.unified_diff(current.decode().splitlines(keepends=True), updated.decode().splitlines(keepends=True), fromfile=str(args.readme), tofile=str(args.readme)+' + lab')
        sys.stdout.writelines(report)


if __name__ == '__main__':
    main()
