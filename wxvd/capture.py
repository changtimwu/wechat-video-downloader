"""mitmproxy addon: log WeChat Channels feed media (url + decodeKey) as JSONL.

    mitmdump -s wxvd/capture.py --set wxvd_out=captures.jsonl

Watches JSON responses from channels.weixin.qq.com, finds every feed object
(anything with ``objectDesc.media``) and appends one record per video. The
url and decodeKey must come from the same response, so they are stored together.
"""

import json
import time
from pathlib import Path

from mitmproxy import ctx, http

HOSTS = ("channels.weixin.qq.com",)


def _iter_feeds(node):
    if isinstance(node, dict):
        desc = node.get("objectDesc")
        if isinstance(desc, dict) and isinstance(desc.get("media"), list):
            yield node
        for v in node.values():
            yield from _iter_feeds(v)
    elif isinstance(node, list):
        for v in node:
            yield from _iter_feeds(v)


def _record(feed, source):
    media = feed["objectDesc"]["media"]
    if not media or not media[0].get("decodeKey"):
        return None  # picture posts / feeds without an encrypted video
    m = media[0]
    contact = feed.get("contact") or {}
    return {
        "captured_at": int(time.time()),
        "id": str(feed.get("id", "")),
        "nonce_id": feed.get("objectNonceId"),
        "title": (feed["objectDesc"].get("description") or "").strip(),
        "author": contact.get("nickname"),
        "url": (m.get("url") or "") + (m.get("urlToken") or ""),
        "decode_key": str(m["decodeKey"]),
        "size": m.get("fileSize"),
        "duration": m.get("videoPlayLen"),
        "cover": m.get("coverUrl") or m.get("thumbUrl"),
        "spec": [s.get("fileFormat") for s in m.get("spec") or [] if s.get("fileFormat")],
        "source": source,
    }


class ChannelsCapture:
    def __init__(self):
        self.seen = set()

    def load(self, loader):
        loader.add_option("wxvd_out", str, "captures.jsonl", "JSONL file for captured feeds")

    def response(self, flow: http.HTTPFlow):
        if flow.request.pretty_host not in HOSTS or not flow.response:
            return
        if "json" not in flow.response.headers.get("content-type", ""):
            return
        try:
            body = json.loads(flow.response.get_text(strict=False) or "")
        except ValueError:
            return
        out = Path(ctx.options.wxvd_out)
        for feed in _iter_feeds(body):
            rec = _record(feed, flow.request.path.split("?")[0])
            if not rec or (rec["id"], rec["decode_key"]) in self.seen:
                continue
            self.seen.add((rec["id"], rec["decode_key"]))
            with out.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            ctx.log.info(f"[wxvd] {rec['id']} key={rec['decode_key']} {rec['title'][:40]!r}")


addons = [ChannelsCapture()]
