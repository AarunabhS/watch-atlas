"""Offline tests. Fixtures are invented and are not watchmaker catalog data."""
import csv
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from watch_atlas_scraper.adapters import ADAPTERS
from watch_atlas_scraper.client import Client, FetchError, HostBlocked
from watch_atlas_scraper.discovery import sitemap_links
from watch_atlas_scraper.export import export_records
from watch_atlas_scraper.policy import Policy, PermissionDenied
from watch_atlas_scraper.robots import Robots
from watch_atlas_scraper.runner import run
from watch_atlas_scraper.schema import COLUMNS, Record
from watch_atlas_scraper.state import State

URL = 'https://www.tudorwatch.com/en/watches/test-family/m12345-0001'
OTHER = 'https://www.tudorwatch.com/en/watches/test-family/m12345-0002'


class AllowPolicy:
    def require(self, *args):
        return {'evidence':'synthetic test permission'}


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, url, headers):
        self.calls.append((url, headers))
        if not self.responses:
            raise AssertionError('Unexpected network request')
        return self.responses.pop(0)


class RobotsTests(unittest.TestCase):
    def test_longest_rule_and_allow_tie(self):
        r = Robots('User-agent: *\nDisallow: /en\nAllow: /en/watches\nDisallow: /same\nAllow: /same')
        self.assertTrue(r.allowed(URL))
        self.assertFalse(r.allowed('https://x/en/account'))
        self.assertTrue(r.allowed('https://x/same'))

    def test_wildcard_and_end_anchor(self):
        r = Robots('User-agent: *\nDisallow: /*?*filters=\nDisallow: /*.pdf$')
        self.assertFalse(r.allowed('https://x/en?a=1&filters=test'))
        self.assertFalse(r.allowed('https://x/manual.pdf'))
        self.assertTrue(r.allowed('https://x/manual.pdf.html'))

    def test_merge_repeated_wildcard_groups(self):
        r = Robots('User-agent: *\nAllow: /\nUser-agent: Other\nDisallow: /\nUser-agent: *\nDisallow: /private')
        self.assertFalse(r.allowed('https://x/private'))
        self.assertTrue(r.allowed('https://x/watches'))

    def test_specific_agent_excludes_wildcard(self):
        r = Robots('User-agent: *\nDisallow: /\nUser-agent: WatchAtlasCatalogBot\nAllow: /')
        self.assertTrue(r.allowed(URL))

    def test_tudor_non_slash_wildcard(self):
        r = Robots('User-agent: *\nDisallow: *?q=\nDisallow: */search')
        self.assertFalse(r.allowed('https://x/en?q=watch'))
        self.assertFalse(r.allowed('https://x/en/search'))

    def test_unreserved_encoded_and_unicode(self):
        r = Robots('User-agent: *\nDisallow: /%77atches\nDisallow: /café')
        self.assertFalse(r.allowed('https://x/watches'))
        self.assertFalse(r.allowed('https://x/caf%C3%A9'))

    def test_content_signals_and_delay(self):
        r = Robots('User-agent: *\nCrawl-delay: 8\nContent-Signal: search=yes, ai-input=no\nSitemap: https://x/map.xml')
        self.assertEqual(r.delay, 8)
        self.assertEqual(r.signals['ai-input'], 'no')
        self.assertEqual(r.sitemaps, ['https://x/map.xml'])


