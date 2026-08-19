# Muse Analytics — what it measures and how to read it

Written for the product owner. Same content as the shared web version, kept in
the repo so it stays with the code that produces these numbers.

Last updated: 2026-08-19 · app version V1.1.0

---

## Where to look

**lovemuse.app/admin → Analytics → Events → "Analytics dashboard"**

Sign in with your own admin account. The dashboard button sits at the top
right of the events list.

Numbers are recalculated at most every ten minutes, and the page tells you
when it last did. If you tap a button on your phone and refresh straight
away, give it a moment — nothing is broken.

---

## The two figures, and which one to quote

Every outbound tap is stored twice over: once as it happened, and once
counted per person per day. Both are on screen on purpose — so that when
someone asks "is that the same person five times?", there is an answer.

| Figure | What it counts | Use it for |
|---|---|---|
| **People** | One tap per person, per venue, per day | This is the one to quote. Five taps from one regular on a Friday count as one person interested. |
| **Taps** | Every tap, raw | A sanity check. Misleading on its own. |

The dashboard also shows four totals for the last thirty days: venues saved
to a map, outbound clicks, venue pages opened, and cards seen in a list.

**Saved to map** is the sturdiest of the four: it is recorded by the server
when the pin is actually created, so it cannot be inflated from a phone.

---

## Booking links

A venue only shows a **Book a table** button once it has a booking link, and
a link is only published once we are confident it belongs to that
restaurant. Anyone adding a restaurant to Muse can type one in, so the check
is not optional: "book here" is exactly the screen where somebody hands over
their name and phone number.

**Published straight away**

- A booking provider we recognise — OpenTable, TheFork, Resy, SevenRooms,
  Quandoo, TableCheck, Meitre, Woki, Tock, CoverManager.
- The restaurant's own website, the one Google already gave us.
- A domain that carries the restaurant's name.

**Held for review**

Anything else is saved but not shown, and waits in the admin under
`Restaurants → Reservation status: pending`. Approve it there and the button
appears.

A link like `somewhere-else.example/book/don-julio` stays hidden no matter
how convincing the address looks — we compare the domain, never the rest of
the URL.

---

## Already live

Seven venues have a verified booking link. Each one was opened and checked
before loading.

| Venue | City | Booking via | Link |
|---|---|---|---|
| Don Julio | Buenos Aires | Meitre | `donjulio.meitre.com` |
| El Preferido de Palermo | Buenos Aires | Meitre | `elpreferido.meitre.com` |
| Anchoita | Buenos Aires | Woki | `wokiapp.com/restaurante/anchoita` |
| Trescha | Buenos Aires | Woki | `wokiapp.com/restaurante/trescha-restaurant` |
| St. JOHN | London | OpenTable | `stjohnrestaurant.com/pages/reservations` |
| Sketch | London | SevenRooms | `sketch.london/book` |
| Yardbird | Hong Kong | Tock | `yardbirdrestaurant.com/reserve` |

For St. JOHN and Sketch the link points at the restaurant's own booking page
rather than a deep link, because both run several rooms or sites behind one
page and the choice belongs to the guest.

---

## What we found in the catalogue

Checking booking links meant checking whether each restaurant still exists.
Three did not survive that check.

| Venue | Status | What we found |
|---|---|---|
| Tegui | **Closed** | Shut in October 2021. Its booking record confirms it: inactive, last reservations November 2021. |
| i Latina | **Closed** | Shut in January 2021, and its old domain now redirects to an unrelated site. |
| Sacro | Open | Still trading, but no booking channel we could verify — the domain lapsed and its old booking page is inactive. No link loaded. |

### Two closed restaurants are still on the map

Between them, Tegui and i Latina hold four real pins from members — someone
could set out for dinner at a place that closed four years ago. i Latina is
the more awkward of the two: its address is the one **Trescha** occupies
today, so the map carries two pins on the same door, one of them for a
restaurant that no longer exists.

Nothing has been deleted. Removing a venue takes members' reviews with it,
and that is a product call. The options are to hide them from search while
keeping the history, or to merge i Latina into Trescha.

---

## Honest limits

- **The clock starts now.** Measurement began the day this shipped; there is
  no history for the months before it. The first weeks will look thin, and
  that is the data being truthful.
- **A tap is a tap, not a booking.** Muse can tell you someone chose to go to
  OpenTable from a venue's page. Whether they finished the booking happens on
  the other side of that link, where we cannot see.
- **People can opt out.** Settings has a switch to stop measuring an account
  entirely, and nothing from that account is recorded while it is on. Our
  privacy policy promises this, so the app has to honour it.
- **Individual events are deleted after 14 months.** What remains is a
  monthly total per venue with no user attached to it — which is the number
  you would show a restaurant anyway, and it is kept indefinitely.

---

## For whoever maintains this

- Events are written in one place only: `analytics/services/ingest.py::record_event`.
- The monthly aggregates come from `rollup_analytics`, the deletion from
  `prune_analytics`; both run from `deploy/cron/muse-maintenance`.
- Booking-link classification lives in `restaurants/services/reservations.py`.
  Adding a provider means adding its **registrable domain** there, with a test.
- `scripts/ver-eventos.py` prints what has been recorded while testing by hand.
