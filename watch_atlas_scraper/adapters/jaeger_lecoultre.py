from .richemont import RichemontAdapter

ADAPTER = RichemontAdapter('jaeger_lecoultre', 'Jaeger-LeCoultre', 'https://www.jaeger-lecoultre.com', 'en', 'US', ('/us-en/watches',), r'/us-en/watches/[^/]+/[^/]+-[qQa-zA-Z]?\d{6,}/?', (r'/us-en/watches/?', r'/us-en/watches/[a-z-]+/?'))
