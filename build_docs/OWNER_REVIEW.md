# George’s Oasis — consolidated owner review

Prepared October 7, 2026; restaurant hours updated October 14, 2026 from the user’s explicit publication request. Other observations still require approval.
The existing homepage’s photographs and visual direction are retained. Business facts observed on the old site are drafts until reviewed.

Open `/admin/content-review` for the authenticated checklist and links to each draft page preview. Full draft menu: `/admin/preview/food`. Public pages use current ordering/contact links while unapproved records are withheld.

| Review area | Prefilled source observations | Decision needed |
| --- | --- | --- |
| Contact & location | 2355 Schoenersville Road, Allentown PA 18109; (610) 264-1955 | Confirm public address, phone and ordinary table-reservation destination. |
| Staff routing | Event candidate: gsitaras90@gmail.com; general-contact candidate: galatou@msn.com | Confirm who checks saved inquiries, approved email recipient/sender, and response expectations. No live email has been sent. |
| General & dinner schedules | Approved by user October 14, 2026 and displayed on Home and Visit. General: Mon 7–3, Tue–Thu 7–8, Fri 7–9, Sat 8–9, Sun closed. Dinner: Mon/Sun closed, Tue 3–7, Wed–Thu 3–7:30, Fri 3–8, Sat 8 AM–9 PM. All times Eastern; other starts are AM for General and PM for Dinner. | Confirm future changes and holiday exceptions. Older blanket kitchen and breakfast cutoffs were not approved with these hours and are no longer displayed. |
| Golf schedule | Source: Mon 9–3, Tue–Thu 9–8, Fri–Sat 9–9, Sun closed; April into November; final start 45 minutes before close | Confirm current season/temporary closures, operating windows and last start. |
| Golf rates & group options | User approved October 14: adults $8, children $6; children are 58 inches and under OR under 12. Season April into November, last start 45 minutes before closing. Package options: ice cream, meal, cake/desserts, indoor/outdoor seating; entire-course reservations for groups of 20 or more. | Daily course hours, package pricing, discounts and reservation terms still need confirmation. |
| Full menu | 176 draft records transcribed from six recovered source images | Review every price, portion, inclusion, addition and disclosure. Supply the missing inventory document and seventh menu image; senior selections and full dinner coverage cannot be verified from the recovered set. |
| Menu ambiguities | Both takeout malt sizes appear as $5.75; some omelet add-on rules depend on the dish | Confirm ambiguous source printing and category/item-specific rules. Review dietary item names and descriptions before approval. |
| Desserts | Source includes hard ice cream, soft serve, sundaes, fountain drinks, pies and Greek desserts | Approve flavor list, season and serving hours separately. Do not imply every item is homemade or year-round. |
| Tuesday special | Half-price appetizers, summer-only source | Confirm eligible items, dates, hours and restrictions. |
| Wednesday special | Burger Night sources conflict: $10 versus $11–$13 | Resolve price, inclusions, time and dine-in/ordering eligibility. |
| Thursday special | Half-price appetizers source | Confirm current terms and schedule. |
| Friday special | $15 crab offering, unclear item scope | Identify exact dish/offer; do not imply crab cakes plus crab mac and cheese form a bundle. |
| Breakfast/brunch offers | Source promotional material | Confirm current dishes, prices and times. |
| Events | Dining/private-space/golf/dessert interests are inquiry options | Confirm capacities, minimums, deposits, lead time, cancellation/rain policies, pricing and off-site catering before publishing them. |
| Arrival/access | No verified detailed policy supplied | Confirm parking, accessibility, pets and alcohol rules if these should be published. |
| Story | Source names George and Harriet Sitaras and John, Debbie and Kelly | Confirm names, current roles and approved narrative. No founding date or undated 40th-anniversary claim is published. |
| Media | Existing eight homepage photographs reused | Confirm rights, current relevance, captions and photographs appropriate for each page. |
| Pie campaign | Existing 2025 campaign is expired | Remains unpublished. A new campaign needs separate approval, dates, prices, pickup and payment arrangements. |
| Operations | SQLite inbox plus optional SMTP staff notice | Assign dashboard monitoring, retention/deletion policy, backup owner and production credentials. |

## Approval mechanics

The versioned file `georges_oasis/content/site.json` is the source for menus, schedules, editorial offers and business information. Preserve `metadata.source`; set a real `reviewed_at` date and `metadata.status` to `approved` only after approval. Use `valid_from` and `valid_until` for time-limited facts. `paused` and `archived` records are withheld. Run `flask --app app check-content` and inspect the authenticated preview after editing.

The existing offer editor explicitly records approval when the owner chooses to publish. Disabling homepage placements does not hide a valid offer on Specials. Source observations and conflicts remain in this review sheet and the archived menu images.
