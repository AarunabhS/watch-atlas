"""RFC 9309-style group matching, merging, wildcards and longest-rule precedence."""
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit


def normalize_octets(text):
    # Decode percent-encoded ASCII unreserved chars, preserve encoded delimiters.
    unreserved = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'
    text = re.sub(r'%([0-9a-fA-F]{2})', lambda m: chr(int(m[1], 16)) if chr(int(m[1], 16)) in unreserved else '%' + m[1].upper(), text)
    return ''.join(c if ord(c) < 128 else ''.join('%%%02X' % b for b in c.encode('utf-8')) for c in text)


@dataclass
class Group:
    agents: list = field(default_factory=list)
    rules: list = field(default_factory=list)
    delay: float = 0
    signals: dict = field(default_factory=dict)


class Robots:
    def __init__(self, text, product_token='WatchAtlasCatalogBot'):
        self.sitemaps = []
        groups, current, has_directive = [], None, False
        for raw in text.splitlines():
            line = raw.split('#', 1)[0].strip()
            if ':' not in line:
                continue
            key, value = (x.strip() for x in line.split(':', 1))
            key = key.lower()
            if key == 'sitemap':
                self.sitemaps.append(value)
                continue
            if key == 'user-agent':
                if current is None or has_directive:
                    current = Group()
                    groups.append(current)
                    has_directive = False
                current.agents.append(value.lower())
            elif current is not None:
                has_directive = True
                if key in ('allow', 'disallow') and value:
                    pattern = normalize_octets(value)
                    regex = re.escape(pattern).replace(r'\*', '.*')
                    if pattern.endswith('$'):
                        regex = regex[:-2] + '$'
                    specificity = len(re.sub(r'\*|\$$', '', pattern).encode())
                    current.rules.append((specificity, key == 'allow', re.compile('^' + regex)))
                elif key == 'crawl-delay':
                    try:
                        current.delay = max(0, float(value))
                    except ValueError:
                        pass
                elif key == 'content-signal':
                    for signal in value.split(','):
                        if '=' in signal:
                            k, v = signal.split('=', 1)
                            current.signals[k.strip()] = v.strip()
        token = product_token.lower()
        # Product-token matching is case-insensitive, exact, not UA substring spoofing.
        selected = [g for g in groups if token in g.agents]
        if not selected:
            selected = [g for g in groups if '*' in g.agents]
        self.rules = [r for g in selected for r in g.rules]
        self.delay = max((g.delay for g in selected), default=0)
        self.signals = {k: v for g in selected for k, v in g.signals.items()}

    def allowed(self, url):
        parsed = urlsplit(url)
        path = normalize_octets((parsed.path or '/') + ('?' + parsed.query if parsed.query else ''))
        matched = [(n, allow) for n, allow, regex in self.rules if regex.search(path)]
        return max(matched, default=(0, True))[1]
