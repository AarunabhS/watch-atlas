from .richemont import RichemontAdapter

ADAPTER = RichemontAdapter('iwc', 'IWC', 'https://www.iwc.com', 'en', 'US', ('/us/en/watches.html',), r'/us/en/watch-collections/[^/]+/iw\d{6}[^/]*\.html', (r'/us/en/watches\.html', r'/us/en/watch-collections/[^/]+\.html'))
