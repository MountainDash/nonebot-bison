import sys, re, html, os, subprocess, hashlib
def text(h):
    h = re.sub(r'(?is)<(script|style|noscript|svg|head|nav|footer)[^>]*>.*?</\1>', ' ', h)
    h = re.sub(r'(?is)<!--.*?-->', ' ', h)
    h = re.sub(r'(?i)</(p|div|li|tr|h[1-6]|pre|blockquote|table|dt|dd|section|article)>', '\n', h)
    h = re.sub(r'(?i)<br\s*/?>', '\n', h)
    h = re.sub(r'(?i)<(li|tr)[^>]*>', '\n* ', h)
    h = re.sub(r'(?i)<(h[1-6])[^>]*>', '\n\n### ', h)
    h = re.sub(r'(?i)<(td|th)[^>]*>', ' | ', h)
    h = re.sub(r'(?s)<[^>]+>', ' ', h)
    h = html.unescape(h)
    h = re.sub(r'[ \t\xa0]+', ' ', h)
    out=[]
    for l in h.split('\n'):
        l=l.strip()
        if l: out.append(l)
    return '\n'.join(out)
os.makedirs('raw',exist_ok=True); os.makedirs('txt',exist_ok=True)
for pair in sys.argv[1:]:
    slug, url = pair.split('=',1)
    c=f'raw/{slug}.html'; t=f'txt/{slug}.txt'
    try:
        if not os.path.exists(c) or os.path.getsize(c)<400:
            subprocess.run(['curl','-sSL','-m','45','-A','Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36','-H','Accept-Language: en-US,en;q=0.9',url,'-o',c],check=True)
        open(t,'w').write(text(open(c,encoding='utf-8',errors='replace').read()))
        print(f'{slug}: {os.path.getsize(t)} chars txt')
    except Exception as e:
        print(f'{slug}: FAIL {e}')
