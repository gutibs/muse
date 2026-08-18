# Publishing Muse — Setting Up Your Store Accounts

This guide explains how **you (the account owner)** create the two developer
accounts needed to publish the Muse app, and how to grant **your developer**
access so they can upload and manage the app on your behalf.

You will need two separate accounts:

| Store | Account | Cost |
|---|---|---|
| Google Play | Google Play Console | **USD 25, one-time** |
| Apple App Store | Apple Developer Program | **USD 99, per year (recurring)** |

> **Important:** The accounts must be created and owned by **you**, not by the
> developer. You stay the legal owner; the developer is only *invited* as a
> team member. This way the app, the reviews, and the revenue always belong to
> you, even if you change developers later.

---

## Decision first: Individual vs. Company account

Before creating anything, you have to choose **one of two account types**. The
same choice exists on both stores, and it's the most important decision because
it's hard to change later.

### Individual / Personal account

- Registered under **your personal name and ID**.
- The **"seller name"** shown publicly on the store listing is **your personal
  name** (e.g. *"Jane Doe"*), unless the store lets you set a separate display
  name.
- Fast to set up — no company paperwork required.
- Best if you don't have a registered company, or you want to launch quickly.

### Company / Organization account

- Registered under a **legally registered business entity**.
- The **"seller name"** shown publicly is your **company's name**
  (e.g. *"Muse Labs Ltd."*).
- Requires extra verification:
  - A **legal business entity** (registered company).
  - A **D-U-N-S Number** — a free business identifier from Dun & Bradstreet.
    Apple *requires* it for organization accounts; Google requires it for
    organization accounts too. Requesting one can take **a few days to two
    weeks**, so start early if you go this route.
  - A business website and a contact who can legally bind the company.
- Best if you have a company and want the app to look like a brand, or if more
  than one person from the business needs ownership-level control.

### Which one should you pick?

- **No registered company / want to launch now →** choose **Individual**.
- **Have a registered company / want the brand name on the store →** choose
  **Company**, and request your D-U-N-S Number *before* you start.

> ⚠️ Switching from Individual to Company later is possible but it's a manual
> migration process (especially on Apple) and can be slow. Decide up front.

---

## Part 1 — Google Play Console

### Step 1. Create the account

1. Go to **https://play.google.com/console/signup**.
2. Sign in with the **Google account** you want to own the app
   (use a dedicated business Gmail if you can — not a personal throwaway).
3. Choose your account type when asked: **"Yourself" (Individual)** or
   **"An organization / business" (Company)**.
4. Pay the **one-time USD 25** registration fee.
5. Complete identity verification (Google will ask for an ID document, and for
   organizations, the D-U-N-S Number and business details).

Verification can take a **few hours to a few days**. You can't publish until
it's approved.

### Step 2. Invite your developer

1. In **Play Console**, open the left menu → **Users and permissions**.
2. Click **Invite new users**.
3. Enter the developer's **email address** (it must be a Google account).
4. Set an **access expiry** if you want (optional).
5. Assign permissions. To let them publish and manage the app fully, grant:
   - **Admin (all permissions)** — full control, or
   - A custom set including **Release to production, testing, and pre-launch**,
     **Manage store presence**, and **View app information**.
6. Click **Send invitation**. The developer accepts via the email link.

You can change or revoke this access at any time from the same screen.

---

## Part 2 — Apple App Store (Apple Developer Program)

### Step 1. Create the account

1. First, make sure **you** have an **Apple ID** with two-factor authentication
   enabled (create one at **https://appleid.apple.com** if needed).
2. Go to **https://developer.apple.com/programs/enroll/**.
3. Sign in with your Apple ID and choose your entity type:
   - **Individual / Sole Proprietor** → registered under your personal name.
   - **Company / Organization** → requires the **D-U-N-S Number**, your legal
     entity name, and proof you can sign on behalf of the company.
4. Pay the **USD 99 annual** membership fee.
5. Complete Apple's verification. For organizations, Apple may **call you** to
   verify the business. This can take **a few days to two weeks**.

> Note: For an **Individual** account, your **personal name** appears as the
> seller on the App Store. For a **Company** account, your **company name**
> appears. This is set during enrollment and is not trivial to change later.

### Step 2. Invite your developer

1. Go to **https://appstoreconnect.apple.com**.
2. Open **Users and Access**.
3. Click the **+ (add)** button.
4. Enter the developer's **name and Apple ID email address**.
5. Assign a **role**:
   - **Admin** — full control (can manage everything except legal/banking), or
   - **App Manager** — can upload builds and manage the app, but not finances.
   - **Developer** — can upload builds and manage technical details only.

   For your developer to upload and submit the app, **Admin** or **App Manager**
   is recommended.
6. Click **Invite**. The developer accepts via the email link and the app then
   appears in their App Store Connect dashboard.

You can change roles or remove the developer at any time from **Users and
Access**.

---

## What to send your developer

Once both accounts are created and verified, the developer only needs to be
**invited** (Steps "invite your developer" above) — never share your passwords.
Send them:

- A confirmation that the **Play Console** invitation was sent to their email.
- A confirmation that the **App Store Connect** invitation was sent to their
  Apple ID email.

That's it. They accept the invitations and can start uploading Muse.

---

## Quick checklist

- [ ] Decide **Individual** vs **Company** (request D-U-N-S now if Company).
- [ ] Create **Google Play Console** account (USD 25, one-time) + verify.
- [ ] Invite developer in Play Console → **Users and permissions**.
- [ ] Create **Apple Developer Program** account (USD 99/year) + verify.
- [ ] Invite developer in App Store Connect → **Users and Access**.
- [ ] Confirm both invitations were accepted.
