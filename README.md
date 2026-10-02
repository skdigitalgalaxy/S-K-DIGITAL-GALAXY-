# S&K Digital Galaxy

A responsive business website with a small Python inquiry API for S&K Digital Galaxy. The API uses only the Python standard library.

## Run locally

Install Python 3.11 or newer, then run `python server.py` from this directory. Open `http://127.0.0.1:8000`. Do not open `index.html` directly; the contact form requires the same-origin API.

## Update business details

Edit the service descriptions, company overview, contact details, and business name directly in `index.html`. The header logo is in `assets/sk-digital-galaxy-logo.svg`.

## Email configuration

Set these environment variables in your local shell or hosting secret manager:

- `SMTP_USER`: the Gmail account used to send inquiries
- `SMTP_PASSWORD`: a Google App Password for that account (never commit it)
- `INQUIRY_TO`: destination inbox; defaults to `sandkdigitalgalaxy@gmail.com`
- `APP_ORIGIN`: exact site origin; defaults to `http://127.0.0.1:8000`
- `SMTP_HOST` / `SMTP_PORT`: defaults to Gmail SMTP over STARTTLS on port 587
- `SHEETS_WEB_APP_URL`: optional deployed Google Apps Script web app URL
- `SHEETS_WEBHOOK_SECRET`: optional random secret of at least 32 characters; keep it in the server secret manager
- `BIND_HOST` / `PORT`: defaults to `127.0.0.1:8000`
- `TRUSTED_PROXY_IP`: optional; trust `X-Real-IP` only from this exact proxy IP

For Gmail, enable 2-Step Verification and use an App Password. Do not use your normal Gmail password or put secrets in source files. Without SMTP credentials the API rejects submissions with a service-unavailable response; it does not pretend delivery succeeded.

## Google Sheets integration

Every inquiry form submission is emailed to the business and recorded in two tabs, `Inquiries` and `Contacts`, in the same private spreadsheet. The form includes a short notice explaining this. The site does not collect contact details from ordinary page visits. Keep the spreadsheet private and share it only with staff who need access.

1. Create a private Google Sheet and open **Extensions > Apps Script** from that sheet.
2. Copy `google_sheets_webhook.gs` into the Apps Script project and save it.
3. In Apps Script **Project Settings > Script Properties**, add `SHEETS_SPREADSHEET_ID` with the spreadsheet ID and `SHEETS_WEBHOOK_SECRET` with a cryptographically random secret of at least 32 characters.
4. Deploy as a **Web app**, execute as your account, and allow access to anyone. The endpoint rejects requests without the secret token; do not publish that token in the website or share it in chat.
5. Put the deployed `/exec` URL in the server's `SHEETS_WEB_APP_URL` secret and the same secret token in `SHEETS_WEBHOOK_SECRET`.
6. Test one inquiry and verify it reaches Gmail and creates one row in each tab. Test that a normal page visit creates no row.

If Gmail succeeds but Sheet sync fails, the form reports that distinction and does not claim the Sheet was updated. The `Contacts` tab stores name, email, optional phone, business, service, and date. The `Inquiries` tab stores those details plus the message. A site visit never sends personal contact details to Google Sheets.

## Security and deployment

The API serves only an explicit file allowlist and one `POST /api/inquiries` endpoint. It accepts JSON text only: multipart requests and file uploads are unsupported, and unexpected fields are rejected. It validates fields and body size, rejects duplicate JSON keys and invalid Unicode, checks the configured origin and host, applies an in-memory rate limit, caps concurrent connections, uses a honeypot, and returns a restrictive Content Security Policy and other security headers. Inquiry email is plain text; the app does not render submitted text as HTML. The app server does not persist inquiry data; each form submission is forwarded to the private Google Sheet. There are no admin/data retrieval endpoints. The rate limit resets on restart and is per address seen by the app.

For public deployment, use a trusted HTTPS reverse proxy, configure the exact `APP_ORIGIN`, keep the app bound to loopback where possible, enable proxy-side rate limiting, and store SMTP credentials in the host's secret manager. Do not expose Python's built-in HTTP server directly to the public internet; use a maintained production server behind the proxy. If the platform requires a non-loopback bind, `ALLOW_NON_LOOPBACK_BIND=1` is an explicit opt-in; only use it behind the platform's HTTPS proxy and firewall. If using `TRUSTED_PROXY_IP`, configure the proxy to overwrite (not append) `X-Real-IP`. These measures reduce common injection and malicious-upload paths but cannot guarantee immunity from compromise. The API has not been run or security-tested in this environment because Python is not installed here. After installing Python, run `python -m unittest` to execute the validation and rate-limit tests.