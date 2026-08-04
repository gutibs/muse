# Muse — GDPR Privacy Notice

> ⚠️ **This file is NOT the published policy.** What users actually read is
> `nginx/landing/gdpr.html` (and `pdpo.html`), served at lovemuse.app and
> linked from the app and the store listings. This document is an internal
> working draft plus the technical annex describing how each right is
> implemented.
>
> They have drifted before — this file said backups are purged on a 30-day
> cycle while the published page said 90. **If you change a user-facing
> statement here, change the published HTML too, or the discrepancy is what a
> regulator reads.** The 30 vs 90 day contradiction is still open: nobody has
> confirmed the real retention configured on RDS.

*Effective date: 22 May 2026*
*Last updated: 22 May 2026*
*Version: 1.0*

> This document is the **GDPR-compliant Privacy Notice** for Muse. It is drafted to satisfy the information-duty requirements of Articles 12, 13 and 14 of the EU General Data Protection Regulation (Regulation (EU) 2016/679) ("GDPR") and the equivalent UK GDPR (as retained by the Data Protection Act 2018). It is intended for users in the European Economic Area, the United Kingdom, and Switzerland. Users in other jurisdictions may be covered by a separate notice (e.g. the Hong Kong PDPO policy shipped with the landing page).

---

## 1. Who we are (Data Controller)

**Muse** ("we", "us", "our") is the controller of the personal data processed through the Muse mobile and web application available at `lovemuse.app` and via the corresponding Android / iOS apps.

| Field | Value |
| --- | --- |
| Trading name | Muse |
| Registered address | *To be completed by the operator before publication* |
| General contact | [info@lovemuse.app](mailto:info@lovemuse.app) |
| Privacy contact | [privacy@lovemuse.app](mailto:privacy@lovemuse.app) |

**Data Protection Officer (DPO).** We are not required under Article 37 GDPR to designate a DPO because (a) we are not a public authority, (b) our core activities do not consist of large-scale monitoring of data subjects, and (c) we do not process special-category data on a large scale. Privacy enquiries should be sent to the privacy contact above.

**EU / UK representative.** If we do not have an establishment in the EEA / UK, we will appoint a representative under Article 27 GDPR / Article 27 UK GDPR. The representative's details will be published in this section once designated.

---

## 2. Personal data we process

We process the categories of personal data listed below. Items marked "optional" are only collected if you choose to provide them.

### 2.1 Account data
- Email address
- Display name
- Password (stored as a salted PBKDF2 hash — we never see the cleartext)
- Language / locale preference
- Account creation date

### 2.2 Profile data (optional)
- Bio / short description
- City
- Dietary preferences (from a closed list)
- Favourite cuisine
- Instagram handle, website URL, phone number
- Avatar image

### 2.3 Content you create
- Restaurants you pin as "visited" or "to visit"
- Ratings (1–5), free-text comments, optional "persona" tags
- Shared lists (public URLs you create to share a curated list)

### 2.4 Social graph
- Friend connections (sent / received / accepted / declined)
- Email invitations you send to non-users (recipient email, status)

### 2.5 Device & technical data
- IP address (used for security and rate-limiting)
- Device type, OS, app version, locale
- Approximate or precise geolocation — **only** when you explicitly grant the OS-level permission
- Crash reports and basic diagnostic logs
- Authentication tokens stored on the device

### 2.6 Communications
- Emails you send to us (e.g. support requests)
- Transactional emails we send to you (invitations, password resets, security alerts) and their delivery status

We do **not** knowingly process special categories of personal data (Article 9 GDPR) such as health, racial or ethnic origin, political opinions, religious beliefs, sexual orientation, or biometric data used for unique identification. Dietary preferences are recorded as user-chosen lifestyle tags, not as health data, and remain visible only to the user and their friends.

We do **not** knowingly collect data from children under 16 (or the applicable lower threshold set by a Member State down to 13). If you believe a child has provided us with personal data without parental consent, please contact us and we will delete it.

---

## 3. Purposes and legal bases (Article 6 GDPR)

Each processing activity has a documented purpose and a specific legal basis.

