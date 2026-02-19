"""Markdown to HTML converter for email reports."""

import sys
import re


def markdown_to_html(md_text):
    """Convert markdown report to HTML email with inline styles."""
    lines = md_text.split("\n")
    body_parts = []
    in_list = False
    in_blockquote = False

    for line in lines:
        # Close open elements
        if in_list and not line.startswith("- "):
            body_parts.append("</ul>")
            in_list = False
        if in_blockquote and not line.startswith("> "):
            body_parts.append("</blockquote>")
            in_blockquote = False

        stripped = line.strip()

        if stripped == "---":
            body_parts.append('<hr style="border:none;border-top:1px solid #dee2e6;margin:1.5em 0">')
            continue

        if stripped.startswith("### "):
            text = _inline(stripped[4:])
            color = "#dc3545" if "URGENT" in text else "#fd7e14" if "HIGH" in text else "#0d6efd"
            body_parts.append(f'<h3 style="font-size:1em;margin:1.2em 0 0.4em;padding:0.4em 0.6em;'
                            f'border-left:4px solid {color};background:#f8f9fa">{text}</h3>')
            continue

        if stripped.startswith("## "):
            text = _inline(stripped[3:])
            body_parts.append(f'<h2 style="font-size:1.2em;margin:1.5em 0 0.5em;color:#343a40">{text}</h2>')
            continue

        if stripped.startswith("# "):
            text = _inline(stripped[2:])
            body_parts.append(f'<h1 style="font-size:1.4em;margin:0 0 0.5em;color:#1a1a2e">{text}</h1>')
            continue

        if stripped.startswith("- "):
            if not in_list:
                body_parts.append('<ul style="margin:0.5em 0 0.5em 1.5em">')
                in_list = True
            body_parts.append(f"<li>{_inline(stripped[2:])}</li>")
            continue

        if stripped.startswith("> "):
            if not in_blockquote:
                body_parts.append('<blockquote style="border-left:3px solid #dee2e6;padding:0.5em 1em;'
                                'margin:0.5em 0;background:#f8f9fa;color:#495057;font-size:0.9em">')
                in_blockquote = True
            body_parts.append(f"<p>{_inline(stripped[2:])}</p>")
            continue

        if stripped == "":
            continue

        body_parts.append(f"<p style=\"margin:0.4em 0\">{_inline(stripped)}</p>")

    if in_list:
        body_parts.append("</ul>")
    if in_blockquote:
        body_parts.append("</blockquote>")

    body = "\n".join(body_parts)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
line-height:1.6;color:#1a1a2e;max-width:700px;margin:0 auto;padding:1em">
{body}
</body>
</html>"""


def _inline(text):
    """Process inline markdown: bold and links."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color:#0d6efd">\1</a>', text)
    return text


if __name__ == "__main__":
    md = sys.stdin.read()
    print(markdown_to_html(md))
