# Acne Medicine YouTube automation

Cloudflare Worker: `acne-youtube-automation`

Production URL: https://acne-youtube-automation.ramatladi-mphela.workers.dev

Expected channel: `UCtwhnWNVzoS6MR0SkvZIDHQ` (Acne Medicine Johannesburg).

## Google connection

Create a **Web application** OAuth client in the existing `globalnewsflix-video` project. Preserve the existing Web and Desktop clients. Register this exact redirect URI:

`https://acne-youtube-automation.ramatladi-mphela.workers.dev/oauth/callback`

Use the private administrator link supplied to the owner, select the Web client JSON on the setup page, then choose Connect YouTube. The Desktop JSON is deliberately rejected. Google consent must be completed as the owner of Acne Medicine Johannesburg. Connection is saved only after the Google API returns exactly the expected channel ID and both requested scopes.

The hosted Web client and Google consent are still required. Deployment does not mean the YouTube channel is connected.

## Architecture

- D1 `acne-youtube-automation` stores encrypted OAuth configuration and refresh token, expiring single-use state and durable job records.
- R2 `acne-youtube-media` stores MP4 files privately; there is no public media route.
- Worker secrets `VAULT_KEY` and `ADMIN_TOKEN` are configured remotely. Never commit either value or credential JSON.
- AES-GCM encrypts credentials and resumable-upload session URLs at application level.
- Administrator session cookies are encrypted, HttpOnly, Secure, SameSite=Lax and expire in 24 hours. The private access-link key is exchanged through POST, then removed from browser history.
- Google consent uses PKCE, an owner-session binding, an expiry, and an atomic one-time state consume. Full query strings are redacted from Cloudflare observability.
- Mutation routes check same-origin requests. Credentials and tokens are never returned by the status API.
- Cron runs every five minutes. It does nothing until a channel token is present and validated. A verified unlisted connection test is required before product posts.

## Publishing

Queue only approved MP4 content up to 90 MB. One due upload is claimed atomically per run. Jobs have unique IDs and unique media keys. Channel identity is revalidated before every run.

An interrupted upload goes to NEEDS_REVIEW and is never automatically uploaded again. Review YouTube Studio before recovery. Successful upload responses persist their video ID; later runs verify channel, processing, visibility and paid-promotion settings. Media is retained privately; no automated deletion is configured.

The UI can load the first post's prepared metadata and commission disclosure. Select Claude's disclosed `amj001.mp4` to upload that media. This service automates the publication of supplied videos, not the generation of new review content. The legacy GitHub uploader is not modified and must not be separately queued for the same post.

## Tests and deployment

`node --test acnemedicine/cloudflare/test.mjs`

Source is a dependency-free ES module deployed through the Cloudflare integration using multipart upload. Bindings:

- `DB`: D1 database ID `f06ae47f-8028-4981-ae7f-592844811c4a`
- `MEDIA`: R2 bucket `acne-youtube-media`
- `VAULT_KEY`, `ADMIN_TOKEN`: Worker secret bindings; preserve on redeployment

Compatibility date is `2026-11-04` because Cloudflare's UTC date had not advanced to 5 November during deployment. Observability is enabled with query-string redaction and invocation logging disabled. Never replace Worker secrets during a routine code deployment: changing the encryption key makes existing credentials unreadable.

Remaining end-to-end validation: Web client setup, real Google consent, test upload and paid-promotion read-back. No successful public upload is claimed before these checks pass.