| # | Purpose | Categories | Legal basis (Art. 6 GDPR) |
| --- | --- | --- | --- |
| P1 | Creating, maintaining and securing your account | Account data | (b) Performance of the contract you enter into when registering |
| P2 | Letting you pin, rate and share restaurants | Content, Profile | (b) Performance of the contract |
| P3 | Showing you content from friends you have accepted | Social graph, Content | (b) Performance of the contract |
| P4 | Sending transactional emails (invitations, password resets, security alerts) | Account, Communications | (b) Performance of the contract / (c) Compliance with legal obligations for security alerts |
| P5 | Showing your approximate/precise location on the map | Location | (a) Your **consent**, granted via the OS permission prompt and revocable at any time in OS settings |
| P6 | Preventing abuse (rate-limiting, anti-spam, fraud detection) | IP address, technical data | (f) Our **legitimate interest** in operating a safe service, balanced against your rights — see §10 |
| P7 | Improving the service, debugging, and aggregate analytics | Technical, error logs | (f) Our **legitimate interest** in maintaining and improving the product |
| P8 | Sending invitation emails to addresses you supply | Recipient email, your name | (f) Our **legitimate interest** and the recipient's reasonable expectation that you, as their contact, are introducing them to a service — see §10 |
| P9 | Complying with legal obligations and lawful requests from authorities | All categories as required | (c) Compliance with a legal obligation to which we are subject |
| P10 | Defending or establishing legal claims | All categories as required | (f) Our **legitimate interest** in protecting our rights |

If we ever decide to process your data for a new purpose that is incompatible with those listed above, we will inform you in advance and, where required, obtain your consent under Article 6(1)(a) GDPR.

---

## 4. Recipients of your data (Article 13(1)(e) GDPR)

We do **not** sell your personal data. We share it only as set out below.

### 4.1 Other users of Muse
- **Your friends** see your display name, avatar, city, profile fields you have filled in, your pins and ratings, and your shared lists.
- **Anyone holding a "shared list" link** you have generated can see the public version of that list (title, pins included, your display name, avatar, city). You can revoke a shared link at any time from your Profile screen — the link will then return a 404.
- **Anyone you have invited by email** receives an email that contains your display name (or email if no display name is set) and an invitation link.

### 4.2 Processors acting on our instructions (Article 28 GDPR)
Each of the following entities processes personal data on our behalf under a written data-processing agreement that imposes the safeguards required by Article 28 GDPR.

| Processor | Function | Data processed | Region |
| --- | --- | --- | --- |
| Amazon Web Services EMEA SARL ("AWS") | Hosting (EC2 compute, RDS PostgreSQL database, S3 storage) | All categories | **United States** — `us-east-2` (Ohio) |
| Resend (Resend.com, Inc.) | Transactional email delivery | Recipient email, email subject/body, delivery status | **United States** |
| Google LLC | Google Maps Platform — Places API and tile imagery, called via our backend proxy | Search terms you type, lat/lng you view, place IDs you select | **United States** (Google does not return personal identifiers from these calls to us) |
| OpenStreetMap Foundation / Nominatim contributors | Reverse-geocoding (lat/lng → address) called via our backend proxy | lat/lng, our contact email in the User-Agent header per the Nominatim usage policy | **Germany / EU** |
| Cloudflare, Inc. (if/when configured) | TLS termination and DDoS protection | IP address, request metadata | Globally distributed edge network |

### 4.3 Disclosures required by law
We may disclose personal data when compelled to do so by a binding court order, regulatory request or subpoena issued by an authority of competent jurisdiction. Where the law permits, we will notify you before complying.

### 4.4 Business transfers
If Muse is involved in a merger, acquisition or sale of all or part of its assets, your personal data may be transferred to the acquirer subject to the same protections set out in this Notice. We will notify you (and obtain consent if required) before any such transfer becomes effective.

---

## 5. International transfers (Articles 44–50 GDPR)

Some of our processors operate outside the EEA / UK / Switzerland — principally in the United States. Where we transfer personal data to such processors we rely on one or more of the following safeguards:

1. **Adequacy decisions** (Art. 45) — for transfers to countries the European Commission or the UK government has deemed to provide an adequate level of protection.
2. **EU–US Data Privacy Framework** — for transfers to US recipients that are self-certified under the DPF, and the UK Extension to the DPF for UK transfers.
3. **Standard Contractual Clauses** (Art. 46(2)(c)) — the European Commission's 2021 SCCs, supplemented by transfer impact assessments where required.
4. **Encryption in transit** — TLS 1.2 or higher for all data leaving our infrastructure.
5. **Pseudonymisation and minimisation** — we transmit only the data necessary for each processor's function.

You may request a copy of the safeguards in force for any specific transfer by writing to [privacy@lovemuse.app](mailto:privacy@lovemuse.app).

---

## 6. Retention (Article 5(1)(e) GDPR)

