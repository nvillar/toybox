#!/usr/bin/env python3
"""Build a private, offline-capable image gallery with provenance and filters.

Usage:
  python3 scripts/gen/gallery.py out/concept/example --out-dir out/gallery --title "Concept studies"
  python3 -m http.server 8765 --bind 127.0.0.1 --directory out/gallery

Copies images into the output directory; never modifies the source.
Tested with Python 3.9.6 on macOS. No dependencies or external web requests.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path
from urllib.parse import quote, unquote

PAGE = r"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>__TITLE__</title>
<style>
:root{color-scheme:dark;--bg:#111413;--panel:#1b201e;--ink:#f1f0e8;--muted:#a8b3ac;--accent:#d7edb6;--line:#343e37}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui,sans-serif}
main{max-width:1600px;margin:auto;padding:36px clamp(18px,4vw,64px)}
.eyebrow{font-size:11px;letter-spacing:.18em;color:var(--accent);text-transform:uppercase}
h1{font:clamp(36px,5vw,66px)/1.08 Georgia,serif;letter-spacing:-.035em;margin:18px 0}
.intro{max-width:740px;color:var(--muted);margin-bottom:28px}.summary{color:var(--muted);font-size:13px}
.toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;padding:18px 0;margin:20px 0;border-block:1px solid var(--line)}
button,input,select{font:inherit;color:inherit;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:8px 12px}
button{cursor:pointer}button:hover{border-color:var(--accent)}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
button[aria-pressed=true]{background:var(--accent);color:#172015;border-color:var(--accent)}
.groups{display:flex;flex-wrap:wrap;gap:6px}input{flex:1;min-width:160px}select{max-width:100%}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(320px,100%),1fr));gap:22px;margin:18px 0 48px}
.card{padding:0;overflow:hidden;text-align:left;background:var(--panel);border:1px solid var(--line);border-radius:12px;transition:transform .15s}
.card:hover{transform:translateY(-3px)}.card img{width:100%;aspect-ratio:16/10;object-fit:contain;background:#141615;display:block}
.card section{padding:14px 16px}.card h2{font-size:16px;font-weight:550;margin:0 0 6px}
.meta{font-size:12px;color:var(--muted)}.badge{display:inline-block;font-size:10px;letter-spacing:.03em;margin-top:9px;border:1px solid #535b4c;border-radius:4px;padding:2px 6px;color:#d7d3ac}
footer{color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:18px}
dialog{width:min(1400px,96vw);max-height:94vh;border:1px solid var(--line);border-radius:14px;padding:0;background:var(--bg);color:var(--ink)}
dialog::backdrop{background:#000c;backdrop-filter:blur(7px)}.viewer-head{display:flex;gap:12px;align-items:center;padding:14px 20px}
.viewer-head h2{flex:1;font-size:18px;margin:0}.viewer-image{display:block;width:100%;max-height:66vh;object-fit:contain;background:#090b0a}
.details{padding:18px 24px}.details p{margin:8px 0;white-space:pre-wrap}.details summary{cursor:pointer;color:var(--accent)}
a{color:var(--accent)}.viewer-actions{display:flex;flex-wrap:wrap;align-items:center;gap:12px}.viewer-actions span{flex:1;color:var(--muted);font-size:13px}
@media(max-width:600px){main{padding-top:24px}.viewer-head{padding:12px}.details{padding:14px}.viewer-head h2{font-size:15px}}
</style>
<main>
  <div class="eyebrow">Toybox / Private viewing room</div>
  <h1>__TITLE__</h1>
  <p class="intro">A working collection of concept images, character studies and visual experiments.
  Explore the rounds below. Open any image for a full-size view, its prompt and generation details.</p>
  <div class="summary" id="totals"></div>
  <div class="toolbar">
    <div class="groups" id="groups" aria-label="Filter by round"></div>
    <select id="model" aria-label="Filter by model"><option value="">All models</option></select>
    <input id="search" type="search" placeholder="Find a scene or prompt..." aria-label="Search scenes and prompts">
  </div>
  <div class="summary" id="count" role="status" aria-live="polite"></div>
  <div class="grid" id="grid"></div>
  <footer>Local gallery &middot; No external services, fonts or analytics.
  Research images and mixed-model sheets are not automatically cleared for commercial use.</footer>
</main>
<dialog id="viewer" aria-labelledby="viewer-title">
  <div class="viewer-head"><h2 id="viewer-title"></h2><button id="close" aria-label="Close image">Close &times;</button></div>
  <img class="viewer-image" id="full" alt="">
  <div class="details">
    <div class="viewer-actions">
      <button id="prev" aria-label="Previous image">&larr; Previous</button>
      <button id="next" aria-label="Next image">Next &rarr;</button>
      <span id="position"></span><a id="original" target="_blank" rel="noopener">Open original</a>
    </div>
    <p class="meta" id="provenance"></p>
    <details><summary>Generation prompt</summary><p id="prompt"></p></details>
  </div>
</dialog>
<script type="application/json" id="data">__DATA__</script>
<script>
const items = JSON.parse(document.getElementById('data').textContent);
const $ = id => document.getElementById(id);
let group = '', filtered = [], active = 0;
const models = [...new Set(items.map(x => x.model).filter(Boolean))].sort();
models.forEach(model => { const option = new Option(model, model); $('model').add(option); });
const rounds = [...new Set(items.map(x => x.group))];
$('totals').textContent = `${items.length} images & review sheets / ${models.length} models / ${rounds.length} collections`;
['', ...rounds].forEach(value => {
  const button = document.createElement('button');
  button.textContent = value || 'Everything';
  button.setAttribute('aria-pressed', value === '' ? 'true' : 'false');
  button.onclick = () => {
    group = value;
    for (const other of $('groups').children) other.setAttribute('aria-pressed', String(other === button));
    render();
  };
  $('groups').append(button);
});
function metadata(item) {
  return [item.group, item.model || 'Review sheet', item.seed == null ? '' : `Seed ${item.seed}`].filter(Boolean).join(' / ');
}
function render() {
  const query = $('search').value.trim().toLowerCase();
  filtered = items.filter(item =>
    (!group || item.group === group) && (!$('model').value || item.model === $('model').value) &&
    `${item.name} ${item.prompt}`.toLowerCase().includes(query));
  $('count').textContent = `${filtered.length} of ${items.length} results`;
  $('grid').replaceChildren();
  filtered.forEach((item, index) => {
    const card = document.createElement('button'); card.className = 'card';
    const img = document.createElement('img'); img.src = item.src; img.alt = item.name; img.loading = 'lazy';
    const section = document.createElement('section');
    const name = document.createElement('h2'); name.textContent = item.name;
    const meta = document.createElement('div'); meta.className = 'meta'; meta.textContent = metadata(item);
    section.append(name, meta);
    if (!item.license || /non-commercial|research/i.test(item.license)) {
      const badge = document.createElement('span'); badge.className = 'badge';
      badge.textContent = item.license ? 'NON-COMMERCIAL / RESEARCH' : 'RIGHTS: CHECK SOURCE IMAGES';
      section.append(badge);
    }
    card.append(img, section); card.onclick = () => show(index); $('grid').append(card);
  });
}
function show(index) {
  active = (index + filtered.length) % filtered.length;
  const item = filtered[active];
  $('viewer-title').textContent = item.name;
  $('full').src = item.src; $('full').alt = item.name; $('original').href = item.src;
  $('position').textContent = `${active + 1} / ${filtered.length}`;
  $('provenance').textContent = `${metadata(item)} / ${item.license || 'No sidecar: check source-image licences'}${item.elapsed == null ? '' : ` / ${item.elapsed}s`}`;
  $('prompt').textContent = item.prompt || 'Composite review sheet. Refer to the individual source images for prompts and licence terms.';
  if (!$('viewer').open) $('viewer').showModal();
}
$('search').oninput = render; $('model').onchange = render;
$('close').onclick = () => $('viewer').close();
$('prev').onclick = () => show(active - 1); $('next').onclick = () => show(active + 1);
$('viewer').addEventListener('keydown', event => {
  if (event.key === 'ArrowLeft') { event.preventDefault(); show(active - 1); }
  if (event.key === 'ArrowRight') { event.preventDefault(); show(active + 1); }
});
render();
</script>
</html>
"""


