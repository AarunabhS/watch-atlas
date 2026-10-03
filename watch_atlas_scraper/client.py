import gzip
import io
import json
import random
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit

from .policy import PermissionDenied
from .robots import Robots

USER_AGENT = 'WatchAtlasCatalogBot/1.0 (+https://github.com/AarunabhS/watch-atlas)'
TOKEN = 'WatchAtlasCatalogBot'
MAX_BYTES = 16 * 1024 * 1024


class FetchError(RuntimeError):
    pass


class HostBlocked(FetchError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Transport:
    def __init__(self):
        self.opener = urllib.request.build_opener(NoRedirect)

    def request(self, url, headers):
        req = urllib.request.Request(url, headers=headers)
        try:
            res = self.opener.open(req, timeout=30)
        except urllib.error.HTTPError as e:
            res = e
        with res:
            body = res.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise FetchError('Response exceeds 16 MiB limit')
            headers = {k.lower(): v for k, v in res.headers.items()}
            if headers.get('content-encoding', '').lower() == 'gzip':
                with gzip.GzipFile(fileobj=io.BytesIO(body)) as stream:
                    body = stream.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    raise FetchError('Decompressed response exceeds 16 MiB limit')
            return res.code, headers, body


class Client:
    def __init__(self, brand, adapter, policy, state, delay=3, cache_ttl=86400, transport=None, sleep=time.sleep, clock=time.time):
        self.brand, self.adapter, self.policy, self.state = brand, adapter, policy, state
        self.delay, self.cache_ttl = max(3, delay), cache_ttl
        self.transport = transport or Transport()
        self.sleep, self.clock = sleep, clock
        self.rules, self.last = {}, {}

    def scope(self, url):
        p = urlsplit(url)
        if p.scheme != 'https' or p.hostname not in self.adapter.hosts or p.port not in (None, 443) or p.username or p.password:
            raise PermissionDenied('Only configured official HTTPS hosts are allowed')
        return p

    def _pace(self, host):
        delay = max(self.delay, self.rules[host].delay if host in self.rules else 0)
        remaining = self.last.get(host, 0) + delay - self.clock()
        if remaining > 0:
            self.sleep(remaining)
        self.last[host] = self.clock()

    def _fetch(self, url, robots_only=False):
        parsed = self.scope(url)
        host = parsed.hostname
        if reason := self.state.blocked(host):
            raise HostBlocked(reason)
        cached = self.state.cached(url)
        if cached and self.clock() - cached[0]['fetched_epoch'] < self.cache_ttl and cached[0]['status'] == 200:
            self.state.event('cache_hit', url, cached[0]['sha256'])
            return cached
        headers = {'User-Agent': USER_AGENT, 'Accept': 'text/html,application/xml,application/json,text/plain', 'Accept-Language': 'en', 'Accept-Encoding': 'gzip'}
        if cached and cached[0]['status'] == 200:
            h = cached[0]['headers']
            if h.get('etag'):
                headers['If-None-Match'] = h['etag']
            if h.get('last-modified'):
                headers['If-Modified-Since'] = h['last-modified']
        for attempt in range(3):
            self._pace(host)
            try:
                status, response_headers, body = self.transport.request(url, headers)
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                self.state.event('network_error', url, e)
                if attempt == 2:
                    raise FetchError(str(e)) from e
                self.sleep(2 ** (attempt + 1))
                continue
            self.state.event('http', url, status)
            if status in (301, 302, 303, 307, 308):
                target = urljoin(url, response_headers.get('location', ''))
                self.scope(target)
                if robots_only:
                    # A robots redirect is only accepted at the same audited origin.
                    if urlsplit(target).netloc != parsed.netloc or urlsplit(target).path != '/robots.txt':
                        raise FetchError('Robots redirect outside the audited robots location')
                else:
                    self.policy.require(self.brand, target)
                    self.ensure_robots(target)
                    if not self.rules[urlsplit(target).hostname].allowed(target):
                        raise PermissionDenied('Redirect target disallowed by robots')
                return ('redirect', target)
            if status == 304 and cached:
                meta = {**cached[0], 'fetched_epoch': self.clock(), 'revalidated_at': datetime.now(timezone.utc).isoformat()}
                return self.state.save_response(url, meta, cached[1]), cached[1]
            sample = body[:6000].decode('utf-8', errors='replace').lower()
            challenge = any(x in sample for x in ('<title>access denied', '<title>just a moment', 'cf-chl-', '<title>attention required', 'verify you are human', '<title>robot or human'))
            if status in (401, 403, 429, 451) or challenge:
                reason = f'HTTP {status}' + (' / bot challenge' if challenge else '')
                until = None
                if status == 429:
                    retry = response_headers.get('retry-after', '')
                    try:
                        until = self.clock() + max(60, float(retry))
                    except ValueError:
                        try:
                            until = max(self.clock() + 60, parsedate_to_datetime(retry).timestamp())
                        except (ValueError, TypeError):
                            until = self.clock() + 3600
                self.state.block(host, reason, until)
                self.state.event('circuit_open', url, reason)
                raise HostBlocked(reason)
            if status in (500, 502, 503, 504) and attempt < 2:
                self.sleep(2 ** (attempt + 1) + random.uniform(0, 0.5))
                continue
            # Store only cache-relevant, non-sensitive response headers.
            safe_headers = {k: v for k, v in response_headers.items() if k in ('content-type', 'etag', 'last-modified', 'retry-after', 'x-robots-tag')}
            meta = {'url':url, 'status':status, 'headers':safe_headers, 'fetched_epoch':self.clock(), 'fetched_at':datetime.now(timezone.utc).isoformat()}
            meta = self.state.save_response(url, meta, body)
            if status != 200:
                raise FetchError(f'HTTP {status}')
            return meta, body
        raise FetchError('Retry budget exhausted')

    def fetch_following(self, url, robots_only=False):
        seen = set()
        for _ in range(6):
            if url in seen:
                raise FetchError('Redirect loop')
            seen.add(url)
            result = self._fetch(url, robots_only)
            if result[0] == 'redirect':
                url = result[1]
            else:
                return result
        raise FetchError('Too many redirects')

    def ensure_robots(self, url):
        parsed = self.scope(url)
        if parsed.hostname not in self.rules:
            robots_url = f'{parsed.scheme}://{parsed.netloc}/robots.txt'
            meta, body = self.fetch_following(robots_url, robots_only=True)
            text = body.decode('utf-8-sig', errors='replace')
            if '<html' in text[:500].lower() or ('user-agent' not in text.lower() and 'sitemap:' not in text.lower()):
                raise FetchError('Robots unavailable or not a valid robots document; stopped')
            self.rules[parsed.hostname] = Robots(text, TOKEN)
        return self.rules[parsed.hostname]

    def get(self, url):
        self.scope(url)
        self.policy.require(self.brand, url)
        rules = self.ensure_robots(url)
        if not rules.allowed(url):
            self.state.event('robots_denied', url, 'Longest matching robots rule')
            raise PermissionDenied('Disallowed by robots.txt')
        return self.fetch_following(url)