We keep personal data only for as long as necessary for the purposes set out in §3:

| Data | Retention |
| --- | --- |
| Account & profile data | For the lifetime of your account |
| Content you create (pins, ratings, shared lists) | For the lifetime of your account; shared lists you delete are removed within 24 hours |
| Friend connections & email invitations | Until accepted/declined or deleted; pending invitations expire after 12 months |
| Authentication tokens | Refresh tokens valid for 14 days from issuance; rotated on each use |
| Server logs (IP, request metadata) | 30 days |
| Crash reports | 90 days |
| Database backups | Rolling 30 days — your deletion may persist in a backup for up to that period before being overwritten |

When you delete your account, we delete or irreversibly anonymise all personal data within **30 days**, except where retention is required (a) to comply with a legal obligation, (b) to resolve disputes, or (c) to enforce our agreements. Backup snapshots are purged on a rolling 30-day cycle.

---

## 7. Your rights (Articles 15–22 GDPR)

You can exercise any of the rights below by writing to [privacy@lovemuse.app](mailto:privacy@lovemuse.app). We will respond within **one month** of receiving your request (extendable by two further months for complex requests, in which case we will inform you within the first month). Most rights can also be exercised directly from your in-app Profile and Settings screens.

| Right | What it means | How to use it |
| --- | --- | --- |
| **Access** (Art. 15) | Obtain a copy of the personal data we hold about you and information about how we process it | Email us, or use Settings → "Export my data" |
| **Rectification** (Art. 16) | Correct inaccurate or incomplete data | Edit directly in Profile / Settings, or email us |
| **Erasure / "right to be forgotten"** (Art. 17) | Have your data deleted, subject to legal-retention exceptions | Settings → "Delete my account", or email us |
| **Restriction** (Art. 18) | Pause processing in certain situations (e.g. while a rectification request is pending) | Email us |
| **Portability** (Art. 20) | Receive your data in a structured, commonly used, machine-readable format and transmit it to another controller | Settings → "Export my data" (JSON), or email us |
| **Object** (Art. 21) | Object to processing based on legitimate interests (§3, P6–P8, P10) — we will stop unless we can demonstrate compelling legitimate grounds that override your rights | Email us, stating the basis on which you object |
| **Withdraw consent** (Art. 7(3)) | Withdraw consent at any time, without affecting the lawfulness of processing carried out before the withdrawal | Revoke the OS location permission, unsubscribe from emails, or email us |
| **Automated decision-making** (Art. 22) | Not to be subject to a decision based solely on automated processing that produces legal effects | We do not make such decisions; this right therefore does not apply to current processing |

### 7.1 Right to lodge a complaint
You also have the right to lodge a complaint with a supervisory authority — in particular, the supervisory authority of the Member State of your habitual residence, place of work, or place of the alleged infringement (Art. 77 GDPR).

A non-exhaustive list of supervisory authorities:

