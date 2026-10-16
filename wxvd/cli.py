"""wxvd: list captured Channels feeds, download + decrypt, or decrypt a local file."""

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

from .isaac64 import ENC_LEN, keystream

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 MicroMessenger")
CHUNK = 1 << 20


def _load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _safe(name):
    return re.sub(r'[\\/:*?"<>|\s]+', "_", name).strip("_")[:80] or "video"


def _decrypt_stream(src, dst, seed, enc_len):
    """Copy src -> dst, XORing the first enc_len bytes with the keystream."""
    ks = keystream(seed, enc_len)
    pos = 0
    while chunk := src.read(CHUNK):
        if pos < enc_len:
            n = min(len(chunk), enc_len - pos)
            head = bytes(a ^ b for a, b in zip(chunk[:n], ks[pos:pos + n]))
            chunk = head + chunk[n:]
        dst.write(chunk)
        pos += len(chunk)
    return pos


def cmd_list(args):
    for i, r in enumerate(_load(args.captures)):
        print(f"{i:3d}  {r['id']}  key={r['decode_key']:<12} {r.get('author') or ''} | {r['title'][:50]}")


def cmd_download(args):
    recs = _load(args.captures)
    picked = [r for i, r in enumerate(recs) if args.which in (str(i), r["id"])]
    if not picked:
        sys.exit(f"no capture matches {args.which!r} (use index or feed id from `wxvd list`)")
    r = picked[-1]  # latest capture wins: url and key rotate together
    url = r["url"] + (f"&X-snsvideoflag={args.spec}" if args.spec else "")
    out = Path(args.out or f"{_safe(r['title'] or r['id'])}_{r['id']}.mp4")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req) as resp, out.open("wb") as f:
        n = _decrypt_stream(resp, f, int(r["decode_key"]), args.enc_len)
    print(f"wrote {out} ({n} bytes)")


def cmd_decrypt(args):
    with open(args.input, "rb") as src, open(args.output, "wb") as dst:
        n = _decrypt_stream(src, dst, int(args.key), args.enc_len)
    print(f"wrote {args.output} ({n} bytes)")


def main(argv=None):
    p = argparse.ArgumentParser(prog="wxvd")
    p.add_argument("--captures", default="captures.jsonl")
    p.add_argument("--enc-len", type=int, default=ENC_LEN)
    sub = p.add_subparsers(required=True)

    s = sub.add_parser("list", help="show captured feeds")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("download", help="download + decrypt a captured feed")
    s.add_argument("which", help="index or feed id from `wxvd list`")
    s.add_argument("-o", "--out")
    s.add_argument("--spec", help="quality fileFormat, e.g. xWT111 (default: server default)")
    s.set_defaults(func=cmd_download)

    s = sub.add_parser("decrypt", help="decrypt an already-downloaded encrypted file")
    s.add_argument("input")
    s.add_argument("output")
    s.add_argument("--key", required=True, help="decodeKey")
    s.set_defaults(func=cmd_decrypt)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