def build_gallery(source: Path, output: Path, title: str) -> int:
    source, output = source.resolve(), output.resolve()
    if not source.is_dir():
        raise ValueError(f"Source directory does not exist: {source}")
    if output == source or source in output.parents or output in source.parents:
        raise ValueError("Source and output directories must be separate, not nested.")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError(f"Choose a new or empty output directory: {output}")
    items = []
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if any(part.startswith(".") for part in relative.parts):
            continue
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"} or not path.is_file():
            continue
        if source not in path.resolve().parents:
            raise ValueError(f"Image points outside source: {path}")
        sidecar = path.with_suffix(path.suffix + ".json")
        data = {}
        if sidecar.exists():
            if source not in sidecar.resolve().parents:
                raise ValueError(f"Sidecar points outside source: {sidecar}")
            data = json.loads(sidecar.read_text())
            if not isinstance(data, dict):
                raise ValueError(f"Expected JSON object in {sidecar}")
        name = re.sub(r"_(klein4b|klein9b|qwen21)_s\d+$", "", path.stem)
        name = name.strip("_").replace("_", " ").capitalize()
        group = relative.parts[0] if len(relative.parts) > 1 else "Overview"
        items.append({
            "src": "media/" + quote(relative.as_posix(), safe="/"),
            "name": name, "group": group, "model": data.get("model", ""),
            "seed": data.get("seed"), "prompt": data.get("prompt", ""),
            "license": data.get("license", ""), "elapsed": data.get("elapsed_s"),
        })
    if not items:
        raise ValueError(f"No supported images found in {source}")
    output.mkdir(parents=True, exist_ok=True)
    for item in items:
        # Use the original relative path rather than its URL-encoded form.
        relative = Path(unquote(item["src"][len("media/"):]))
        destination = output / "media" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, destination)
    priority = {"Overview": 0, "v2": 1, "v1": 2, "probe": 3}
    items.sort(key=lambda item: (priority.get(item["group"], 4), item["group"], item["src"]))
    payload = json.dumps(items, ensure_ascii=True).replace("<", "\\u003c")
    page = PAGE.replace("__TITLE__", html.escape(title)).replace("__DATA__", payload)
    (output / "index.html").write_text(page, encoding="utf-8")
    return len(items)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("out/gallery"))
    parser.add_argument("--title", default="Concept studies")
    args = parser.parse_args()
    try:
        count = build_gallery(args.source, args.out_dir, args.title)
    except (OSError, ValueError) as error:
        parser.exit(1, f"gallery: {error}\n")
    print(f"wrote {args.out_dir / 'index.html'} ({count} images)")


if __name__ == "__main__":
    main()
