# wechat-video-downloader (wxvd)

Capture WeChat Channels (视频号) feeds from the desktop client, then download and decrypt the videos.

Channels MP4s have their first 131072 bytes XORed with an Isaac64 keystream seeded by the
feed's `decodeKey` (`objectDesc.media[0].decodeKey`). The video URL is `media.url + media.urlToken`.
Each API response rotates both values, so they must be captured together.

## Layout

- `wxvd/isaac64.py`: Isaac64 keystream and prefix decrypt (port of JohnABC/WechatSphDecrypt `decrypt.go`)
- `wxvd/capture.py`: mitmproxy addon that appends feed records to `captures.jsonl`
- `wxvd/cli.py`: `wxvd list | download | decrypt`
- `tests/`: golden vectors generated from the Go reference
- `docker/`, `docker-compose.yml`: WeChat for Linux + transparent mitmproxy in one container

## Setup

```sh
uv sync --extra capture --group dev
uv run pytest -q
```

## Capture (container, no host changes)

WeChat for Linux, mitmproxy and the capture addon all run in one container
(`docker/`, based on linuxserver/webtop). The MITM CA is trusted only inside the container,
and the 443 → mitmproxy redirect uses iptables in the container's own network namespace.
mitmproxy decrypts only `channels.weixin.qq.com`; all other traffic passes through untouched.

```sh
docker compose up -d --build
open http://127.0.0.1:3000          # Linux desktop in the browser; WeChat autostarts
```

1. Scan the login QR code with your phone. Logging in here likely signs out your desktop
   WeChat on the Mac, since WeChat allows one desktop client. A second account avoids that.
2. Open 视频号 in the container's WeChat and scroll or play videos.
3. Watch `docker logs -f wxvd` for `[wxvd] <id> key=...` lines.

State (login, device id, CA, `wxvd/captures.jsonl`) lives in `./data`, so keep it between rebuilds.

## Download / decrypt

Inside the container:

```sh
docker exec -it -u abc -w /config/wxvd wxvd wxvd list
docker exec -it -u abc -w /config/wxvd wxvd wxvd download 0
```

Or on the host, reading the same file:

```sh
uv run wxvd --captures data/wxvd/captures.jsonl list
uv run wxvd download 0                 # by index or feed id; default quality
uv run wxvd download 0 --spec xWT111   # pick a quality from the record's `spec` list
uv run wxvd decrypt enc.mp4 out.mp4 --key 394253653
```
