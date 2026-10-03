# First catalog run — 2 October 2026

This is the historical initial run, before the user clarified that the immediate
task is local personal, non-commercial research. The subsequent Patek-specific
collection captured all 252 current watches; see [`patek_research.md`](patek_research.md).
The subsequent Breitling collection captured all 402 US catalog references;
see [`breitling_research.md`](breitling_research.md). The initial zero-record
result does not describe these later personal research runs.

**New watch records: 0. All six brands require permission for the intended
bulk collection and reuse on Watch Atlas.**

The user confirmed no watchmaker permission and instructed collection only
where permitted. Product crawling therefore stopped at the permission gate.
No watch product pages were requested by the new crawler and the published
archival catalog was not changed.

| Watchmaker | Direct robots audit | Collection/reuse decision | Official evidence |
| --- | --- | --- | --- |
| Breitling | HTTP 200; selected public paths allowed for this bot | Permission required for the intended Atlas use | [Terms, 3.1–3.2](https://www.breitling.com/us-en/terms-of-use/): personal/non-commercial use; public reproduction and display on another platform restricted. |
| Patek Philippe | HTTP 200; `/ErrorPages*` disallowed | Permission required for the intended Atlas use | [Website terms, section 1](https://www.patek.com/en/legal-notices/terms-and-conditions): personal/non-commercial license; copying, downloading and republication beyond it require written consent. |
| Jaeger-LeCoultre | HTTP 403 Access Denied; no further direct host requests | Permission required and direct access blocked | [Terms, Use of Materials](https://www.jaeger-lecoultre.com/us-en/terms-of-use): public reuse and communication on another platform restricted. |
| Omega | HTTP 200 for the identified catalog bot; several other agents are explicitly disallowed | Permission required | [Terms, 4.1–4.2](https://www.omegawatches.com/terms-of-use): data mining/robots excluded from the license; database incorporation/republication restricted. |
| Tudor | HTTP 200; search/wishlist/query routes disallowed | Permission required for the intended Atlas use | [Terms, Copyrights and Trademarks](https://www.tudorwatch.com/en/terms-of-use): copying/downloading and redistribution restricted without written agreement; exception for non-commercial hard-copy printing. |
| IWC | HTTP 403 Access Denied; no further direct host requests | Permission required and direct access blocked | [Current terms, sections 4 and 10](https://www.iwc.com/us-en/terms-and-legal/terms-of-use): automated access/copying requires written approval; public reuse restricted. |

The direct robots observations are local saved responses, not claims about
universal access from every region or client. Jaeger-LeCoultre and IWC were not
retried with spoofed headers, proxies or alternate hostnames. Access to their
terms through the research tool was used only to evaluate permissions.

Four successful robots responses do not grant the requested collection/reuse
rights. Breitling's content signals permit search and AI input and prohibit
AI training. Those signals do not establish a license for a wholesale product
database or full descriptions and images on another platform.

Patek's homepage was read to locate its legal notice and inspect its inert
Next.js/Sitecore payload. Its notice was then read before product discovery.
No product content was extracted from that page.

## Delivered

- Modular Python package with six separate brand profiles and shared extraction hooks.
- Exact 40-column AP/Bulgari export schema plus full JSON records, provenance,
  missing-field diagnostics, snapshots and quarantine.
- Permission scope gates, robots handling, pacing, caching, resumable SQLite
  queues, bounded retries and persistent host circuits.
- Machine-readable [permission report](site_permissions.json) with response hashes.
- [Installation, extension and authorized-run instructions](../docs/scraping.md).
- 35 passing offline tests, including a synthetic sitemap-to-export run and resume.

The product profiles are **provisional and not live validated**. No complete
current catalog has been collected, no brand feed has been obtained, and no
new data has been merged into `dist/data.json` or deployed.

The next catalog step requires a documented collection/reuse grant or an
approved feed. For an access-blocked host, the provider also needs to supply an
approved endpoint or access method. Permissions and current product templates
must then be checked for that source and market before catalog collection.
