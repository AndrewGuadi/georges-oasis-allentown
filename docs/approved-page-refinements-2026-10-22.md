# Approved page refinements — October 22, 2026

Implemented the user's approval of the ten-page proposal, incorporating their corrections: set the soup feature aside, leave golf hours blank, describe ice cream as a seated restaurant visit with counter ordering, emphasize peaceful corporate gatherings in the Allentown–Bethlehem area, state restaurant wheelchair accessibility, and use restaurant opening hours for ordering.

| Page | Implemented |
| --- | --- |
| Homepage | Welcome describes booths, flowers and personal details. General family-recipe kitchen introduction replaces the tomato-soup feature. Gathering copy includes team lunches and family celebrations. Story preview and sidebar describe actual family photographs and décor. Existing hero and Menu/Visit actions retained. |
| Menu | Two photographed features, French toast and the gyro, replace the quantity-led opening. Features use approved menu records and prices and link to their exact entries; unpublished dishes cannot appear as features. All 212 selections, search and printed menus remain accessible. Soup remains in the original full-menu listing but is not featured or assigned a new recipe story. |
| Mini Golf | Course schedule deliberately cleared and displayed as a dash with an accessible “Hours not yet posted” label and one explanatory note. Approved rates, child definition, season, last-start and group arrangements retained. FAQ child price now uses the shared rate record. Restaurant accessibility is distinguished from unconfirmed course access. |
| Ice Cream | Featured sundaes, soft serve and Greek pastries precede the full dessert menu. One concise section explains ordering at the restaurant counter, seated enjoyment, visiting just for ice cream and seasonal soft serve. Old flavor observations are retained privately as drafts until the user supplies the current list; no fabricated flavor placeholders. |
| Parties & Groups | Corporate lunches, professional connection and team bonding receive prominent Allentown–Bethlehem messaging alongside family celebrations. Corporate inquiry link preselects the existing Company gathering option using an allowlisted URL parameter. Descriptive indoor/outdoor photo labels, accessible-restaurant guidance and three-step process remain. Booking qualification is consolidated beside the form. No capacities, equipment, private meeting rooms or guaranteed quiet conditions are invented. |
| Visit | Directions and separate service hours precede the supporting photos. Confirmed restaurant wheelchair accessibility is stated directly. Table reservations, group inquiry and general contact remain distinct. Simple breakfast / golf-and-treat visit ideas are qualified by the relevant service availability. |
| Specials | Wednesday–Friday direction retained, with exact offers still pending. Entire coupon section is absent unless a coupon is live; removed its permanent footer subsection link. Existing coupon editor and validity filtering retained. Recurring-special editor/content work deferred with the missing offers to the next pass. |
| Our Story | Trimmed generic experience copy, kept confirmed family-recipe / hospitality themes and actual dining-room details, and removed the repeated historic-photo card. Historical names, dates, recipe origin stories and photo identification remain unpublished pending user input. |
| Gallery | Added an accessible photo viewer with previous/next, keyboard arrows, Escape, focus return, original-image links and an image-error fallback. Ordinary image links work without JavaScript. Shares viewer behavior with Mini Golf. |
| Order | Shortened provider choices and supporting copy. FoodBooking uses neutral “Order Online” wording; the user confirmed the same restaurant menu but did not specify pickup/delivery fulfillment. An expandable shared restaurant-hours table supplies ordering hours. Reduced the dine-in invitation to a compact link. |

## Shared facts and pending inputs

Approved visit, ice-cream and ordering facts and their source are recorded in `georges_oasis/content/site.json`. The private Content & launch review page now displays the follow-up list. Remaining inputs: current golf hours, current flavors and counter photographs, breakfast cutoff, event capacities/terms/response expectations, family history and photograph identification, specific weekly offers, and precise FoodBooking fulfillment mode. The soup feature is intentionally deferred.

## Validation

42 Python tests passed, covering complete menu inventory, featured-item publication and shared prices, coupon scheduled/live/expired behavior, shared ordering hours, safe corporate prefill, draft flavor/history exclusion and all existing public/inquiry/security tests. Content validation, JavaScript syntax checks and Git whitespace checks passed.

All ten public pages passed image and overflow checks at 320, 390, 768, 1024 and 1440 px. Desktop/mobile screenshots were captured under `/tmp/oasis-approved-review`. Additional viewer, corporate inquiry, search, ordering-disclosure, enlarged-text and JavaScript-disabled checks are recorded with the final review results.

Changes remain local. No deployment, live inquiry, email or order was submitted.

Final interaction checks passed: gallery keyboard opening, previous/next wrap, Escape and focus return; the shared golf viewer; featured-food links clearing menu search; corporate occasion prefill and form-anchor clearance; ordering-hours disclosure; Visit hours above supporting photos; homepage actions above the short-phone dock; 200% text without horizontal overflow; direct photo links and all 212 menu items without JavaScript. Optional external font requests were disabled during the focused interaction checks; the earlier full layout/screenshots used the normal page assets.

Viewer layout was additionally checked at 320×568, 390×844 and 1440×900. Close/next controls and captions remain within the viewport on both Gallery and Mini Golf; keyboard arrows, Escape and focus return passed at each size.