- **Spain** — Agencia Española de Protección de Datos (AEPD), [aepd.es](https://www.aepd.es)
- **Italy** — Garante per la Protezione dei Dati Personali, [garanteprivacy.it](https://www.garanteprivacy.it)
- **France** — CNIL, [cnil.fr](https://www.cnil.fr)
- **Germany** — your competent Landesdatenschutzbehörde
- **Ireland** — Data Protection Commission, [dataprotection.ie](https://www.dataprotection.ie)
- **United Kingdom** — Information Commissioner's Office (ICO), [ico.org.uk](https://ico.org.uk)
- **Other EEA states** — see the EDPB list at [edpb.europa.eu/about-edpb/board/members](https://edpb.europa.eu/about-edpb/board/members)

We would, of course, appreciate the chance to address your concerns before you approach the supervisory authority.

---

## 8. Security (Article 32 GDPR)

We apply reasonable and appropriate technical and organisational measures to protect personal data, including:

- **Encryption in transit** — TLS 1.2+ for all client–server traffic; HSTS on all subdomains.
- **Password hashing** — Django's default PBKDF2-SHA256 with per-user salt; cleartext passwords are never stored or logged.
- **Access control** — least-privilege IAM roles for production access; SSH access restricted to administrator keys; database access restricted to the application backend.
- **Rate-limiting** — per-IP and per-user throttles on sensitive endpoints (login, registration, invitations, search, places autocomplete).
- **Auditing** — server logs of authentication, invitation issuance, and admin actions retained for 30 days.
- **Patching** — operating system and dependency updates applied on a regular schedule; security advisories monitored.
- **Backups** — encrypted at rest; restorability tested periodically.

No system is perfectly secure. If you find a vulnerability please report it confidentially to [security@lovemuse.app](mailto:security@lovemuse.app); we will acknowledge within 72 hours.

---

## 9. Personal data breaches (Articles 33–34 GDPR)

If we become aware of a personal data breach we will:

- Notify the competent supervisory authority within **72 hours** of becoming aware, unless the breach is unlikely to result in a risk to your rights and freedoms.
- Notify affected users **without undue delay** when the breach is likely to result in a *high* risk to their rights and freedoms, unless one of the exceptions in Art. 34(3) applies (e.g. data was encrypted and the key is intact).

---

## 10. Legitimate-interest balancing test (Article 6(1)(f))

Where we rely on legitimate interest (purposes P6, P7, P8, P10 in §3) we have considered:

- **Necessity** — the processing is necessary to operate, secure and improve Muse; we have considered less intrusive alternatives and adopted the minimum data necessary.
- **Reasonable expectations** — users reasonably expect a social application to (i) defend against abuse, (ii) improve via aggregate analytics, and (iii) deliver invitations addressed to contacts that an existing user voluntarily provides.
- **Impact** — the impact on data subjects is low: technical data is short-lived and pseudonymous; invitation emails are one-shot and revocable.
- **Safeguards** — strict retention limits, rate-limiting on outgoing emails, an opt-out at the recipient's first email click, and an internal block-list for addresses that have asked not to receive further invitations.

You can object to any of these processings at any time — see §7.

---

## 11. Cookies and similar technologies

The Muse app does not use behavioural advertising cookies. The web landing at `lovemuse.app` uses only strictly necessary cookies and `localStorage` for storing your preferred language. See the separate Cookies Notice at [lovemuse.app/cookies.html](https://lovemuse.app/cookies.html) for full details.

---

## 12. Automated decision-making and profiling

We do not carry out automated decision-making, including profiling, that produces legal or similarly significant effects on you (Art. 22 GDPR).

---

## 13. Changes to this Notice

We may update this Notice from time to time. Material changes will be notified to you in-app and by email before they take effect; non-material changes (typographical fixes, clarifications) will simply update the "Last updated" date at the top.

A history of substantive changes is maintained in `docs/GDPR_PRIVACY_POLICY.md` in our source repository.

---

## 14. Contact

For any question, complaint, or rights request:

- **Email:** [privacy@lovemuse.app](mailto:privacy@lovemuse.app) (privacy enquiries)
- **Email:** [info@lovemuse.app](mailto:info@lovemuse.app) (general)
- **Postal:** *Operator's postal address — to be completed before publication*

---

## Annex A — Data export & deletion mechanics

This annex documents, for transparency and operator due-diligence, how the rights in §7 are implemented technically.

### A.1 Export ("Access" and "Portability")
- Endpoint: `GET /api/v1/auth/profile/me/export/` — returns a JSON document containing every row in our database keyed to the requester's user id (profile, pins, shared lists, friendships, email invitations sent).
- The export excludes: password hash, authentication tokens, and data belonging to other users (e.g. friend identities are returned as pseudonymous user ids only).
- The export is delivered within one month per Art. 12(3).

### A.2 Deletion ("Erasure")
- Endpoint: `DELETE /api/v1/auth/profile/` — triggers the erasure pipeline. Reachable in-app from **Settings → Delete my account**.
- The request must carry your current password: an access token alone is not accepted, so a lost or unlocked device cannot be used to erase your account.
- Identifying fields are replaced or emptied: email and username become `deleted-<uuid>@muse.local`, the password is made unusable, the account is deactivated, and every profile field (display name, bio, city, phone, Instagram, website, avatar file, location, dietary preferences) is cleared.
- Deleted outright: friendships in both directions, email invitations you sent and any addressed to you, feed activity, shared-list links, and your consent records.
- Retained, without your identity attached: the ratings and comments you left on restaurants. They remain visible to other users, attributed to "Anonymous". This is the one category we keep, because removing it would erase other people's reference points about a venue.
- The deletion is irreversible and takes effect immediately; all active sessions stop working at once.

### A.3 Objection and restriction
- These rights are handled manually via [privacy@lovemuse.app](mailto:privacy@lovemuse.app) (we expect very low volume).
- During the resolution of a restriction request we may flag the relevant rows with a `processing_restricted` boolean that the application checks before any non-essential processing.

---

*End of Notice — Version 1.0 · 22 May 2026*
