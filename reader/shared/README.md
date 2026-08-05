# shared/

What both halves of aligned.click use: the chat at `aligned.click` (served by
the proxy from `public/`) and the reader at `read.aligned.click` (this
directory, deployed to GitHub Pages).

It lives inside `reader/` because Pages publishes exactly one tree and the
reader cannot reach outside it. The proxy serves these same files at the same
`/shared/…` URLs, so both pages ask for one path and neither knows the other's
hosting.

## The vendored libraries

Fetched from jsdelivr on 2026-08-05 and committed, not linked. They had been
loaded from the CDN at **unpinned** URLs on pages that can post, publish and
redact as whoever is logged in — so whatever the CDN served on a given load ran
with those powers. A CSP now blocks script from anywhere but the origin, in a
header from the proxy and a `<meta>` on Pages.

| file | version | sha384 |
|---|---|---|
| `marked.min.js` | 15.0.12 | `948ahk4ZmxYVYOc+rxN1H2gM1EJ2Duhp7uHtZ4WSLkV4Vtx5MUqnV+l7u9B+jFv+` |
| `purify.min.js` | DOMPurify 3.4.13 | `ZuC+DIACqSIZTsp+7YF57cR5Y+6qXa7YFbEKdA/EHA/R0T+41dtorqucYl71Zp+t` |
| `atproto-wc.js` | atproto-wc (browser bundle) | `2kQtPd+WOxLFU69idVRIdjfYJ3n0l4YgltS8pyTWlHUHua3g76DC9TQU+xmF9V54` |

To refresh one, download it, check the hash changed for a reason, and commit the
new file and the new hash together:

    curl -sS -o marked.min.js https://cdn.jsdelivr.net/npm/marked@15.0.12/marked.min.js
    openssl dgst -sha384 -binary marked.min.js | openssl base64 -A

## The rest

- `theme.css` — the colour tokens, and the redaction bar. One copy: two sites
  with their own copy of a colour is how they stop looking like one thing.
- `redact.js` — `paintRedactions(root, onBar)`, which turns runs of block
  characters into bars. Both sites draw them; only the chat makes them
  pressable, which is what `onBar` is for.