class PolicyTests(unittest.TestCase):
    def test_all_six_blocked_by_default(self):
        for brand, adapter in ADAPTERS.items():
            with self.subTest(brand=brand), self.assertRaises(PermissionDenied):
                Policy().require(brand, adapter.seeds[0])

    def test_scope_boundary_and_separate_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'grants.json'
            path.write_text(json.dumps({'tudor':{'collection':True, 'reuse':False, 'evidence':'fictional fixture', 'valid_until':'2099-01-01', 'url_prefixes':['https://www.tudorwatch.com/en/watches']}}))
            policy = Policy(path)
            policy.require('tudor', URL)
            for url in ('https://www.tudorwatch.com/en/watches-evil/x', 'https://www.tudorwatch.com.evil/en/watches/a'):
                with self.assertRaises(PermissionDenied):
                    policy.require('tudor', url)
            with self.assertRaises(PermissionDenied):
                policy.require('tudor', URL, 'reuse')

    def test_expired_grant(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'grants.json'
            path.write_text(json.dumps({'tudor':{'collection':True, 'evidence':'fixture', 'valid_until':'2000-01-01', 'url_prefixes':['https://www.tudorwatch.com/']}}))
            with self.assertRaises(PermissionDenied):
                Policy(path).require('tudor', URL)


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = State(self.tmp.name)

    def tearDown(self):
        self.state.close()
        self.tmp.cleanup()

    def client(self, responses, policy=None, **kwargs):
        transport = FakeTransport(responses)
        client = Client('tudor', ADAPTERS['tudor'], policy or AllowPolicy(), self.state, transport=transport, sleep=lambda _:None, **kwargs)
        return client, transport

    def test_permission_gate_precedes_every_request(self):
        c, t = self.client([], Policy())
        with self.assertRaises(PermissionDenied):
            c.get(URL)
        self.assertEqual(t.calls, [])

    def test_robots_precedes_product_and_cache(self):
        c, t = self.client([(200, {}, b'User-agent: *\nAllow: /'), (200, {'etag':'"v1"'}, b'<main>test</main>')])
        first = c.get(URL)
        second = c.get(URL)
        self.assertEqual(len(t.calls), 2)
        self.assertTrue(t.calls[0][0].endswith('/robots.txt'))
        self.assertEqual(first, second)

    def test_403_opens_persistent_circuit(self):
        c, t = self.client([(403, {}, b'<title>Access Denied</title>')])
        with self.assertRaises(HostBlocked):
            c.get(URL)
        with self.assertRaises(HostBlocked):
            c.get(OTHER)
        self.assertEqual(len(t.calls), 1)
        self.assertIsNotNone(self.state.blocked('www.tudorwatch.com'))

    def test_429_stops_without_immediate_retry(self):
        c, t = self.client([(200, {}, b'User-agent: *\nAllow: /'), (429, {'retry-after':'600'}, b'')])
        with self.assertRaises(HostBlocked):
            c.get(URL)
        self.assertEqual(len(t.calls), 2)
        row = self.state.db.execute('SELECT until FROM circuits').fetchone()
        self.assertGreater(row[0], time.time() + 590)

    def test_200_challenge_is_not_a_watch(self):
        c, t = self.client([(200, {}, b'User-agent: *\nAllow: /'), (200, {}, b'<title>Just a moment...</title><div>Verify you are human</div>')])
        with self.assertRaises(HostBlocked):
            c.get(URL)
        self.assertEqual(len(t.calls), 2)

    def test_robots_denied_never_requests_product(self):
        c, t = self.client([(200, {}, b'User-agent: *\nDisallow: /en/watches')])
        with self.assertRaises(PermissionDenied):
            c.get(URL)
        self.assertEqual(len(t.calls), 1)

    def test_unknown_robots_is_fail_closed(self):
        c, t = self.client([(404, {}, b'not found')])
        with self.assertRaises(FetchError):
            c.get(URL)
        self.assertEqual(len(t.calls), 1)

    def test_redirect_cannot_escape_official_host(self):
        c, t = self.client([(200, {}, b'User-agent: *\nAllow: /'), (302, {'location':'https://evil.invalid/watches'}, b'')])
        with self.assertRaises(PermissionDenied):
            c.get(URL)
        self.assertEqual(len(t.calls), 2)

    def test_redirect_checks_new_path_rules(self):
        c, t = self.client([(200, {}, b'User-agent: *\nDisallow: /private'), (302, {'location':'/private'}, b'')])
        with self.assertRaises(PermissionDenied):
            c.get(URL)
        self.assertEqual(len(t.calls), 2)

    def test_conditional_revalidation(self):
        c, t = self.client([(200, {}, b'User-agent: *\nAllow: /'), (200, {'etag':'"v1"'}, b'<main>one</main>'), (304, {}, b'')], cache_ttl=0)
        first = c.get(URL)
        second = c.get(URL)
        self.assertEqual(first[1], second[1])
        self.assertEqual(t.calls[-1][1]['If-None-Match'], '"v1"')

    def test_transient_errors_have_bounded_retry(self):
        c, t = self.client([(200, {}, b'User-agent: *\nAllow: /'), (503, {}, b''), (503, {}, b''), (503, {}, b'')])
        with self.assertRaises(FetchError):
            c.get(URL)
        self.assertEqual(len(t.calls), 4)


class ParsingTests(unittest.TestCase):
    def test_current_product_not_related_watch(self):
        schema = [{'@type':'Product', 'url':OTHER, 'sku':'12345-0002', 'name':'Other variant', 'offers':{'price':99,'priceCurrency':'USD'}}, {'@type':'Product','url':URL,'sku':'12345-0001','name':'Fixture watch','offers':{'price':0,'priceCurrency':'CHF'}, 'additionalProperty':[{'name':'Diameter','value':'39 mm'}]}]
        body = ('<main><h1>Fixture watch</h1></main><script type="application/ld+json">' + json.dumps(schema) + '</script>').encode()
        r = ADAPTERS['tudor'].parse(body, URL)
        self.assertEqual(r['reference_number'], '12345-0001')
        self.assertEqual(r['price'], '0')
        self.assertEqual(r['currency'], 'CHF')
        self.assertEqual(r['diameter'], '39 mm')

    def test_related_schema_never_supplies_current_specs(self):
        schema = {'@type':'Product','url':OTHER,'sku':'12345-0002','name':'Other watch','offers':{'price':99,'priceCurrency':'USD'}}
        body = ('<main><h1>Current fixture</h1></main><script type="application/ld+json">' + json.dumps(schema) + '</script>').encode()
        r = ADAPTERS['tudor'].parse(body, URL)
        self.assertEqual(r['price'], '')
        self.assertEqual(r['currency'], '')
        self.assertEqual(r['specific_model'], 'Current fixture')

    def test_explicit_case_measurements_preserved(self):
        body = b'<main><h1>Fixture</h1><h3>Case</h3><p>39mm stainless steel case with polished finish. Lugs: 21mm lug width. Case thickness: 12.0mm</p><h3>Movement</h3><p>Manufacture Calibre MT0000; Self-winding movement</p><dl><dt>Rare measurement</dt><dd>42 test units</dd></dl></main>'
        r = ADAPTERS['tudor'].parse(body, URL)
        self.assertEqual((r['diameter'], r['between_lugs'], r['case_thickness']), ('39 mm', '21 mm', '12.0 mm'))
        self.assertEqual(r['caliber'], 'MT0000')
        self.assertEqual(r['raw_specifications']['Rare measurement'], ['42 test units'])
        self.assertIn('diameter', r['provenance'])
        self.assertEqual(r['made_in'], '')

    def test_missing_remains_missing(self):
        r = ADAPTERS['tudor'].parse(b'<main><h1>Fixture</h1></main>', URL)
        self.assertEqual(r['power_reserve'], '')
        self.assertIn('power_reserve', r['missing_core_fields'])
        self.assertTrue(r['extraction_warnings'])

    def test_ids_do_not_merge_variants_or_markets(self):
        a = Record('Tudor', URL, 'US', 'en')
        a.set('reference_number', '12345-0001', 'fixture')
        b = Record('Tudor', OTHER, 'US', 'en')
        b.set('reference_number', '12345-0002', 'fixture')
        c = Record('Tudor', URL, 'IN', 'en')
        c.set('reference_number', '12345-0001', 'fixture')
        self.assertEqual(len({x.finalize()['id'] for x in (a,b,c)}), 3)

    def test_patek_navigation_not_current_product(self):
        url = 'https://www.patek.com/en/collection/calatrava/9999G-001'
        embedded = {'navigation':{'name':'Wrong watch','referenceNumber':'8888R-002','url':'/en/collection/calatrava/8888R-002'}, 'product':{'name':'Fixture Calatrava','referenceNumber':'9999G-001','url':url,'technicalSpecifications':[{'name':'Power reserve','value':'48 h'}]}}
        body = ('<main><h1>Fixture Calatrava</h1></main><script type="application/json" id="__NEXT_DATA__">' + json.dumps(embedded) + '</script>').encode()
        r = ADAPTERS['patek'].parse(body, url)
        self.assertEqual(r['reference_number'], '9999G-001')
        self.assertEqual(r['power_reserve'], '48 h')

    def test_all_adapter_url_templates(self):
        urls = {
            'breitling':'https://www.breitling.com/us-en/watches/navitimer/test/AB0000000001/',
            'patek':'https://www.patek.com/en/collection/calatrava/9999G-001',
            'jaeger_lecoultre':'https://www.jaeger-lecoultre.com/us-en/watches/reverso/test-q1234567',
            'omega':'https://www.omegawatches.com/en-us/watch-omega-fixture-12345678901001',
            'tudor':URL,
            'iwc':'https://www.iwc.com/us/en/watch-collections/pilot-watches/iw123456-test.html',
        }
        for key, url in urls.items():
            with self.subTest(key=key):
                adapter = ADAPTERS[key]
                self.assertEqual(adapter.classify(url), 'product')
                r = adapter.parse(b'<main><h1>Invented fixture watch</h1><dl><dt>Water resistance</dt><dd>100 test metres</dd></dl></main>', url)
                self.assertTrue(r['reference_number'])
                self.assertEqual(r['water_resistance'], '100 test metres')
                self.assertEqual(adapter.classify(url + '?filters=x'), None)


class DiscoveryTests(unittest.TestCase):
    def test_sitemap_ignores_image_locs(self):
        body = b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"><url><loc>https://x/watch</loc><image:image><image:loc>https://x/photo</image:loc></image:image></url></urlset>'
        self.assertEqual(sitemap_links(body), ('urlset', ['https://x/watch']))

    def test_xml_external_entities_not_resolved(self):
        body = b'<!DOCTYPE urlset [<!ENTITY secret SYSTEM "file:///etc/passwd">]><urlset><url><loc>&secret;</loc></url></urlset>'
        self.assertEqual(sitemap_links(body), ('urlset', []))

    def test_link_discovery_uses_official_paths_only(self):
        body = f'<main><a href="{OTHER}">Watch</a><a href="https://evil.invalid/en/watches/x/m12345-0001">External</a><a href="/en/search?q=a">Search</a></main>'.encode()
        self.assertEqual(ADAPTERS['tudor'].links(body, URL), [OTHER])


class PipelineTests(unittest.TestCase):
    def test_authorized_fixture_catalog_end_to_end_and_resume(self):
        adapter = ADAPTERS['tudor']
        schema = {'@type':'Product','url':URL,'sku':'12345-0001','name':'Invented fixture watch'}
        body = ('<main><h1>Invented fixture watch</h1><dl><dt>Diameter</dt><dd>39 mm</dd></dl></main><script type="application/ld+json">' + json.dumps(schema) + '</script>').encode()
        map_url = adapter.origin + '/map.xml'
        class FixtureClient:
            calls = []
            def __init__(self, *args):
                pass
            def ensure_robots(self, url):
                return Robots('User-agent: *\nAllow: /\nSitemap: ' + map_url)
            def get(self, url):
                self.calls.append(url)
                if url == map_url:
                    data = f'<urlset><url><loc>{URL}</loc></url><url><loc>{OTHER}?q=ignored</loc></url></urlset>'.encode()
                elif url == URL:
                    data = body
                else:
                    data = b'<main><h1>Fixture collection</h1></main>'
                return {'url':url, 'sha256':'fixturehash', 'fetched_at':'2000-01-01T00:00:00Z'}, data
        with tempfile.TemporaryDirectory() as folder:
            grants = Path(folder) / 'grants.json'
            grants.write_text(json.dumps({'tudor':{'collection':True,'reuse':True,'evidence':'INVENTED TEST PERMISSION','valid_until':'2099-01-01','url_prefixes':[adapter.origin + '/']}}))
            with patch('watch_atlas_scraper.runner.Client', FixtureClient):
                first = run(folder, ['tudor'], grants)
                second = run(folder, ['tudor'], grants)
            self.assertEqual(first['export']['accepted'], 1)
            self.assertEqual(second['stored_product_records'], 1)
            self.assertEqual(FixtureClient.calls.count(URL), 1)
            self.assertEqual(first['brands'][0]['queue'], {'done':3})
            self.assertFalse(first['complete'])
            row = json.loads((Path(folder) / 'exports/watches.jsonl').read_text())
            self.assertEqual(row['diameter'], '39 mm')
            self.assertEqual(row['source_hash'], 'fixturehash')

    def test_first_run_all_permissions_denied_no_network(self):
        with tempfile.TemporaryDirectory() as folder, patch('watch_atlas_scraper.runner.Client') as client:
            result = run(folder, list(ADAPTERS))
            client.assert_not_called()
            self.assertEqual(len(result['brands']), 6)
            self.assertEqual(result['stored_product_records'], 0)
            self.assertEqual(result['export']['accepted'], 0)
            self.assertTrue(all(x['status'] == 'permission_required' for x in result['brands']))
            with open(Path(folder) / 'exports/watches.csv') as f:
                self.assertEqual(next(csv.reader(f)), COLUMNS)

    def test_queue_resume_and_snapshot_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            state = State(folder)
            state.enqueue('tudor', URL, 'product')
            state.enqueue('tudor', OTHER, 'product')
            state.finish('tudor', URL)
            meta = state.save_response(URL, {'status':200}, b'fixture')
            state.close()
            state = State(folder)
            self.assertEqual(state.pending('tudor')['url'], OTHER)
            self.assertEqual(state.cached(URL)[1], b'fixture')
            self.assertTrue(meta['sha256'])
            state.close()

    def test_export_quarantines_missing_identity_and_unlicensed_reuse(self):
        r = ADAPTERS['tudor'].parse(b'<main><h1>Fixture watch</h1></main>', URL)
        with tempfile.TemporaryDirectory() as folder:
            result = export_records([r], folder, Policy(), ADAPTERS)
            self.assertEqual(result['accepted'], 0)
            self.assertEqual(result['quarantined'], 1)
            self.assertIn('restricted', json.loads((Path(folder) / 'quarantine.json').read_text())[0]['errors'][-1])
        r['reference_number'] = ''
        with tempfile.TemporaryDirectory() as folder:
            result = export_records([r], folder, AllowPolicy(), ADAPTERS)
            self.assertEqual(result['quarantined'], 1)


if __name__ == '__main__':
    unittest.main()
