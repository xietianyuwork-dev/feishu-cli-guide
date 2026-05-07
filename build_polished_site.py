#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
SOURCE = ROOT / "source.xml"


def slugify(text: str, fallback: str) -> str:
    text = re.sub(r"<[^>]+>", "", text).strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", text)
    slug = slug.strip("-")
    return slug or fallback


def text_content(node: ET.Element) -> str:
    return "".join(node.itertext()).strip()


def inline(node: ET.Element) -> str:
    parts: list[str] = []
    if node.text:
        parts.append(html.escape(node.text))
    for child in list(node):
        tag = child.tag.lower()
        content = inline(child)
        if tag in {"b", "strong"}:
            parts.append(f"<strong>{content}</strong>")
        elif tag in {"em", "i"}:
            parts.append(f"<em>{content}</em>")
        elif tag == "code":
            parts.append(f"<code>{content}</code>")
        elif tag == "a":
            href = html.escape(child.attrib.get("href", "#"))
            parts.append(f'<a href="{href}" target="_blank" rel="noreferrer">{content}</a>')
        elif tag == "br":
            parts.append("<br>")
        else:
            parts.append(content)
        if child.tail:
            parts.append(html.escape(child.tail))
    return "".join(parts)


def table_to_html(node: ET.Element) -> str:
    rows = node.findall(".//tr")
    if not rows:
        return ""
    output = ['<div class="table-wrap"><table>']
    for index, row in enumerate(rows):
        cells = row.findall("./th") or row.findall("./td")
        tag = "th" if index == 0 else "td"
        output.append("<tr>")
        for cell in cells:
            output.append(f"<{tag}>{inline(cell)}</{tag}>")
        output.append("</tr>")
    output.append("</table></div>")
    return "".join(output)


def node_to_html(node: ET.Element, toc: list[dict], counters: dict[str, int]) -> str:
    tag = node.tag.lower()
    if tag == "title":
        return ""
    if re.fullmatch(r"h[1-6]", tag):
        level = int(tag[1])
        label = text_content(node)
        counters["heading"] += 1
        anchor = slugify(label, f"section-{counters['heading']}")
        toc.append({"level": level, "text": label, "id": anchor})
        return f'<h{level} id="{anchor}">{inline(node)}</h{level}>'
    if tag == "p":
        content = inline(node)
        return f"<p>{content}</p>" if content else ""
    if tag == "callout":
        emoji = html.escape(node.attrib.get("emoji", "💡"))
        body = "".join(node_to_html(child, [], counters) for child in list(node))
        return f'<aside class="callout"><span class="callout-emoji">{emoji}</span><div>{body}</div></aside>'
    if tag == "hr":
        return "<hr>"
    if tag == "table":
        return table_to_html(node)
    if tag in {"ul", "ol"}:
        items = "".join(node_to_html(child, [], counters) for child in list(node))
        return f"<{tag}>{items}</{tag}>"
    if tag == "li":
        return f"<li>{inline(node)}</li>"
    if tag == "blockquote":
        return f"<blockquote>{''.join(node_to_html(child, [], counters) for child in list(node))}</blockquote>"
    if tag == "pre":
        code = text_content(node)
        lang = html.escape(node.attrib.get("lang", ""))
        return f'<pre><code class="language-{lang}">{html.escape(code)}</code></pre>'
    if tag == "img":
        name = html.escape(node.attrib.get("name", "document image"))
        src = html.escape(node.attrib.get("url") or node.attrib.get("href") or "")
        if not src:
            return f'<div class="media-placeholder">{name}</div>'
        return f'<figure><img src="{src}" alt="{name}"><figcaption>{name}</figcaption></figure>'
    return "".join(node_to_html(child, toc, counters) for child in list(node)) or html.escape(text_content(node))


def extract_feature_cards(root: ET.Element) -> list[tuple[str, str]]:
    cards: list[tuple[str, str]] = []
    first_table = root.find(".//table")
    if first_table is None:
        return cards
    for row in first_table.findall(".//tr")[1:7]:
        cells = row.findall("./td")
        if len(cells) >= 2:
            cards.append((text_content(cells[0]), text_content(cells[1])))
    return cards


