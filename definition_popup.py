"""Floating, draggable '📖 Define' widget via components.v1.html (escapes the iframe to overlay the page)."""
import html
import streamlit as st
import streamlit.components.v1 as components
from rag_engine import get_groq_response

DEFINE_PROMPT = """Define the CFA/finance term "{term}" in 1-2 short sentences, beginner-friendly.
Then on a new line write "MORE:" followed by a slightly deeper 3-4 sentence explanation with an example."""


def render_definition_popup():
    term = st.query_params.get("define_term", "")
    definition, more = "", ""
    if term:
        with st.spinner(""):
            resp = get_groq_response(
                [{"role": "user", "content": DEFINE_PROMPT.format(term=term)}],
                model="llama-3.1-8b-instant", temp=0.3,
            )
        text = resp.choices[0].message.content
        definition, _, more = text.partition("MORE:")

    term_e = html.escape(term)
    def_e = html.escape(definition.strip()).replace("\n", "<br>")
    more_html = ""
    if more.strip():
        more_e = html.escape(more.strip()).replace("\n", "<br>")
        more_html = f"<details><summary>More</summary><div class='d-more'>{more_e}</div></details>"

    page_html = f"""
    <style>
      html, body {{ margin:0; padding:0; background:transparent; font-family: sans-serif; }}
      #define-fab {{
        position:absolute; bottom:16px; right:16px; width:52px; height:52px; border-radius:50%;
        background:#c9a84c; color:#1a3c5e; display:flex; align-items:center; justify-content:center;
        font-size:22px; cursor:pointer; box-shadow:0 2px 8px rgba(0,0,0,.4); user-select:none;
      }}
      #define-panel {{
        position:absolute; bottom:76px; right:16px; width:300px; display:none;
        background:#1a3c5e; color:#f0f0f0; border:1px solid #c9a84c; border-radius:8px;
        box-shadow:0 4px 16px rgba(0,0,0,.5); overflow:hidden;
      }}
      #define-drag-handle {{
        background:#c9a84c; color:#1a3c5e; padding:6px 10px; cursor:move;
        display:flex; justify-content:space-between; font-weight:600; font-size:13px;
      }}
      #define-close {{ cursor:pointer; }}
      #define-body {{ padding:10px; font-size:13px; }}
      #define-input {{ width:100%; box-sizing:border-box; padding:6px; margin-bottom:6px; border-radius:4px; border:1px solid #c9a84c; }}
      #define-go {{ background:#c9a84c; color:#1a3c5e; border:none; padding:6px 10px; border-radius:4px; cursor:pointer; font-weight:600; }}
      #define-answer {{ margin-top:8px; line-height:1.4; }}
      details {{ margin-top:6px; }}
      summary {{ cursor:pointer; color:#c9a84c; }}
    </style>

    <div id="define-fab">📖</div>
    <div id="define-panel">
      <div id="define-drag-handle">📖 Define <span id="define-close">✕</span></div>
      <div id="define-body">
        <input id="define-input" type="text" placeholder="Type a term..." value="{term_e}" />
        <button id="define-go">Look up</button>
        <div id="define-answer"><strong>{term_e}</strong><br>{def_e}{more_html}</div>
      </div>
    </div>

    <script>
      (function() {{
        // Escape the sandboxed iframe so the widget overlays the whole app, not just its own box.
        const frame = window.frameElement;
        if (frame) {{
          frame.style.position = 'fixed';
          frame.style.bottom = '0'; frame.style.right = '0';
          frame.style.width = '340px'; frame.style.height = '480px';
          frame.style.border = 'none'; frame.style.zIndex = 999999;
          frame.style.background = 'transparent';
          frame.style.pointerEvents = 'auto';
        }}
        const fab = document.getElementById('define-fab');
        const panel = document.getElementById('define-panel');
        {"panel.style.display = 'block';" if term else ""}
        fab.onclick = () => panel.style.display = (panel.style.display === 'none' || !panel.style.display) ? 'block' : 'none';
        document.getElementById('define-close').onclick = () => panel.style.display = 'none';

        document.getElementById('define-go').onclick = () => {{
          const val = document.getElementById('define-input').value.trim();
          if (!val) return;
          const url = new URL(window.top.location.href);
          url.searchParams.set('define_term', val);
          window.top.location.href = url.toString();
        }};
        document.getElementById('define-input').addEventListener('keydown', (e) => {{
          if (e.key === 'Enter') document.getElementById('define-go').click();
        }});

        // Drag support on the handle
        let dragging = false, offX = 0, offY = 0;
        const handle = document.getElementById('define-drag-handle');
        handle.addEventListener('mousedown', (e) => {{
          dragging = true;
          offX = e.clientX - panel.getBoundingClientRect().left;
          offY = e.clientY - panel.getBoundingClientRect().top;
          panel.style.right = 'auto'; panel.style.bottom = 'auto';
        }});
        document.addEventListener('mouseup', () => dragging = false);
        document.addEventListener('mousemove', (e) => {{
          if (!dragging) return;
          panel.style.left = (e.clientX - offX) + 'px';
          panel.style.top = (e.clientY - offY) + 'px';
        }});
      }})();
    </script>
    """
    components.html(page_html, height=0, width=0)
