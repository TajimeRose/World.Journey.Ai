"""Stub guide helpers used by chatbot during development."""
def build_bangkok_guides_html(entries):
    """Return a simple HTML block for a list of guide entries."""
    if not entries:
        return ""
    parts = [f"<article><h3>{e.get('name','')}</h3><p>{e.get('summary','')}</p></article>" for e in entries]
    return '<div class="bangkok-guides">' + ''.join(parts) + '</div>'
