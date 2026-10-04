# Watch image viewer

Open a watch from Watch Finder, the catalog, overview, or comparison, then choose **Enlarge image** in its details. The full-screen viewer supports wheel zoom, drag-to-pan, pinch zoom, double-tap/double-click zoom, plus/minus buttons, and **Fit image**. Keyboard controls: `+`/`-` to zoom, arrow keys to pan, `0` or `Home` to fit, and `Escape` to return to the watch details. Focus returns to the image button; the underlying page stays still while viewing.

No image assets or gallery downloads are stored in Git. Catalog cards continue using their existing small URLs. Larger images are fetched when the viewer opens, using verified variants of the exact source image. The source link displays the actual loaded pixel dimensions. Failed or timed-out larger requests leave the existing image visible; a failed base image provides a source link and disables zoom.

## Larger source images

| Watchmaker | Existing source | Viewer source | Verified sample dimensions |
| --- | --- | --- | --- |
| Breguet | `im=Resize,height=752` (or smaller height) | `im=Resize,height=2400` | 526 × 752 → 1,680 × 2,400 |
| Omega | `w=230` (or smaller width) | `w=2000` | 230 × 230 → 2,000 × 2,000 |
| IWC | `product-card-3` or `product-slideshow-1` | `product-slideshow-2xl-1/o-dpr-2` | 376 × 365 → 1,854 × 2,140 |
| Jaeger-LeCoultre | `product-grid-hero-4` or `product-card-3` | `product-grid-hero-xl-4/o-dpr-2` | 400 × 400 → 1,700 × 1,700 |

Verified on 5 October 2026. IWC's larger slideshow presets and Jaeger-LeCoultre's larger hero presets are present in the locally preserved official product pages. Preset changes retain the exact 40-character asset hash, image extension, and query parameters. Omega and Breguet retain the exact image path and other query parameters. Rules accept only the precise official hosts and supported image paths; other watchmakers keep their original URLs.

Before displaying a candidate, the browser checks that it decodes and is larger in both dimensions. Omega/Breguet resize variants must retain their aspect ratio within 2%. IWC/JLC presets have different canvas padding, so their aspect ratio may change while preserving the asset hash. Applying the aspect-ratio restriction to IWC would incorrectly reject its genuine larger image. Candidate URLs must exactly match the expected larger URL; a different asset is never substituted.

The verified Breguet variant is 2,751,139 bytes versus 7,478,335 bytes for its unresized original. IWC's sample larger PNG is 859,736 bytes; JLC's is 213,695 bytes. Direct Omega requests timed out, but normal Chrome image loading verified the 2,000-pixel version and the viewer was checked in the in-app browser. All 555 nonempty Omega image URLs, 225 IWC URLs, and 197 JLC URLs match the respective upgrade rules. No alternate angles are added in this stage. Zoom beyond the source resolution can still show pixels.

Implementation: `dist/image-viewer.js` and `dist/image-viewer.css`, with watch-detail integration in `dist/app.js` and versioned assets in `dist/index.html`. The module initializes the dialog lazily, bounds panning to image edges, caps zoom at 600%, cancels outstanding loads when closing, and prevents stale loads from replacing another watch.

## Validation

Run the existing suite with `node --test tests/*.test.cjs tests/*.test.mjs` and `node tools/validate_catalog.cjs`. Image geometry and source-selection checks are in `tests/image-viewer.test.cjs`.

For browser QA, start `ATLAS_PREVIEW_PORT=8790 node tools/preview-price-backend.mjs`, then run `node tools/verify-image-viewer.cjs http://127.0.0.1:8790/`. Set `ATLAS_PLAYWRIGHT` and `ATLAS_CHROMIUM` if the packages/browser are installed outside their defaults. The browser checks use explicitly synthetic watch fixtures to isolate gestures, HQ loading on demand, failure fallback, stale requests, missing images, focus restoration, Escape, and viewport overflow. PNGs go into the system temporary directory under `watch-atlas-viewer-qa` (override with `ATLAS_VIEWER_REPORTS`), outside Git. Visual validation with the real verified Breguet image is separate from fixture-based behavior checks.

Completed checks: desktop and mobile Chrome behavior checks passed, including real touch pinch and double-tap input. Real Breguet images rendered at 1,680 × 2,400 on both viewport sizes; fit and zoom screenshots were inspected. Catalog validation retained 3,636 watches, eleven watchmakers, and 73 archive files.

The larger-image update passed all 87 current tests and catalog validation. In-app browser checks confirmed loaded dimensions and visually inspected zoom for IWC Aquatimer IW328801, IWC Ingenieur IW345901 (alternate slideshow source), JLC Calibre 101 Q2872201, JLC Duometre Q603H480 (alternate card source), Omega Constellation 131.10.25.60.02.002, and Omega Seamaster 210.20.42.20.01.001. Proof screenshots are kept outside the repository in the temporary QA directory.
