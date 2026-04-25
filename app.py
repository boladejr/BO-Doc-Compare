"""
app.py — DocDiff: Document Comparison Tool
Run with: streamlit run app.py
"""

import os
import tempfile
import streamlit as st
from datetime import datetime

from extractor import extract_text
from comparator import compare_documents, ComparisonResult, Change
from reporter import build_text_report, build_pdf_report


# ─── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="DocDiff — Document Comparison",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ─── CSS ──────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:ital,wght@0,400;0,600;1,400&family=Sora:wght@400;500;600;700&display=swap');

  :root {
    --added-bg:     #e6f9ed;  --added-fg:    #145a2e;  --added-bdr:   #22c55e;
    --removed-bg:   #fef1f2;  --removed-fg:  #7f1d1d;  --removed-bdr: #ef4444;
    --modified-bg:  #fffbeb;  --modified-fg: #78350f;  --modified-bdr:#f59e0b;
    --moved-bg:     #eff6ff;  --moved-fg:    #1e3a5f;  --moved-bdr:   #3b82f6;
    --selected-ring:#6366f1;
    --panel-bg:     #f8f9fc;
    --border:       #e2e6ef;
    --mono: 'IBM Plex Mono', monospace;
    --sans: 'Sora', sans-serif;
    --radius: 10px;
  }

  html, body, [class*="css"] { font-family: var(--sans); }

  /* ── Top bar ── */
  .top-bar { display:flex; align-items:baseline; gap:12px; margin-bottom:4px; }
  .app-title { font-size:1.9rem; font-weight:700; letter-spacing:-0.03em; color:#1a1a2e; }
  .app-sub   { font-size:0.95rem; color:#6b7280; }

  /* ── Stats pills ── */
  .pills { display:flex; flex-wrap:wrap; gap:6px; margin:10px 0 6px; }
  .pill {
    display:inline-flex; align-items:center; gap:4px;
    padding:3px 12px; border-radius:99px; font-size:0.8rem; font-weight:600;
    cursor:default;
  }
  .pill.added    { background:var(--added-bg);    color:var(--added-fg); }
  .pill.removed  { background:var(--removed-bg);  color:var(--removed-fg); }
  .pill.modified { background:var(--modified-bg); color:var(--modified-fg); }
  .pill.moved    { background:var(--moved-bg);    color:var(--moved-fg); }
  .pill.material { background:#fce7f3; color:#831843; }

  /* ── Panel label ── */
  .panel-label {
    font-size:0.72rem; font-weight:700; letter-spacing:0.1em;
    text-transform:uppercase; color:#9ca3af; margin-bottom:8px;
  }

  /* ── Change card ── */
  .change-card {
    border-radius:var(--radius); padding:11px 14px; margin-bottom:4px;
    border-left:4px solid;
    transition: box-shadow 0.12s, transform 0.08s;
    font-size:0.84rem; line-height:1.45;
    position:relative; pointer-events:none;
  }
  .change-card.selected {
    box-shadow:0 0 0 2.5px var(--selected-ring);
    transform:translateX(3px);
  }
  .change-card.added    { background:var(--added-bg);    color:var(--added-fg);    border-color:var(--added-bdr); }
  .change-card.removed  { background:var(--removed-bg);  color:var(--removed-fg);  border-color:var(--removed-bdr); }
  .change-card.modified { background:var(--modified-bg); color:var(--modified-fg); border-color:var(--modified-bdr); }
  .change-card.moved    { background:var(--moved-bg);    color:var(--moved-fg);    border-color:var(--moved-bdr); }

  .card-top  { display:flex; align-items:center; gap:6px; margin-bottom:5px; flex-wrap:wrap; }
  .card-type { font-weight:700; font-size:0.72rem; letter-spacing:0.07em; text-transform:uppercase; }
  .card-pos  { font-family:var(--mono); font-size:0.68rem; background:rgba(0,0,0,0.07); padding:1px 7px; border-radius:4px; }
  .card-mat  { background:#ef4444; color:#fff; font-size:0.64rem; font-weight:700; padding:1px 7px; border-radius:99px; letter-spacing:0.04em; }
  .card-sim  { font-size:0.68rem; opacity:0.7; margin-left:auto; font-family:var(--mono); }

  .card-text { font-family:var(--mono); font-size:0.75rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; opacity:0.85; margin-top:2px; }
  .card-text.old { color:#991b1b; }
  .card-text.new { color:#166534; }

  /* ── Click button wrapper — make full card clickable ── */
  .card-wrap { position:relative; margin-bottom:4px; }
  .card-wrap > div[data-testid="stButton"] {
    position:absolute; inset:0; z-index:10;
  }
  .card-wrap > div[data-testid="stButton"] > button {
    width:100%; height:100%; opacity:0;
    cursor:pointer; border:none; background:transparent;
    padding:0; margin:0;
  }
  .card-wrap:hover .change-card {
    box-shadow:0 3px 14px rgba(0,0,0,0.1);
    transform:translateX(2px);
  }

  /* ── Document viewer panel ── */
  .viewer-panel {
    background:#fff; border:1px solid var(--border);
    border-radius:12px; overflow:hidden;
  }
  .viewer-header {
    background:#1a1a2e; color:#e2e8f0;
    padding:9px 14px; font-size:0.78rem;
    font-family:var(--mono);
    display:flex; align-items:center; gap:10px;
  }
  .viewer-header .vh-title { font-weight:500; flex:1; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
  .viewer-header .vh-badge {
    font-size:0.65rem; padding:2px 9px; border-radius:99px;
    font-family:var(--sans); font-weight:700; letter-spacing:0.04em; white-space:nowrap;
  }
  .vh-badge.added    { background:#22c55e; color:#fff; }
  .vh-badge.removed  { background:#ef4444; color:#fff; }
  .vh-badge.modified { background:#f59e0b; color:#fff; }
  .vh-badge.moved    { background:#3b82f6; color:#fff; }

  /* ── Doc lines ── */
  .doc-lines { padding:4px 0; }
  .doc-line  {
    display:grid; grid-template-columns:44px 1fr;
    font-family:var(--mono); font-size:0.78rem; line-height:1.65;
  }
  .doc-line .ln {
    color:#9ca3af; text-align:right; padding:0 8px;
    user-select:none; border-right:1px solid #eee;
    background:#f9fafb; font-size:0.72rem;
  }
  .doc-line .lt { padding:0 12px; white-space:pre-wrap; word-break:break-word; }

  .doc-line.hl-added    .lt { background:#bbf7d0; color:#14532d; font-weight:500; }
  .doc-line.hl-added    .ln { background:#dcfce7; color:#15803d; font-weight:700; }
  .doc-line.hl-removed  .lt { background:#fecaca; color:#7f1d1d; }
  .doc-line.hl-removed  .ln { background:#fee2e2; color:#dc2626; font-weight:700; }
  .doc-line.hl-modified .lt { background:#fef08a; color:#713f12; font-weight:500; }
  .doc-line.hl-modified .ln { background:#fef9c3; color:#b45309; font-weight:700; }
  .doc-line.hl-moved    .lt { background:#bfdbfe; color:#1e3a5f; }
  .doc-line.hl-moved    .ln { background:#dbeafe; color:#1d4ed8; font-weight:700; }
  .doc-line.context     .lt { background:#fff;    color:#374151; }
  .doc-line.ellipsis    .lt { background:#f9fafb; color:#9ca3af; font-style:italic; }
  .doc-line.ellipsis    .ln { background:#f3f4f6; }

  /* ── Scrollable containers ── */
  .change-scroll { max-height:70vh; overflow-y:auto; padding-right:2px; }
  .change-scroll::-webkit-scrollbar { width:4px; }
  .change-scroll::-webkit-scrollbar-thumb { background:#d1d5db; border-radius:99px; }

  .doc-scroll { max-height:70vh; overflow-y:auto; }
  .doc-scroll::-webkit-scrollbar { width:4px; }
  .doc-scroll::-webkit-scrollbar-thumb { background:#d1d5db; border-radius:99px; }

  /* ── Welcome placeholder ── */
  .welcome {
    border:2px dashed #d1d5db; border-radius:14px;
    padding:50px 30px; text-align:center; color:#9ca3af;
    font-size:0.9rem; line-height:1.9;
  }
  .welcome .big { font-size:3rem; margin-bottom:8px; }

  /* ── Group divider ── */
  .grp-div {
    font-size:0.68rem; font-weight:700; color:#9ca3af;
    letter-spacing:0.09em; text-transform:uppercase;
    margin:10px 0 4px; display:flex; align-items:center; gap:8px;
  }
  .grp-div::after { content:''; flex:1; height:1px; background:#e5e7eb; }

  /* ── Absent line placeholder ── */
  .absent-line {
    padding:30px 20px; text-align:center; color:#9ca3af;
    font-size:0.82rem; font-style:italic;
  }
</style>
""", unsafe_allow_html=True)


# ─── Session State ────────────────────────────────────────────────────────────

for k, v in {
    "result": None, "old_text": None, "new_text": None,
    "old_name": "", "new_name": "",
    "selected_idx": None,
    "filter_material": False, "ignore_punct": False, "similarity": 0.60,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─── Helpers ──────────────────────────────────────────────────────────────────

ICONS  = {"added": "✚", "removed": "✖", "modified": "✎", "moved": "↕"}
LABELS = {"added": "ADDED", "removed": "REMOVED", "modified": "MODIFIED", "moved": "MOVED"}

def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def safe_extract(name: str, file_bytes: bytes):
    try:
        return extract_text(name, file_bytes), None
    except Exception as e:
        return None, str(e)


# ─── Card HTML ────────────────────────────────────────────────────────────────

def _card_html(c: Change, selected: bool) -> str:
    ctype = c.change_type
    sel_cls = " selected" if selected else ""
    icon, label = ICONS.get(ctype,"?"), LABELS.get(ctype, ctype.upper())

    pos_tags = []
    if c.old_line_num: pos_tags.append(f"L{c.old_line_num}")
    if c.new_line_num and c.new_line_num != c.old_line_num: pos_tags.append(f"→L{c.new_line_num}")
    if c.old_para_num: pos_tags.append(f"¶{c.old_para_num}")
    pos_html = "".join(f'<span class="card-pos">{p}</span>' for p in pos_tags)

    mat  = '<span class="card-mat">⚡ MATERIAL</span>' if c.is_material else ""
    sim  = f'<span class="card-sim">{int(c.similarity*100)}%</span>' if ctype=="modified" else ""

    if ctype == "added":
        preview = f'<div class="card-text new">+ {_esc((c.new_text or "")[:85])}</div>'
    elif ctype == "removed":
        preview = f'<div class="card-text old">− {_esc((c.old_text or "")[:85])}</div>'
    elif ctype == "modified":
        preview = (f'<div class="card-text old">− {_esc((c.old_text or "")[:75])}</div>'
                   f'<div class="card-text new">+ {_esc((c.new_text or "")[:75])}</div>')
    else:
        preview = f'<div class="card-text">↕ {_esc((c.old_text or c.new_text or "")[:85])}</div>'

    return (f'<div class="change-card {ctype}{sel_cls}">'
            f'<div class="card-top"><span class="card-type">{icon} {label}</span>{pos_html}{mat}{sim}</div>'
            f'{preview}</div>')


# ─── Document Viewer ──────────────────────────────────────────────────────────

CONTEXT = 6  # lines of context above/below

def _viewer_html(lines: list, highlight: int | None, ctype: str) -> str:
    n = len(lines)
    if not lines:
        return '<div class="absent-line">Document is empty.</div>'

    if highlight is None or highlight < 1 or highlight > n:
        window = list(range(0, min(35, n)))
        top_ell, bot_ell = False, n > 35
    else:
        hi = highlight - 1
        start = max(0, hi - CONTEXT)
        end   = min(n - 1, hi + CONTEXT)
        window = list(range(start, end + 1))
        top_ell = start > 0
        bot_ell = end < n - 1

    rows = []
    if top_ell:
        rows.append(f'<div class="doc-line ellipsis"><span class="ln">…</span><span class="lt">  ··· {window[0]} lines above ···</span></div>')

    for i in window:
        ln = i + 1
        txt = _esc(lines[i]) if lines[i].strip() else "&nbsp;"
        cls = f"hl-{ctype}" if (highlight and ln == highlight) else "context"
        rows.append(f'<div class="doc-line {cls}"><span class="ln">{ln}</span><span class="lt">{txt}</span></div>')

    if bot_ell:
        remaining = n - window[-1] - 1
        rows.append(f'<div class="doc-line ellipsis"><span class="ln">…</span><span class="lt">  ··· {remaining} lines below ···</span></div>')

    return f'<div class="doc-lines">{"".join(rows)}</div>'


def render_viewer(c: Change | None, old_lines: list, new_lines: list):
    if c is None:
        st.markdown("""<div class="welcome">
  <div class="big">👈</div>
  <strong style="color:#374151">Click any change</strong> on the left panel<br>
  to jump to it in the document here.
</div>""", unsafe_allow_html=True)
        return

    ctype = c.change_type
    badge = f'<span class="vh-badge {ctype}">{ICONS[ctype]} {LABELS[ctype]}</span>'

    vc1, vc2 = st.columns(2, gap="small")

    # ─ Old doc ─
    with vc1:
        if ctype == "added":
            hdr = "Old Document — not present"
            hl, body = None, f'<div class="absent-line">This line was added in the new version.</div>'
        else:
            hdr = f"Old Document · L{c.old_line_num or '?'}"
            hl, body = c.old_line_num, _viewer_html(old_lines, c.old_line_num, ctype)
        st.markdown(
            f'<div class="viewer-panel"><div class="viewer-header">'
            f'<span class="vh-title">📄 {hdr}</span>{badge}</div>'
            f'<div class="doc-scroll">{body}</div></div>',
            unsafe_allow_html=True)

    # ─ New doc ─
    with vc2:
        if ctype == "removed":
            hdr = "New Document — line removed"
            body = f'<div class="absent-line">This line was removed from the old version.</div>'
        else:
            hdr = f"New Document · L{c.new_line_num or '?'}"
            body = _viewer_html(new_lines, c.new_line_num, ctype)
        st.markdown(
            f'<div class="viewer-panel"><div class="viewer-header">'
            f'<span class="vh-title">📄 {hdr}</span>{badge}</div>'
            f'<div class="doc-scroll">{body}</div></div>',
            unsafe_allow_html=True)

    # ─ Metadata strip ─
    meta = []
    if c.material_tags: meta.append(f"⚡ {' · '.join(c.material_tags)}")
    if ctype == "modified": meta.append(f"≈ {int(c.similarity*100)}% similar to original")
    if c.old_para_num: meta.append(f"Paragraph {c.old_para_num}")
    if meta:
        st.markdown(
            '<div style="margin-top:6px;font-size:0.78rem;color:#6b7280;display:flex;gap:18px;flex-wrap:wrap">'
            + "".join(f"<span>{m}</span>" for m in meta) + "</div>",
            unsafe_allow_html=True)


# ─── Change List ──────────────────────────────────────────────────────────────

def render_change_list(changes: list):
    groups: dict = {}
    for idx, c in enumerate(changes):
        groups.setdefault(c.group_id or 0, []).append((idx, c))

    for gid, items in sorted(groups.items()):
        if len(items) > 1:
            st.markdown(f'<div class="grp-div">Cluster {gid+1} · {len(items)} nearby</div>', unsafe_allow_html=True)

        for idx, c in items:
            selected = (st.session_state.selected_idx == idx)

            # Render the visual card
            st.markdown(_card_html(c, selected), unsafe_allow_html=True)

            # Transparent full-width button overlaid via CSS .card-wrap trick
            # We use a container + negative margin to lay button ON TOP of the card
            st.markdown('<div style="margin-top:-52px;margin-bottom:4px;opacity:0;height:48px">', unsafe_allow_html=True)
            if st.button("select", key=f"btn_{idx}", help="Click to open in document viewer"):
                st.session_state.selected_idx = idx
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


# ─── Stats Bar ────────────────────────────────────────────────────────────────

def render_stats(s: dict):
    st.markdown(f"""<div class="pills">
  <span class="pill added">✚ {s['added']} Added</span>
  <span class="pill removed">✖ {s['removed']} Removed</span>
  <span class="pill modified">✎ {s['modified']} Modified</span>
  <span class="pill moved">↕ {s['moved']} Moved</span>
  <span class="pill material">⚡ {s['material_changes']} Material</span>
  <span style="font-size:0.75rem;color:#9ca3af;align-self:center">
    Old {s['old_lines']}L / New {s['new_lines']}L
  </span>
</div>""", unsafe_allow_html=True)


# ─── Main ─────────────────────────────────────────────────────────────────────

st.markdown('<div class="top-bar"><span class="app-title">📄 DocDiff</span>'
            '<span class="app-sub">— click a change to inspect it live in the document</span></div>',
            unsafe_allow_html=True)

# ── Upload & settings expander ──
with st.expander("⚙️ Upload Files & Settings", expanded=st.session_state.result is None):
    u1, u2 = st.columns(2)
    with u1:
        st.caption("**Old Version**")
        old_file = st.file_uploader("Old", type=["txt","docx","pdf","xlsx"], key="up_old", label_visibility="collapsed")
    with u2:
        st.caption("**New Version**")
        new_file = st.file_uploader("New", type=["txt","docx","pdf","xlsx"], key="up_new", label_visibility="collapsed")

    s1, s2, s3 = st.columns(3)
    with s1: ign_p = st.checkbox("Ignore punctuation-only", value=st.session_state.ignore_punct)
    with s2: show_mat = st.checkbox("Material changes only", value=st.session_state.filter_material)
    with s3: sim = st.slider("Sensitivity", 0.30, 0.95, st.session_state.similarity, 0.05)

    if st.button("🔍 Compare Documents", type="primary", use_container_width=True):
        if not old_file or not new_file:
            st.error("❌ Please upload both files.")
        else:
            with st.spinner("Extracting text…"):
                ob, nb = old_file.read(), new_file.read()
                ot, oe = safe_extract(old_file.name, ob)
                nt, ne = safe_extract(new_file.name, nb)
            if oe: st.error(f"❌ Old file: {oe}")
            elif ne: st.error(f"❌ New file: {ne}")
            else:
                with st.spinner("Comparing…"):
                    result = compare_documents(ot or "", nt or "", ignore_punctuation=ign_p, similarity_threshold=sim)
                st.session_state.update({
                    "result": result, "old_text": ot or "", "new_text": nt or "",
                    "old_name": old_file.name, "new_name": new_file.name,
                    "selected_idx": None, "filter_material": show_mat,
                    "ignore_punct": ign_p, "similarity": sim,
                })
                st.rerun()

# ── Results ──
result: ComparisonResult | None = st.session_state.result

if result is None:
    st.markdown("""<div class="welcome" style="margin-top:28px;">
  <div class="big">📄</div>
  <strong style="color:#374151;font-size:1.05rem">Welcome to DocDiff</strong><br>
  Upload two documents above and click <strong>Compare</strong>.<br>
  Each change appears as a clickable card — click it to jump to that spot in the document.
  <br><br>
  <code style="font-size:0.8rem">.txt &nbsp; .docx &nbsp; .pdf &nbsp; .xlsx</code>
</div>""", unsafe_allow_html=True)

else:
    render_stats(result.stats)

    # Apply filter
    changes = result.changes
    if st.session_state.filter_material:
        changes = [c for c in changes if c.is_material]

    if not changes:
        st.info("No changes match the current filter.")
    else:
        # ── Split panel ──
        left, right = st.columns([5, 12], gap="large")

        with left:
            st.markdown(f'<div class="panel-label">🔍 {len(changes)} change{"s" if len(changes)!=1 else ""} — click to inspect</div>',
                        unsafe_allow_html=True)
            st.markdown('<div class="change-scroll">', unsafe_allow_html=True)
            render_change_list(changes)
            st.markdown('</div>', unsafe_allow_html=True)

        with right:
            sel = st.session_state.selected_idx
            sel_change = changes[sel] if (sel is not None and sel < len(changes)) else None
            old_lines = st.session_state.old_text.split("\n")
            new_lines = st.session_state.new_text.split("\n")

            st.markdown(
                '<div class="panel-label">📄 Document view — old &amp; new side by side, change highlighted</div>',
                unsafe_allow_html=True)
            render_viewer(sel_change, old_lines, new_lines)

    # ── Export ──
    with st.expander("💾 Export Report", expanded=False):
        ec1, ec2 = st.columns(2)
        txt = build_text_report(result, st.session_state.old_name, st.session_state.new_name)
        with ec1:
            st.download_button("📥 Download TXT", txt.encode(),
                f"diff_{datetime.now():%Y%m%d_%H%M}.txt", "text/plain", use_container_width=True)
        with ec2:
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp_path = tmp.name
                out = build_pdf_report(result, st.session_state.old_name, st.session_state.new_name, tmp_path)
                pdf_data = open(out,"rb").read(); os.unlink(out)
                ext = "pdf" if out.endswith(".pdf") else "txt"
                st.download_button(f"📥 Download {ext.upper()}", pdf_data,
                    f"diff_{datetime.now():%Y%m%d_%H%M}.{ext}", use_container_width=True)
            except Exception:
                st.caption("PDF export: `pip install reportlab`")
