import sys, re, subprocess, html, os
def text(h):
    h = re.sub(r'(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>', ' ', h)
    h = re.sub(r'(?is)<!--.*?-->', ' ', h)
    h = re.sub(r'(?i)</(p|div|li|tr|h[1-6]|pre|blockquote|table|dt|dd|section|article)>', '\n', h)
    h = re.sub(r'(?i)<br\s*/?>', '\n', h)
    h = re.sub(r'(?i)<(li|tr)[^>]*>', '\n- ', h)
    h = re.sub(r'(?i)<(h[1-6])[^>]*>', '\n\n## ', h)
    h = re.sub(r'(?s)<[^>]+>', ' ', h)
    h = html.unescape(h)
    h = re.sub(r'[ \t\xa0]+', ' ', h)
    h = re.sub(r'\n\s*\n\s*\n+', '\n\n', h)
    return '\n'.join(l.strip() for l in h.split('\n')).strip()

url, cache = sys.argv[1], sys.argv[2]
start = sys.argv[3] if len(sys.argv) > 3 else None
end = sys.argv[4] if len(sys.argv) > 4 else None
limit = int(sys.argv[5]) if len(sys.argv) > 5 else 9000
if not os.path.exists(cache) or os.path.getsize(cache) < 500:
    subprocess.run(['curl','-sSL','-m','40','-A','Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)','-H','Accept-Language: en-US,en;q=0.9', url,'-o',cache], check=True)
h = open(cache, encoding='utf-8', errors='replace').read()
t = text(h)
if start:
    i = t.find(start)
    if i >= 0: t = t[i:]
if end:
    j = t.find(end)
    if j > 0: t = t[:j]
print(t[:limit])
