# Curation feedback and notifications

Experts report a problem or suggestion on a public curated-gene page; curators triage
them in a logged-in inbox and may get an email. The notification layer is reusable
(a later "volunteer to curate" feature adds an event to `EVENTS`).

## Tables (migration 0024)
- `curation_report`: gene_id, association_id (null), kind (problem|suggestion), message
  (<=4000), reporter_name (<=200), reporter_email (<=320), status (open|resolved|dismissed),
  handled_by/handled_at, created_at; index (status, gene_id).
- `user_notification_pref(user_id, event, enabled)`, PK (user_id, event), cascade on user
  delete. A missing row means enabled.

## Endpoints
- `POST /api/curation/reports/` (public, 5/hour per IP): 202 `{"status":"received"}`, never
  echoes data. 404 unless the gene has a published association. Non-empty `website`
  (honeypot) returns 202 and stores nothing.
- `GET /api/curation/reports/` (curator): filter status, gene_symbol; paginated; meta has
  `open_count`. `PATCH /api/curation/reports/{id}` (curator): set status, handled_by/at.
- `GET|PUT /api/users/me/notification-prefs` (any logged-in user): every event with label
  and enabled flag; PUT `{event: bool}`, unknown events are 422.

## Notifications
`services/notifications.notify(db, event, users, subject, body, background_tasks)` sends
plain-text email via `core/email.send_email` after the response. It skips inactive users and
users who disabled the event, does nothing without SMTP, and logs failures without raising.
Links use the existing `SITE_URL` setting. The only event is `curation_report`, sent to
active curators and admins.

## Privacy
Reporter name and email are stored only for curators: no public response contains them;
they appear in the curator inbox and the curator notification email. MCP stays read-only;
these paths are not in its allowlist.

## Frontend
`ReportCurationDialog` on the curated-gene header; `/curation/reports` inbox (curator
route, user-menu entry); `NotificationPrefsCard` on the profile page.

## Volunteer curation applications
A visitor applies to curate a gene from the curated-gene and gene page headers
(`VolunteerDialog`). The application is the registration path: registration stays admin-only.

- Table `volunteer_application` (migration 0025): gene, name, email, affiliation, ORCID,
  motivation, status `pending|approved|rejected`, decider, decision note, linked `user_id`.
- `POST /api/volunteer-applications/` (public, 3/hour, honeypot, gene must exist; a pending
  duplicate for the same email and gene is accepted without a new row; never echoes data).
  `GET` (admin, status filter, paginated) and `POST /{id}/decision` (admin; only pending, else
  409). Approval links an existing account (viewer raised to curator when role=curator) or
  creates one with an unusable random password and a 7-day set-password link
  (`{SITE_URL}/reset-password?token=...`). Rejection emails a polite note plus the decision note.
- Emails: applicant confirmation, invite and rejection are transactional (not switchable,
  sent only when SMTP is configured). Admins get the new event `volunteer_application`, which
  is switchable in notification preferences.
- Admin view `/admin/volunteer-applications` (dashboard card, confirm dialog with role and note).
- Privacy: applicant data is visible to admins only; MCP allowlist unchanged.
- Follow-up (not built): delete rejected applications after 12 months.