def main() -> None:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    content = data["data"]["document"]["content"]
    wrapped = f"<root>{content}</root>"
    root = ET.fromstring(wrapped)
    title_node = root.find("./title")
    title = text_content(title_node) if title_node is not None else "Feishu CLI"

    toc: list[dict] = []
    counters = {"heading": 0}
    body = "\n".join(node_to_html(child, toc, counters) for child in list(root))
    cards = extract_feature_cards(root)

    card_html = "\n".join(
        f'<article class="feature-card"><p class="feature-kicker">{html.escape(name)}</p><p>{html.escape(desc)}</p></article>'
        for name, desc in cards
    )
    toc_html = "\n".join(
        f'<a class="toc-level-{item["level"]}" href="#{html.escape(item["id"])}">{html.escape(item["text"])}</a>'
        for item in toc
        if item["level"] <= 3
    )

    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "index.html").write_text(
        f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div class="progress" id="progress"></div>
  <header class="topbar">
    <a class="brand" href="#">
      <span class="brand-mark">CLI</span>
      <span>Feishu Agent Guide</span>
    </a>
    <nav><a href="#cli">简介</a><a href="#section-2">核心模块</a><a href="#section-28">应用场景</a></nav>
  </header>
  <main class="layout">
    <aside class="sidebar">
      <p class="eyebrow">Navigation</p>
      <h2>{html.escape(title)}</h2>
      <div class="toc">{toc_html}</div>
    </aside>
    <article class="content">
      <section class="hero">
        <div class="hero-copy">
          <p class="eyebrow">AI Agent × Feishu CLI</p>
          <h1>{html.escape(title)}</h1>
          <p class="lead">一份面向外部展示的飞书 CLI 能力说明：让 AI Agent 绕过视觉界面，直接调用文档、多维表格、消息、日历、会议、邮箱等飞书能力。</p>
        </div>
        <div class="hero-panel" aria-label="Feishu CLI highlights">
          <p class="panel-title">Agent Ready</p>
          <div class="command-card">
            <span>$</span>
            <code>lark-cli docs +create</code>
          </div>
          <div class="metric-grid">
            <div><strong>24</strong><span>能力模块</span></div>
            <div><strong>5</strong><span>典型场景</span></div>
            <div><strong>CLI</strong><span>标准化调用</span></div>
          </div>
        </div>
        <div class="hero-actions">
          <a href="#section-2">查看核心模块</a>
          <a href="#section-28">浏览使用场景</a>
        </div>
      </section>
      <section class="feature-grid">{card_html}</section>
      <section class="doc-body">{body}</section>
    </article>
  </main>
  <script src="app.js"></script>
</body>
</html>
""",
        encoding="utf-8",
    )

    (SITE / "styles.css").write_text(
        """ :root {
  --bg: #060913;
  --bg-soft: #0b1020;
  --paper: #f6f8fc;
  --surface: rgba(255,255,255,.88);
  --surface-strong: #fff;
  --ink: #101828;
  --muted: #64748b;
  --line: rgba(148,163,184,.22);
  --blue: #2f6bff;
  --cyan: #19d3ff;
  --violet: #8b5cf6;
  --green: #13c296;
  --shadow: 0 24px 80px rgba(15, 23, 42, .12);
  --shadow-strong: 0 34px 120px rgba(9, 16, 35, .2);
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  color: var(--ink);
  font-family: Inter, ui-sans-serif, "PingFang SC", "Noto Sans SC", system-ui, sans-serif;
  line-height: 1.78;
  background:
    radial-gradient(circle at 20% 0%, rgba(47,107,255,.26), transparent 32rem),
    radial-gradient(circle at 88% 12%, rgba(25,211,255,.18), transparent 30rem),
    linear-gradient(180deg, #060913 0, #0b1020 360px, #eef3ff 361px, #f7f9ff 100%);
}
a { color: var(--blue); }
.progress {
  position: fixed; top: 0; left: 0; height: 3px; width: 0;
  background: linear-gradient(90deg, var(--cyan), var(--blue), var(--violet));
  box-shadow: 0 0 24px rgba(25,211,255,.55);
  z-index: 20;
}
.topbar {
  position: sticky; top: 0; z-index: 19;
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px clamp(18px,4vw,56px);
  border-bottom: 1px solid rgba(255,255,255,.10);
  background: rgba(6,9,19,.72);
  backdrop-filter: blur(18px) saturate(160%);
}
.brand { display: inline-flex; gap: 12px; align-items: center; color: #fff; text-decoration: none; font-weight: 800; letter-spacing: -.02em; }
.brand-mark {
  width: 42px; height: 42px; display: grid; place-items: center; border-radius: 14px;
  background: linear-gradient(135deg, var(--cyan), var(--blue) 48%, var(--violet));
  color: white; font-weight: 900; letter-spacing: -.05em;
  box-shadow: 0 12px 34px rgba(47,107,255,.38);
}
.topbar nav { display: flex; gap: 8px; padding: 4px; border: 1px solid rgba(255,255,255,.1); border-radius: 999px; background: rgba(255,255,255,.06); }
.topbar nav a { color: rgba(255,255,255,.78); text-decoration: none; font-size: 14px; padding: 8px 14px; border-radius: 999px; }
.topbar nav a:hover { color: #fff; background: rgba(255,255,255,.1); }
.layout {
  display: grid;
  grid-template-columns: 304px minmax(0, 1fr);
  gap: clamp(28px,4vw,64px);
  width: min(1500px, 100%);
  margin: 0 auto;
  padding: clamp(22px,4vw,58px);
}
.sidebar {
  position: sticky; top: 92px; align-self: start; max-height: calc(100vh - 120px); overflow: auto;
  padding: 22px 18px;
  border: 1px solid rgba(255,255,255,.52);
  border-radius: 24px;
  background: rgba(255,255,255,.72);
  backdrop-filter: blur(18px) saturate(150%);
  box-shadow: var(--shadow);
}
.sidebar h2 { margin: 0 0 18px; font-size: 23px; line-height: 1.18; letter-spacing: -.04em; }
.eyebrow {
  margin: 0 0 10px;
  color: var(--blue);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: .14em;
  text-transform: uppercase;
}
.toc { display: grid; gap: 4px; }
.toc a {
  display: block; padding: 8px 10px; border-radius: 12px;
  color: #64748b; text-decoration: none; font-size: 14px; line-height: 1.35;
  transition: .18s ease;
}
.toc a:hover { background: rgba(47,107,255,.09); color: #0f172a; transform: translateX(2px); }
.toc-level-2 { padding-left: 22px !important; }
.toc-level-3 { padding-left: 34px !important; font-size: 13px !important; }
.content { min-width: 0; }
.hero {
  position: relative; overflow: hidden;
  display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(280px, .75fr); gap: clamp(28px,4vw,58px);
  align-items: end;
  padding: clamp(44px,7vw,92px);
  min-height: 520px;
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 34px;
  background:
    linear-gradient(135deg, rgba(255,255,255,.13), rgba(255,255,255,.04)),
    radial-gradient(circle at 72% 10%, rgba(25,211,255,.28), transparent 24rem),
    radial-gradient(circle at 12% 85%, rgba(139,92,246,.25), transparent 24rem),
    #0a1020;
  color: #fff;
  box-shadow: var(--shadow-strong);
}
.hero::before {
  content: ""; position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,.05) 1px, transparent 1px);
  background-size: 56px 56px;
  mask-image: linear-gradient(180deg, rgba(0,0,0,.76), transparent 84%);
  pointer-events: none;
}
.hero::after {
  content: ""; position: absolute; right: -90px; top: -120px; width: 360px; height: 360px;
  border-radius: 999px; background: rgba(25,211,255,.22); filter: blur(70px);
  pointer-events: none;
}
.hero-copy, .hero-panel, .hero-actions { position: relative; z-index: 1; }
.hero h1 { max-width: 900px; margin: 0; font-size: clamp(42px,6vw,86px); line-height: .98; letter-spacing: -.07em; }
.lead { max-width: 780px; margin: 28px 0 0; color: rgba(255,255,255,.74); font-size: clamp(18px,2vw,22px); }
.hero-panel {
  padding: 22px; border: 1px solid rgba(255,255,255,.16); border-radius: 26px;
  background: rgba(255,255,255,.08); backdrop-filter: blur(18px);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.14), 0 28px 70px rgba(0,0,0,.22);
}
.panel-title { margin: 0 0 14px; color: rgba(255,255,255,.72); font-size: 13px; font-weight: 900; letter-spacing: .14em; text-transform: uppercase; }
.command-card { display: flex; gap: 10px; align-items: center; padding: 16px; border-radius: 18px; background: rgba(0,0,0,.3); border: 1px solid rgba(255,255,255,.1); }
.command-card span { color: var(--cyan); font-weight: 900; }
.command-card code { color: #e2e8f0; white-space: nowrap; }
.metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 14px; }
.metric-grid div { padding: 14px 12px; border-radius: 16px; background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.1); }
.metric-grid strong { display: block; font-size: 26px; line-height: 1; letter-spacing: -.04em; }
.metric-grid span { display: block; margin-top: 6px; color: rgba(255,255,255,.62); font-size: 12px; }
.hero-actions { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 12px; margin-top: 2px; }
.hero-actions a {
  padding: 12px 18px; border: 1px solid rgba(255,255,255,.2); border-radius: 999px;
  background: #fff; color: #0f172a; text-decoration: none; font-weight: 800;
  box-shadow: 0 16px 38px rgba(0,0,0,.18);
}
.hero-actions a + a { background: rgba(255,255,255,.08); color: #fff; backdrop-filter: blur(10px); }
.feature-grid { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 18px; margin: 30px 0; }
.feature-card {
  position: relative; overflow: hidden;
  min-height: 172px;
  padding: 24px;
  border: 1px solid rgba(255,255,255,.72);
  border-radius: 24px;
  background: linear-gradient(180deg, rgba(255,255,255,.94), rgba(255,255,255,.76));
  box-shadow: var(--shadow);
}
.feature-card::before {
  content: ""; position: absolute; inset: 0 0 auto; height: 4px;
  background: linear-gradient(90deg, var(--cyan), var(--blue), var(--violet));
}
.feature-card p { margin: 0; position: relative; }
.feature-card p + p { margin-top: 12px; color: var(--muted); }
.feature-kicker { color: #0f172a; font-weight: 900; font-size: 18px; letter-spacing: -.03em; }
.doc-body {
  padding: clamp(34px,5vw,76px);
  border: 1px solid rgba(255,255,255,.72);
  border-radius: 32px;
  background: rgba(255,255,255,.88);
  box-shadow: var(--shadow);
  font-size: 17px;
}
.doc-body h1, .doc-body h2, .doc-body h3 { scroll-margin-top: 96px; line-height: 1.16; letter-spacing: -.05em; }
.doc-body h1 {
  margin: 2.35em 0 .75em; padding-top: 1.1em; border-top: 1px solid var(--line);
  font-size: clamp(34px,4vw,56px);
}
.doc-body h1:first-child { margin-top: 0; padding-top: 0; border-top: 0; }
.doc-body h1::before {
  content: ""; display: block; width: 46px; height: 5px; margin-bottom: 18px;
  border-radius: 999px; background: linear-gradient(90deg, var(--cyan), var(--blue), var(--violet));
}
.doc-body h2 { margin-top: 2.1em; font-size: clamp(24px,3vw,34px); }
.doc-body h3 { margin-top: 1.7em; font-size: 22px; }
.doc-body p { margin: 1em 0; color: #334155; }
.doc-body ul, .doc-body ol { padding-left: 1.25em; }
.doc-body li { margin: .42em 0; color: #334155; }
.doc-body strong { color: #111827; }
.callout {
  display: grid; grid-template-columns: auto 1fr; gap: 14px; margin: 26px 0; padding: 20px 22px;
  border: 1px solid rgba(47,107,255,.22); border-radius: 22px;
  background: linear-gradient(135deg, rgba(47,107,255,.08), rgba(25,211,255,.08));
}
.callout p { margin: 0; }
.callout-emoji { font-size: 24px; }
hr { border: 0; border-top: 1px solid var(--line); margin: 38px 0; }
.table-wrap {
  width: 100%; overflow-x: auto; margin: 28px 0;
  border: 1px solid var(--line); border-radius: 22px;
  box-shadow: 0 16px 50px rgba(15,23,42,.08);
}
table { width: 100%; border-collapse: separate; border-spacing: 0; min-width: 760px; background: #fff; }
th, td { padding: 15px 17px; border-bottom: 1px solid var(--line); border-right: 1px solid var(--line); vertical-align: top; }
th {
  position: sticky; top: 0;
  background: linear-gradient(180deg, #edf4ff, #e8f0ff);
  text-align: left; font-weight: 900; color: #1d4ed8;
}
tr:nth-child(even) td { background: #f8fbff; }
tr:hover td { background: #eef6ff; }
td:last-child, th:last-child { border-right: 0; }
tr:last-child td { border-bottom: 0; }
pre { overflow-x: auto; padding: 20px; border-radius: 18px; background: #080c18; color: #e2e8f0; box-shadow: inset 0 1px 0 rgba(255,255,255,.08); }
code { font-family: "SFMono-Regular", Consolas, monospace; font-size: .92em; }
p code, li code { padding: .16em .42em; border-radius: 8px; background: #eef4ff; color: #1d4ed8; }
figure { margin: 28px 0; }
figure img { max-width: 100%; border-radius: 22px; box-shadow: var(--shadow); }
figcaption { margin-top: 10px; color: var(--muted); text-align: center; font-size: 13px; }
@media (max-width: 1080px) {
  .layout { grid-template-columns: 1fr; }
  .sidebar { position: relative; top: auto; max-height: none; order: 2; }
  .hero { grid-template-columns: 1fr; min-height: auto; }
}
@media (max-width: 760px) {
  .topbar nav { display: none; }
  .layout { padding: 16px; }
  .brand span:last-child { display: none; }
  .feature-grid { grid-template-columns: 1fr; }
  .hero { padding: 34px 22px; border-radius: 26px; }
  .hero h1 { font-size: 40px; letter-spacing: -.055em; }
  .metric-grid { grid-template-columns: 1fr; }
  .doc-body { padding: 28px 18px; border-radius: 24px; }
  .doc-body h1 { font-size: 32px; }
}
""",
        encoding="utf-8",
    )

    (SITE / "app.js").write_text(
        """const progress = document.getElementById('progress');
window.addEventListener('scroll', () => {
  const max = document.documentElement.scrollHeight - innerHeight;
  progress.style.width = `${Math.max(0, Math.min(1, scrollY / max)) * 100}%`;
});
""",
        encoding="utf-8",
    )

    (SITE / "search-index.json").write_text(
        json.dumps({"title": title, "source": "Feishu Doc"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
