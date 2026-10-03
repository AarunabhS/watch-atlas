import gzip
import io
from urllib.parse import urlsplit
from lxml import etree
from .client import FetchError, MAX_BYTES


def sitemap_links(body):
    if body.startswith(b'\x1f\x8b'):
        with gzip.GzipFile(fileobj=io.BytesIO(body)) as stream:
            body = stream.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise FetchError('Sitemap exceeds decompressed size limit')
    parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=False)
    root = etree.fromstring(body, parser)
    kind = etree.QName(root).localname
    if kind not in ('sitemapindex', 'urlset'):
        raise FetchError('Not a sitemap index or URL set')
    # Only page loc elements. Image/video/news namespaces are not page URLs.
    namespace = etree.QName(root).namespace
    prefix = '{' + namespace + '}' if namespace else ''
    parent = 'sitemap' if kind == 'sitemapindex' else 'url'
    return kind, [node.text.strip() for node in root.findall(f'{prefix}{parent}/{prefix}loc') if node.text]


def official_sitemap(adapter, url):
    p = urlsplit(url)
    return p.scheme == 'https' and p.hostname in adapter.hosts and not p.query and (p.path.endswith(('.xml', '.xml.gz')))
