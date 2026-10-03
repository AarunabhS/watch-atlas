"""Optional curl transport with normal dual-stack connection handling.

The Client still controls host scope, robots, redirects, pacing and blocks.
Curl uses exactly the headers supplied by Client, with no browser impersonation.
"""
import subprocess
import tempfile
from email.parser import Parser
from pathlib import Path

from .client import MAX_BYTES, FetchError


class CurlTransport:
    def request(self, url, headers):
        with tempfile.TemporaryDirectory(prefix='watch-atlas-http-') as folder:
            folder = Path(folder)
            head, body = folder / 'headers', folder / 'body'
            command = ['curl', '--silent', '--show-error', '--max-time', '30',
                       '--max-filesize', str(MAX_BYTES), '--compressed', '--proto', '=https',
                       '--dump-header', str(head), '--output', str(body), '--write-out', '%{http_code}']
            for key, value in headers.items():
                command.extend(['--header', key + ': ' + value])
            command.append(url)
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=35)
            except subprocess.TimeoutExpired as e:
                raise TimeoutError('curl process exceeded its timeout') from e
            if result.returncode:
                raise OSError('curl: ' + result.stderr.strip())
            payload = body.read_bytes()
            if len(payload) > MAX_BYTES:
                raise FetchError('Response exceeds 16 MiB limit')
            # A proxy CONNECT response or an interim 100 may precede the real
            # response. Curl does not follow redirects; Client checks them.
            blocks = [x for x in head.read_text(encoding='iso-8859-1').split('\n\n') if x.startswith('HTTP/')]
            if not blocks:
                raise FetchError('curl returned no HTTP response headers')
            parsed = Parser().parsestr('\n'.join(blocks[-1].splitlines()[1:]))
            response_headers = {key.lower(): value for key, value in parsed.items()}
            return int(result.stdout), response_headers, payload
