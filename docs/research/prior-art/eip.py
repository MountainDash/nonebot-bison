import sys, re, html, os, subprocess
def text(h):
    h = re.sub(r'(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>', ' ', h)
    h = re.sub(r'(?is)<!--.*?-->', ' ', h)
    h = re.sub(r'(?i)</(p|div|li|tr|h[1-6]|pre|blockquote|table|dt|dd)>', '\n', h)
    h = re.sub(r'(?i)<br\s*/?>', '\n', h)
    h = re.sub(r'(?i)<(li|tr)[^>]*>', '\n* ', h)
    h = re.sub(r'(?i)<(h[1-6])[^>]*>', '\n\n### ', h)
    h = re.sub(r'(?s)<[^>]+>', ' ', h)
    h = html.unescape(h)
    h = re.sub(r'[ \t\xa0]+', ' ', h)
    return '\n'.join(l.strip() for l in h.split('\n') if l.strip())
for p in sys.argv[1:]:
    c = f'raw/eip-{p}.html'
    if not os.path.exists(c):
        subprocess.run(['curl','-sSL','-m','40','-A','Mozilla/5.0',f'https://www.enterpriseintegrationpatterns.com/patterns/messaging/{p}.html','-o',c])
    t = text(open(c,encoding='utf-8',errors='replace').read())
    m = 'Contents ⇐ Prev Next ⇒'
    i = t.find(m)
    if i>=0: t = t[i+len(m):]
    j = t.find('Related patterns:')
    body = t[:j] if j>0 else t
    print(f'\n===== {p} ({len(body)} chars)\n{body}')
