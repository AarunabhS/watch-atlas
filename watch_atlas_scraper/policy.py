import json
from datetime import date
from pathlib import Path


class PermissionDenied(RuntimeError):
    pass


class Policy:
    """Separate collection rights from reuse. No robots or CLI override grants rights."""

    def __init__(self, grants_path=None):
        self.review = json.loads(Path(__file__).with_name('policies.json').read_text())
        self.grants = json.loads(Path(grants_path).read_text()) if grants_path else {}

    def require(self, brand, url, purpose='collection'):
        entry = self.review['brands'][brand]
        if entry[purpose] == 'allowed':
            return entry
        grant = self.grants.get(brand, {})
        if grant.get(purpose) is not True or not grant.get('evidence'):
            raise PermissionDenied(entry['reason'])
        if not grant.get('valid_until') or date.fromisoformat(grant['valid_until']) < date.today():
            raise PermissionDenied('Written permission missing an expiry/review date or expired')
        prefixes = grant.get('url_prefixes', [])
        # Prefixes must terminate at a path boundary and identify an HTTPS origin.
        from urllib.parse import urlsplit
        target = urlsplit(url)
        allowed = False
        for prefix in prefixes:
            scope = urlsplit(prefix)
            if scope.scheme != 'https' or scope.netloc != target.netloc or scope.query or scope.fragment:
                continue
            if target.path == scope.path or target.path.startswith(scope.path.rstrip('/') + '/'):
                allowed = True
        if not allowed:
            raise PermissionDenied('URL outside the documented permission scope')
        return grant

    def summary(self):
        return self.review
