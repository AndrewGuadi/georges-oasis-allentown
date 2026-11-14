# Homepage implementation record — October 16, 2026

The user's homepage plan authorizes implementation while retaining the selected design. Developer: Codex; content preparation and ongoing offer/seasonal updates: Andrew; business facts and presentation review: George. Existing uncommitted work was preserved. Changes remain local and reviewable in Git; no deployment, booking or external message was made.

| ID | Disposition | Change and acceptance evidence | Owner / remaining dependency |
| --- | --- | --- | --- |
| HP01 | Implemented | Existing shared navigation retained; phone added to mobile menu. Menu, Visit and Specials remain available. | Developer; browser verification below. |
| HP02 | Implemented | Eastern-time same-day next-service message; explicit “View service hours” fallback. Existing exception handling retained. Golf and soft serve remain unknown without approved schedules. | Andrew maintains service records; George supplies seasonal hours. |
| HP03 | Implemented / deferred asset | Requested headline and quieter supporting copy; hero grows with content and enlarged text. Existing exterior retained. | Andrew selects desktop/mobile crops from George's new uploads. |
| HP04 | Implemented | Same four cards and order; suggested labels, single links, one-column layout on the narrowest phones. | Approved menu items remain a destination dependency. |
| HP05 | Implemented / deferred facts | Welcome connects the meal, outdoor course and dessert with the confirmed street location. No invented homemade or farm history claims. | Andrew/George: confirm one family detail and a named homemade specialty. |
| HP06 | Implemented / deferred facts | Kitchen now leads with View Menu, followed by existing Order Online provider; burger photograph supplies specific visual context. | George confirms representative dishes and preparations before named homemade claims are added. |
| HP07 | Implemented / deferred launch content | Compact kitchen treatment announces only Wednesday–Friday. Homepage and Specials share publication filtering and the same offer partial. Missing details use honest inquiry copy; Tuesday archived. No invented offers or $0 prices. | Andrew resolves exact offers, prices, windows and terms; George confirms unresolved facts. This remains an outstanding launch decision. |
| HP08 | Implemented / deferred asset | Inquiry and exploration paths retained, copy distinguishes inquiry from booking. | Existing composite photograph retained until Andrew selects a clear space image from George's uploads. Live mail delivery remains a gatherings/deployment check. |
| HP09 | Implemented | Landscape copy, course schedule anchor and targeted phone link. April into November / 45-minute guidance retained; no rates added. Service selected by key, not array position. | George confirms current course hours. |
| HP10 | Implemented / deferred facts | Historic photograph caption added; less repetitive general copy. Approved story record will supply the opening paragraph automatically. | Names, relationships, dates and photograph identification remain drafts. |
| HP11 | Implemented | Shared restaurant/dinner table unchanged in values, including Saturday dinner 8 AM–9 PM. Public email and targeted schedule links added. | Live reservation completion remains unverified. |
| HP12 | Implemented | Shared footer phone/email, existing grouped sitemap and lightweight Facebook link retained. | No social feed or testimonials added. |
| HP13 | Implemented | Shared contacts, service records, recurring offers and provider configuration reused. No new CMS. | Andrew maintains records; George confirms material facts. |
| HP14 | Implemented | Hero content can grow; narrow cards stack; fixed table columns wrap; reduced-motion transitions disabled. Existing keyboard controls retained. | Browser verification below. |
| HP15 | Retained / deferred assets | Existing optimized WebP assets, dimensions, hero preload and lazy lower images retained. | New crops/variants await new photos; no image generator or oversized originals introduced. |
| HP16 | Implemented / deployment check | Existing descriptive title, sharing image, canonical and conservative restaurant schema retained. Preview responses now use noindex/nofollow and robots disallow all. | Production must use OASIS_ENV=production, HTTPS and the correct public host; canonical currently derives from request host. Check final public URL at deployment. |
| HP17 | Implemented / deferred external verification | Internal route/anchor and provider configuration tests pass. Existing provider fallback contact paths retained; no analytics added. | FoodBooking/reservation could not be verified by lookup tool; Grubhub returned its JavaScript gate. Manually walk through providers before launch, without completing a transaction. |

## Contact decision

The existing shared external-link record contained `gsitaras90@gmail.com`. It is now in the business record and visible on Home, Visit and the shared footer. An explicit `INQUIRY_RECIPIENT` override becomes the public address too, keeping them consistent. When SMTP is configured with `INQUIRY_SENDER` but no recipient override, notification delivery uses this business email. No SMTP credentials were changed and no live email was sent. Unconfigured mail remains unconfigured.

## Concrete review packet for Andrew and George

- Hero: existing exterior photograph for now; “More Than a Meal / Good food. A little fresh air. Time together.” New property photograph still needed for the proposed replacement.
- Welcome: “A meal with the people you love, a little time outside, and something sweet before you go. Make room for a slower moment at George’s Oasis on Schoenersville Road, where the restaurant, outdoor mini golf and ice cream each offer a reason to stop by.”
- Kitchen: “A familiar favorite, made with care.” General service copy and burger photo retained. No homemade claim is published until a particular preparation is confirmed.
- Story candidate in existing draft record: George and Harriet Sitaras, later family generations, and John, Debbie and Kelly. Confirm names/relationships and photograph context before publishing these details.
- Wednesday draft: Burger Night; conflicting recorded prices ($10 versus $11–$13). Inclusions, time and eligibility unresolved.
- Thursday draft: appetizers; discount, eligible items, serving time and dine-in terms unresolved.
- Friday draft: crab offering; resolve crab cakes versus crab mac and cheese and whether $15 is current, plus time and terms.

These draft details are deliberately confined to this review record and existing unpublished records. The public weekly treatment names the confirmed days and asks guests about current details.

## Verification

- CSS rebuilt with the existing Tailwind toolchain.
- Content validator and full Python unittest suite run, including dedicated homepage publication/status regression tests.
- Existing tests cover all public routes, internal anchors/assets, external configuration/fallbacks, draft exclusion and inquiry validation/receipts. No live form delivery or provider transaction was performed.
- Browser results recorded after responsive and keyboard checks below.

Final results: 32 Python tests passed; content validation and CSS build passed. Chromium checks passed at 320, 390, 768 and 1440 px with no horizontal overflow or broken images. Keyboard Enter/Escape and focus return, mobile menu dismissal, inquiry-anchor clearance, 200% root text size and reduced motion passed. The enlarged-text check found a visit-grid minimum-width problem; shrinking the grid children fixed it. Screenshots were captured at `/tmp/oasis-home-390.png` and `/tmp/oasis-home-1440.png`. Browser emulation does not replace testing on physical devices. Constrained-network performance and live SMTP/provider completion remain deployment checks.
