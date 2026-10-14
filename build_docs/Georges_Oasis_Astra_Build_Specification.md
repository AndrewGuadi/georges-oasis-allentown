# Georges Oasis Website Build Specification for Astra
Prepared for Authentic Dynamics and Astra
October 7 2026

## 1 Assignment and intended outcome
Extend the existing George’s Oasis Flask website with the remaining pages and shared functionality described here. Preserve the latest Concept 1 visual direction. Build a coherent site that lets a ready customer act immediately and gives an undecided customer the information needed to choose a meal, an outing or an event.

The website should reduce routine questions and incomplete inquiries for restaurant staff. Success means clear choices, accurate expectations, working next steps and information that can be maintained once. More content is useful only when it answers a customer question, demonstrates the experience or supports a decision.

Use the existing application structure and installed dependencies. Inspect repository instructions, routes, templates, models, forms, configuration, tests and deployment constraints before editing. Reuse working components. This is an extension of the separately hosted Flask application, not a WordPress implementation or a new hosting project. Do not replace the existing project with a static demo.

The user’s latest direction takes precedence over earlier Concept 2 guidance: cream backgrounds, forest green, restrained gold accents, palm branding, photographic cards and warm family restaurant styling. The latest prototype is a visual reference, not production architecture. Its generated tropical restaurant scene and low-resolution image regions are concept assets. Replace them with approved restaurant photography and proper logo assets for launch; retain the decorative palm framing.

Implement the public pages, reusable content structures and inquiry workflow. Reuse an existing administration interface if present. Provide maintainable configuration or content files where a full admin interface is not available. Do not create a large bespoke CMS merely to satisfy a small update requirement.

Deliver functioning code, meaningful verification, a route map, a concise change summary and one consolidated list of unresolved business facts. Do not publish, change DNS, remove the old website, submit real orders or replace payment providers as part of this assignment.

## 2 Evidence and publication rules
The October 6 website inventory is the business-content source. It records what was displayed, not owner approval that every item remains valid. The October 7 journey discussion and this specification define the proposed experience. The current repository determines actual implementation details.

Keep source observations, editorial drafts and approved public values distinct. Every time-sensitive record should support source, approval status, last reviewed date and, where applicable, validity dates. Suggested statuses are draft, approved, paused and archived. Preserve original records and conflicting values in internal notes. Do not silently pick a preferred price or rewrite uncertain policies as fact.

Publication rule: only approved records that are active within their validity window may appear as current offers. When information is unconfirmed, show useful approved content and an honest next action. Never expose internal notes such as TODO, confirm with George, placeholder price or approval pending on public pages. On staging, use an authenticated review view or separate owner checklist to identify missing facts.

Known conflicts requiring review include Burger Night at $10 versus $11–$13; the exact $15 Friday crab offering; Tuesday summer-only eligibility; Summer 2026 hours still displayed in October; golf child eligibility expressed with age or height; two different contact inboxes; and the expired 2025 pie form. July 3–4 golf artwork must not appear as a current offer.

Other unconfirmed facts include party capacity, deposits, minimum spend, cancellation and rain policy, group package prices, reservation lead time, off-site catering, course accessibility, parking arrangements, pet rules, alcohol policy and senior eligibility. Omit unsupported claims. Do not publish an invented opening year, hole count, customer quotation, rating, allergy assurance or claim that all ice cream is homemade.

Before launch, George needs to approve one prefilled review sheet covering contacts and hours; menus; specials; seasonal availability; party policies; and photos/story. Astra should continue implementing around those gaps rather than repeatedly stopping to ask for copy or small design decisions.

## 3 Customer journeys and action hierarchy
| Visitor intention | Decision information | Primary next action |
|---|---|---|
| Choose a meal | Menu, prices, meal period, children’s choices, atmosphere | View Menu, then Order Online or Get Directions |
| Plan an outing | Golf status, rates, last start, food and dessert options | Plan Your Visit |
| Get a treat | Ice cream choices, season, serving hours | Get Directions or See Desserts |
| Arrange a gathering | Space, occasion, capacity, options and process | Ask About Your Event |
| Return for a special | Valid date, time, price, inclusions and restrictions | View Special, then visit or order |
| Complete a known task | Direct access to order, phone, directions or hours | Perform that task immediately |

Every destination page must work as a first entry from search or a shared link. Its first screen should establish what the page offers, provide its most important practical fact, and display one primary action plus at most one secondary action. Do not force visitors through the homepage, a carousel, a long story or an account before they can act.

After the first screen, answer the questions in the order someone would make a decision. Repeat the primary action after the decisive information and near the bottom. Repetition must feel helpful rather than becoming a button beneath every paragraph. Labels must predict their destination: View Menu opens the local menu; Get Directions opens maps; Ask About Your Event opens the inquiry form; Order Delivery identifies the delivery provider.

Each page may suggest one relevant next experience. Golf can suggest lunch or ice cream. The restaurant can suggest a round after the meal. The event page can show food, room and golf options together. Never require visitors to accept add-ons or imply a bundled price unless a real package has been approved.

An outbound order click indicates intent, not a completed purchase. An inquiry indicates interest, not a confirmed booking. Carry these distinctions into interface copy, backend states and reporting.

## 4 Site structure and navigation
| Proposed route | Purpose | Main action |
|---|---|---|
| / | Introduce Oasis and distribute visitors to four experiences | View Menu or Plan Your Visit |
| /menu | Browse restaurant food and prices | Order Online |
| /ice-cream | Discover ice cream and desserts | Get Directions |
| /mini-golf | Decide whether and when to play | Plan Your Visit |
| /parties | Understand events and begin an inquiry | Ask About Your Event |
| /specials | See valid recurring and dated offers | Contextual visit or ordering action |
| /visit | Hours, location, service cutoffs and contact | Get Directions |
| /our-story | Family history and authentic setting | View Menu or Plan Your Visit |
| /gallery | Browse representative real photos | Relevant experience page |
| /order | Choose existing ordering or delivery provider | Continue to provider |
| /pies | Seasonal pie campaign, only when approved | Submit Pie Request or existing approved form |

These route names are proposals. Preserve useful existing route conventions and avoid duplicate destinations. Use one canonical route per purpose. Public navigation should prioritize Menu, Mini Golf, Ice Cream, Parties & Groups and Visit, with Order Online as the prominent action. Place Our Story, Gallery, Specials and any active pie campaign where they remain findable without overcrowding the masthead; adapt to available width.

Use a compact dropdown or accessible mobile menu when necessary. Keep the phone and directions readily available. On phones, an optional bottom action bar may show the current page’s primary action and one utility action. It must not cover form fields, content, keyboard controls or the footer. Hide it when it would obstruct an open dialog or active form.

Preserve the approved homepage composition. Change only destination wiring and useful compact shared information where needed. Do not turn the homepage into every page stacked together. Interior pages should use shorter heroes with practical information visible sooner than on the homepage.

Legacy routes need explicit permanent redirects at migration: /menus.html to /menu; /hours--info.html to /visit; /mini-golf.html to /mini-golf; /specials.html to /specials; /gallery.html to /gallery; /private-eventscatering.html to /parties; /index.html to /. Check existing incoming links and query strings before finalizing. Preserve an obvious Our Story link from Visit because the old hours page also contained the family history.

## 5 Shared visual and content system
Use a single base template and shared header, footer, action button, status strip, photo card, price row, FAQ and inquiry form components. Follow existing Tailwind patterns when present; compile production styles through the project’s build process rather than relying on the prototype’s development CDN. Keep public content available as server-rendered HTML.

The palette should follow the latest approved reference. Use dark green for text and primary actions, warm cream for surfaces and gold for a limited high-priority accent. Use a readable body face. Reserve expressive script lettering for short display headings; do not use it for prices, navigation, form labels, hours or long passages. Decorative palms should frame content without obscuring text or imitating photographs of the actual premises.

Use real images to answer questions: what the food looks like, what the room accommodates visually, what the course feels like, and how the entrance looks. Photo captions should identify the subject when helpful. Obtain approval for current relevance and usage rights. Do not use generated diners as real customer evidence or label an illustrative restaurant scene as the actual property.

Aim for approximately 40–80 words in an introductory block and short, specific descriptions elsewhere. These are editing guides, not quotas. A menu can be lengthy because it is useful structured information. A visit page can be short. Avoid keyword padding, repeated family-fun claims and unsupported superlatives. Replace generic Learn More labels with clear destinations when space permits.

Use ordinary links for navigation and buttons for interface actions. Provide visible focus, adequate contrast, descriptive headings, text labels with icons, keyboard-accessible navigation and accessible form errors. Do not hide essential content behind animation or hover. Preserve reading order when cards stack. Respect reduced-motion preferences.

Suggested page pattern: compact introduction and action; practical facts; main decision content; representative photos or proof; closely related experience; relevant FAQ; final action. Reorder when the customer’s task demands it. Never create empty sections merely to fill a template.

## 6 Restaurant menu page
Purpose: let visitors determine whether Oasis has food they want, see the relevant price and proceed to an existing ordering service or a visit. Customers may arrive looking for breakfast, a family meal, vegetarian choices or one particular dish.

First screen: H1 “Breakfast, Lunch and Dinner at George’s Oasis.” Suggested introduction: “Explore breakfast favorites, sandwiches, burgers, dinner plates and something sweet to finish.” Show View Menu Sections as an anchor and Order Online as the action. Display the approved breakfast cutoff nearby. A compact category navigation should immediately expose Breakfast, Lunch & Dinner, Children, Seniors and Desserts when those categories are approved.

Content order: category navigation; selected menu section; approved related special; optional small food-photo group; dining and ordering explanation; meal-specific FAQ; directions. Keep section headings and prices readable on a phone. Do not require horizontal scrolling or image zoom to read a dish. Preserve a downloadable menu as a secondary option.

Transcribe all approved items, descriptions, variations, additions and prices from the seven source menu images. Do not replace the complete menu with a handful of featured items. Preserve distinctions such as portion size and included sides. Review transcription against the original image. Do not infer a dish’s current availability from a filename. Keep the menu’s consumer advisory and other supplied disclosures intact where relevant.

Use structured menu data: category, item name, description, price or variations, add-ons, inclusions, availability note, approved dietary labels, display order and approval metadata. Store currency as an exact value. Do not label an item vegan, gluten-free or allergen-safe based solely on an ingredient guess. Use owner-approved labels and wording.

Optional search should match item names and descriptions without making the menu dependent on JavaScript. Keep all categories reachable without search. A no-results state should offer category browsing. Filters must not erase active context or hide the reset control.

Suggested FAQ topics: breakfast hours; children’s meals; available plant-based choices; takeout ordering. Publish answers only when supported. Cross-sell example: “Make it a visit: explore mini golf and ice cream.” Link to each destination without presenting an unapproved package.

Completion checks: all approved menu images accounted for; text/price transcription reviewed; no duplicate prices maintained in templates; category anchors work; keyboard and phone use verified; ordering opens the correct provider. Compare displayed items and prices with the ordering provider through an approved review process; do not assume automatic synchronization.

## 7 Ice cream and desserts page
Purpose: make a quick treat stop easy to plan, while revealing the dessert range. Use its own page because a customer seeking ice cream should not have to navigate a full lunch and dinner menu.

First screen: H1 “Ice Cream and Desserts.” Suggested introduction: “Stop by for a cone, a sundae or a sweet finish to your meal.” Primary action: Get Directions. Secondary action: Browse Desserts. Display the approved distinction between seasonal soft serve and year-round hard ice cream/desserts. Avoid a broad “available all year” claim that accidentally includes soft serve.

Content order: current seasonal availability; soft serve and approved toppings; hard ice cream choices; sundaes and fountain drinks; pies and Greek desserts; one or two representative photos; visit details; dessert FAQ. Show approved flavors as a readable list, not a long sequence of oversized cards. Keep categories linked to the same data used by the main menu.

Source material supports sundaes, shakes, floats, malts, pies, hard and soft ice cream, and homemade baklava/Greek desserts. The live content should be populated from approved menu records, not an invented rotation. Do not describe all ice cream as homemade. No live stock or flavor-availability indicator unless staff actually maintain it.

If soft serve is out of season, retain the page and explain what remains available. Example draft: “Soft serve is taking a seasonal break. Explore our hard ice cream and other desserts.” Use this only when the seasonal status is confirmed. Remove soft-serve-specific promotional calls to action while keeping directions and other dessert choices available.

Use an active pie-campaign card only when the campaign is approved and accepting requests. Otherwise, a bakery inquiry may be offered if George confirms that service. Do not expose the expired 2025 form.

Related experience: “A round of golf and a sweet finish.” Link to the course page without claiming a meal deal. FAQ topics may include soft-serve season, dessert hours and approved dietary options. Unknown ingredients or allergy questions should receive a truthful contact route rather than invented guarantees.

Completion checks: seasonal state updates page and homepage consistently; See Flavors lands here; approved dessert data matches the main menu; inactive pie campaign stays hidden; no unsupported homemade or dietary claims.

## 8 Mini golf page
Purpose: help a family, couple or group decide whether the course fits their visit and understand when play can start. School trips and fundraisers also need a clear path to group inquiries.

First screen: H1 “Mini Golf at the Oasis.” Suggested introduction: “Add a round of outdoor mini golf to your visit, or make the course your destination.” Show current approved season/status, adult and child rates, and the last-start rule together. Primary action: Plan Your Visit. Secondary action: Ask About a Group Outing. Do not show Book Now unless a real booking workflow exists.

Content order: operating status and rates; course photographs; hours and last start; practical visit information; group outings; food and ice cream suggestion; golf FAQ; final directions or inquiry action. A compact rate card should include the approved child definition and any applicable restrictions. The inventory’s $8/$6 rates and age/height wording are review inputs, not launch-ready values.

Use a small gallery that shows the course, water features and surrounding setting. Do not publish an unconfirmed hole count, expected playing time, stroller/wheelchair access or weather policy. Add these as editable factual fields awaiting approval. A customer should not have to interpret a photo as evidence of accessibility.

Group section: school visits, celebrations and fundraisers may be described using approved source content. Present possible additions such as food, ice cream, desserts and seating as inquiry options. The inventory mentions full-course reservations for groups of 20 or more; confirm threshold and terms before publishing. Prefill the event inquiry’s interest as Mini golf while allowing the visitor to change it.

Seasonal closure is a distinct state from being closed for the evening. During seasonal closure, remove same-day play implications and show approved future season information only if known. Weather or temporary closures require an explicit staff override; do not infer course status from a weather forecast. If status is unknown, provide scheduled hours plus a call link rather than pretending to know live conditions.

FAQ priorities: rates and child eligibility; final start time; season; group inquiries; weather policy once confirmed. Completion checks: no universal restaurant/golf open badge; group context survives the form handoff; approved last-start calculation matches the schedule; seasonal closure messaging appears everywhere the course is promoted.

## 9 Parties and groups page
Purpose: help an organizer picture the occasion and submit enough information for a useful response. The immediate conversion is a qualified inquiry, not a sale or guaranteed reservation.

First screen: H1 “Bring Your Group to the Oasis.” Suggested introduction: “Planning a birthday, shower, company gathering or group outing? Explore food, private-space and mini-golf options for your occasion.” Primary action: Ask About Your Event, anchored to the form. Secondary action: See the Spaces. A ready organizer must be able to reach the form immediately.

Content order: occasions served; real back-room and seasonal outdoor photographs; approved capacity and suitability; food and activity options; how planning works; short inquiry form; event FAQ. Prefer a few meaningful photographs with captions over a generic celebration image. Do not claim a private room is reserved until confirmed by staff.

Offer a simple three-step explanation: share the occasion and preferred date; staff discuss options and availability; finalize arrangements directly with the restaurant. Publish a response-time promise only if George approves and staff can meet it. Prices, deposits and minimums may be shown when established; otherwise explain that arrangements depend on the group without inventing “starting at” figures.

Distinguish on-site events from off-site catering. The old page title includes catering, but the inventory does not establish delivery, off-site service or a catering menu. Build an optional catering block that stays hidden until supported by approved facts.

The form should ask for name, preferred contact method, the selected contact detail, occasion, approximate guest count, preferred date or date flexibility, and interests in dining/private space/golf/dessert. Let visitors choose Not sure yet. Make additional notes optional. Do not require both phone and email unless staff have a justified, approved need. Do not collect payment details, detailed medical information or names of children.

After a successful submission, show a reference and explain that the request is awaiting a response and does not confirm a booking. Preserve entered values on validation or delivery errors. Offer a telephone fallback. If email delivery fails after the inquiry has been safely recorded, do not tell the visitor to repeatedly resubmit; acknowledge receipt only if staff can access the stored record and there is a defined failure alert.

Completion checks: form works server-side; duplicate clicks do not create duplicate inquiries; required fields adapt to contact method; approximate dates are accepted; source interest is retained; success, validation, storage-failure and notification-failure paths are tested with test recipients.

## 10 Specials page
Purpose: give customers an accurate reason to visit and a simple view of upcoming recurring offers. Do not make them infer terms from old promotional artwork.

First screen: H1 “Specials at the Oasis.” Suggested introduction: “See what’s coming up and plan your next visit.” The page may emphasize Today only when the approved schedule and current local time justify it. Follow with a weekly schedule, dated campaigns and relevant action buttons.

Each offer must show a name, short benefit, eligible items or inclusions, price or discount, day/date, start/end time, applicable season, dine-in/takeout restrictions and destination action. Use plain text as the authoritative presentation. Promotional images can supplement it, with equivalent information in accessible text.

Seed the admin/review data with Tuesday appetizers, Wednesday Burger Night, Thursday appetizers, Friday crab and brunch. Keep unresolved prices, eligibility and terms in draft. The conflicting burger prices must remain traceable internally. Do not average, choose the highest or automatically prefer the newest-looking graphic. Do not interpret crab cakes and crab mac and cheese as one $15 bundle without confirmation.

Distinguish “available now,” “later today,” “next Wednesday,” “paused” and “expired” if those states are displayed. For example, a Wednesday offer starting at 3 p.m. must not be marked available Wednesday morning. Inactive and expired offers should not leak through homepage cards, structured data or cached pages. A dated promotion must include a year internally even when the public format is shorter.

When no offers are approved, use a brief empty state with the regular menu and visit actions. Do not invent a special to fill a slot. Do not market specials as coupons unless actual coupon terms exist. A generic phone inquiry is better than an unsupported discount claim.

Action selection: a dine-in-only special points to Visit; an approved online-eligible offer may point to the correct provider; a pie campaign points to its dedicated flow. Never imply that a website promo automatically applies at external checkout.

Completion checks: local-time boundaries, recurrence, validity window, pause and expiry all behave correctly; one record updates every placement; advertised prices match approved values; a direct link to an expired campaign clearly states that it has ended and offers a useful alternative.

## 11 Visit and contact page
Purpose: answer the questions needed to travel successfully or contact the right person. This page is practical and should remain concise.

First screen: H1 “Plan Your Visit.” Show 2355 Schoenersville Road, Allentown, PA 18109 and 610-264-1955 as inventory-derived values to confirm. Primary action: Get Directions. Secondary action: Call Us. Include the address as text even if a map is present.

Content order: location and directions; restaurant/kitchen/breakfast hours; separate golf hours and last start; seasonal ice cream note; approved arrival information; ordinary table reservations versus group inquiries; compact visit FAQ. Include an exterior or entrance photo so visitors can recognize the real place.

Do not assume restaurant closing time is kitchen closing time. The inventory reports a 30-minute kitchen cutoff, breakfast until 2 p.m. and a 45-minute golf cutoff. Store these explicitly or as approved service offsets. Do not publish the old Summer 2026 schedule as a new year-round schedule without review.

Show a readable weekly schedule, holiday/temporary exceptions and a separate seasonal golf state. An “Open now” label must use America/New_York, an approved schedule and explicit exceptions. If accurate status cannot be established, use schedule text and a call link. Never default missing information to Open or Closed.

A map may load on demand; the text address and directions link must work without it. Confirm parking, entrance, accessible facilities and other practical facts before adding them. Do not assume property features from the map or concept art.

Ordinary table reservations must point to the owner-approved existing booking route. Groups should go to the event flow. If the provider is unavailable or unconfirmed, show the approved contact fallback. Do not send a customer to a dead Book a Table button or silently substitute a group inquiry for a confirmed reservation.

Completion checks: tel link is usable on phones; directions contain the complete address; separate service hours are consistent across pages; holiday exceptions override weekly hours; contact paths use the correct approved inbox; map loading is optional; all visible claims are sourced.

## 12 Story gallery and ordering pages
Our Story should establish who operates Oasis and why the place feels personal. H1: “The Family Behind the Oasis.” Use the source-supported connection to George and Harriet Sitaras and later generations after owner review. Favor a concise narrative with real family/restaurant photos and a clear invitation to visit. Do not repeat the undated 40th-anniversary claim or invent founding dates, milestones or quotes. One or two short sections can be sufficient if that is all the approved history supports.

Gallery should serve decisions. Group photos under Food, Ice Cream, Mini Golf, Dining Spaces and Gatherings only when enough representative images exist. Keep a manageable selection and remove duplicate photos. Captions should help visitors understand what they are viewing. A lightbox, if used, must support keyboard controls, a close button, focus return and meaningful image labels. Links beside a room or course gallery should lead to the corresponding information or inquiry page. Do not require a gallery visit to find essential facts.

Order should provide a fast handoff to existing systems. H1: “Order from George’s Oasis.” Present the configured menu/ordering provider and Grubhub delivery as distinct choices with accurate descriptions. Do not label FoodBooking as pickup-only until its actual options are verified. Describe fees, delivery coverage, order timing or availability only when supported by the provider or owner; otherwise leave those details to the provider.

Keep the transition explicit, such as “Continue to our ordering service” or “Order delivery through Grubhub.” Do not insert a marketing funnel, account creation or lead form before the handoff. Use the normal same-tab behavior unless there is a clear reason for a new tab; announce a new tab when used. If the main Order Online button would add an unnecessary intermediary, let it go directly to the approved primary provider and expose delivery as a clear alternative nearby.

Existing provider changes are outside this build. Do not implement a new cart, checkout, POS integration or payment capture simply because the marketing site is changing platforms. A provider outage should yield a helpful fallback, not fabricated order success.

Completion checks: story claims reviewed; gallery asset rights/relevance documented; all gallery actions have useful destinations; ordering and delivery links are centralized; no purchase-complete tracking fires from a mere outbound click.

## 13 Optional seasonal pie campaign
Build a reusable campaign structure, but publish the pie page only when George approves a new campaign. The existing linked form is a 2025 Thanksgiving sale and must not be reused unchanged.

An active campaign needs title, year, opening date, order deadline, pickup dates/windows, collection address, eligible flavors, prices, quantity rules, campaign capacity if maintained, confirmation method and payment process. Prefill the review sheet from the old campaign; do not publish its prices or flavors as current by default.

The page should present the deadline and pickup arrangements before the form. Let customers select quantities beside each flavor, review a readable order summary, supply contact information and choose an available pickup option. Use exact currency arithmetic. If tax, deposits or final charges are not established, do not imply that an estimated subtotal is the final amount due.

Preserve the approved existing confirmation/payment workflow. The old form promised a phone call within 24–48 hours and payment before pickup; a new campaign must obtain approval for those promises. If requests require staff acceptance, label the action Submit Pie Request and the success state Request Received. Do not claim an order is confirmed or paid until the actual workflow supports that state.

Model draft, scheduled, open, paused, sold out, closed and archived states where needed. Disable submissions after the deadline on the server as well as the page. If inventory is not genuinely maintained, do not show live stock counts. Capacity limits, when used, must be enforced during submission to prevent concurrent overbooking.

For a closed campaign, show that ordering has ended, remove active ordering actions and provide an approved contact or menu alternative. Do not reset the year automatically and reopen an old campaign. Existing direct links must not silently lead to a form with past pickup dates.

This is a later enhancement unless an active campaign is explicitly approved for this release. Do not hold the core restaurant, golf and event pages hostage to a new seasonal ordering system.

## 14 Shared data and Flask implementation
| Data area | Core fields | Where used |
|---|---|---|
| Business profile | Public name, address, telephone, approved inboxes | Header, footer, Visit, forms |
| External destinations | Provider URL, purpose, enabled flag, review date | Ordering, reservations, social, delivery |
| Service schedules | Service, timezone, weekly windows, date exceptions, seasonal state | Visit and contextual status strips |
| Menu | Categories, items, variants, prices, add-ons, approved labels | Menu, Ice Cream, related features |
| Offers | Terms, schedule, validity, eligibility, CTA destination, status | Specials and homepage placements |
| Events | Occasions, spaces, approved capacity, options, policies | Parties and inquiry form |
| Media | File, subject, alt text, credit/rights, approval, crop | All public pages |
| Inquiries | Reference, submitted fields, received time, staff state, notification state | Staff workflow and receipt |

Adapt these fields to existing project conventions rather than duplicating equivalent models. For small editorial content, validated structured files may be sufficient. If approved admin capabilities already exist, extend them with a small number of clear fields. Keep credentials and private recipient settings in appropriate server configuration, never in client JavaScript.

Centralize data access and publication rules. Templates should not contain independent copies of hours, telephone numbers, prices or provider URLs. Validate required fields before enabling content. A shared service should determine offer visibility and service status. Handle America/New_York consistently, including daylight-saving changes and date overrides. For production caches, expire or invalidate content at status boundaries so an ended offer is not kept visible.

Keep menu content public and server-rendered. JavaScript may enhance search, filters, dialogs and navigation but must not be required to discover the food or submit the essential inquiry. Reuse the existing project’s routing, database migration and form conventions. Avoid prescribing library versions without inspecting the environment.

Suggested component names include base layout, primary navigation, page introduction, service facts, menu category, menu item, offer card, photo gallery, related experience, FAQ and inquiry form. Use the current project’s naming style rather than adding a competing component hierarchy.

Preserve external ordering/reservation systems and existing integration identifiers. The legacy public site appears to use Weebly, not a WordPress front end; that observation does not establish account ownership or hosting dependencies. Do not plan deactivation or payment migration from visual platform assumptions.

## 15 Inquiry reliability and owner maintenance
Validate forms on the server, preserve safe user input on errors, and use the application’s protections against cross-site requests and spam. Apply sensible length limits, safe rendering, rate limits and a low-friction spam measure. Do not send user-provided HTML directly into notification templates. Use a configured sender and a validated Reply-To value rather than allowing arbitrary email headers.

Store an inquiry durably before treating it as received. Give it a non-sensitive reference. Separate receipt state from notification state and later staff states such as new, contacted and closed. Duplicate submission protection must cover double-clicks and retry after a timeout. The visitor should not need an account to inquire.

Notify only approved staff recipients. Keep notification content readable and include the requested date, guest count, interests and contact preference. Provide an authenticated way to review received inquiries or use an existing authorized workflow. Protect personal data from public URLs, page source, analytics and ordinary diagnostic output. Record only what staff need and document the owner-approved retention process.

When storage fails, show a truthful failure message, retain the form values where safe and offer a phone fallback. When storage succeeds but notification fails, retain the request and alert the responsible operator through the configured mechanism. Do not show a success message if nothing was saved or delivered. Test with configured test recipients and fixture data; never send unsolicited live client notifications during verification.

Make frequent owner updates small: pause an offer; change an end date; update a holiday schedule; switch golf or soft serve seasonal status; edit one menu price; change one provider URL. Show a preview before publishing when an admin interface supports it. Keep modification history or versioned source records so changes are recoverable.

No weekly content-production obligation should be required to keep the site useful. Approved evergreen content should carry the pages. Automate deterministic expiry and display rules, while reserving business judgments such as weather closures, price approval and seasonal reopening for staff.

## 16 Content depth search and measurement
Each paragraph or component should answer one of these questions: What is offered? Is it suitable for me? What will it cost? When can I do it? What will it look like? How do I proceed? If a section does none of these, remove or rewrite it. Do not pad pages to a word count.

Write distinct page titles and descriptions based on actual page content, with one descriptive H1 and clear subheadings. Include the real locality naturally where helpful. Give internal links meaningful labels. Keep public content crawlable and ensure page metadata, canonical URLs, sitemap and legacy redirects reflect the chosen routes. Exclude staging/review views and inquiry receipts from indexing.

If structured data is implemented, derive it from the same approved business information shown on the page. Do not add unsupported ratings, reviews, offers or service hours. Avoid duplicate or inconsistent business identities across pages. Verify the applicable current format during implementation rather than assuming this specification is a standards reference.

Optimize real images at appropriate responsive sizes, provide dimensions to reduce layout movement and lazy-load below-the-fold photos. Keep the main above-the-fold image available promptly. Avoid heavy social feeds, autoplay video, map loading on every page and decorative scripts that delay menu access. Prefer a curated social link or selected approved content to an unreliable feed.

If analytics is approved and configured under the owner’s account, record useful actions: menu-category selection, ordering-provider click, directions click, phone click, event-form start, successful inquiry and submission failure. Include page and service context without personal information or form field contents. An outbound click is not proof of an order, and a directions click is not proof of a visit.

Evaluate journeys using both behavior and staff feedback: can customers find the menu quickly, which pages send useful inquiries, where forms are abandoned, and which repetitive questions persist? Do not invent conversion targets or guarantee revenue improvements. The first review should establish a baseline, then prioritize concrete friction.

## 17 Verification and acceptance criteria
| Scenario | Expected result |
|---|---|
| Visitor lands directly on Menu | Food categories and ordering path are understandable without visiting Home |
| Mobile customer wants breakfast | Breakfast section and approved cutoff are easy to find and read |
| Customer looks for ice cream off season | Soft-serve status is clear; other approved desserts remain discoverable |
| Customer arrives late for golf | Last-start information prevents confusion with restaurant closing |
| Seasonal golf closure | Same status across homepage, Golf and Visit |
| Wednesday before the special starts | Offer is upcoming, not available now |
| Offer expires or is paused | Removed from all active placements and not served from stale cache |
| No approved special exists | Useful regular-menu alternative; no placeholder deal |
| Event customer is unsure of date | Can state flexibility and submit an inquiry |
| Invalid form submission | Specific errors, preserved values and accessible focus/summary |
| Duplicate click or network retry | One recorded inquiry and a consistent receipt |
| Notification outage | Saved request remains available; operator alerted; truthful visitor state |
| Missing provider configuration | No dead button; appropriate approved contact fallback |
| JavaScript disabled | Essential content, links and server-side inquiry remain usable |
| Old menu or events URL | Permanent redirect to the correct new page |

Perform focused automated checks for publication rules, schedule boundaries, holiday overrides, form validation and duplicate handling. Verify the intended daylight-saving behavior and exact start/end boundaries in local time. Test security-sensitive form paths with fixture data. Avoid tests that merely repeat template markup.

Render and inspect representative pages at narrow phone, tablet and desktop widths. Check navigation, menus, tables, long item names, form errors, dialogs, sticky controls and footer placement. Confirm no sideways scrolling, hidden essential content, clipped text, illegible image overlays or hover-only actions. Use keyboard navigation and inspect focus order, dialog escape/return and labels.

Verify internal and external destinations. Use read-only checks for external providers; do not place an order, reserve a real table or submit a live inquiry unless explicitly authorized. Check that the retained provider can be reached from the replacement application and that the handoff is explained.

A page is complete only when its visible content is populated from approved or clearly staged data, its actions work, its state handling is implemented, and its mobile presentation has been inspected. Do not call a page complete because a route renders a headline and an empty card grid.

## 18 Build sequence and Astra handoff
First inspect the existing project and report the relevant architecture briefly. Identify implemented routes, available content, current form/mail/storage capabilities and the exact design reference. Then implement shared data access and components before extending the page set. Preserve unrelated functionality.

Recommended sequence: shared business profile and navigation; Menu and Ice Cream; Visit and service schedules; Golf; Parties and inquiry reliability; Specials and expiry; Story, Gallery and ordering handoff; legacy redirects and metadata; final responsive and action-path verification. Build the optional pie campaign only if approved for the release. Use reversible migrations and document any environment variables or setup commands actually required.

Astra must provide: working source changes; route and component summary; content data files or admin-field notes; the list of owner approvals still needed; evidence of meaningful tests and rendered-page inspection; and deployment notes for the existing hosting setup. Identify limitations honestly, particularly provider behavior that could not be verified. Do not describe staging content as owner-approved.

### Copy ready instruction for Astra
Use this specification and the supplied website inventory to implement the remaining George’s Oasis pages in the existing Flask project. Read repository instructions first. Preserve the latest Concept 1 visual direction and current working application. Build actual page content and complete action paths, not placeholder sections. Reuse approved source information and store uncertain facts as drafts for one consolidated owner review. A ready visitor should be able to act near the top of every page; an undecided visitor should find the practical information and authentic photographs needed to decide. Centralize menus, hours, offers and external links; retain existing ordering and reservation providers. Implement the event inquiry workflow with accurate receipt states and failure handling. Verify phone and desktop rendering and the journeys in this document. Continue autonomously on reversible implementation decisions. Do not publish, change DNS, submit real orders or invent prices, policies, reviews or operating details. Finish with completed changes, verification evidence and the short unresolved-facts list.

### Source and asset handoff
Primary business reference: Georges_Oasis_Website_Inventory.docx, reviewed October 6, 2026, including seven original menu images and promotional graphics. It is a research inventory, not an approval record.

Visual reference: the left-hand Concept 1 in Geo-Oasis-Design-Options-3.png and the latest georges_oasis_tailwind_prototype.zip. The latest prototype follows the corrected direction; earlier Concept 2 guidance is superseded. Provide the original reference and inventory to Astra alongside this specification if they are not already in the project.

Public source pages recorded by the inventory: https://www.georgesoasis.com/ ; /menus.html ; /hours--info.html ; /mini-golf.html ; /specials.html ; /gallery.html ; /private-eventscatering.html. The inventory also contains the old pie form and its dates. Recheck volatile information when needed, but do not treat a public page refresh as owner approval.

Existing ordering URL: https://www.foodbooking.com/ordering/restaurant/menu?restaurant_uid=09ba3e4c-ea05-4d65-9653-b79805afb083

Existing delivery URL: https://www.grubhub.com/restaurant/georges-oasis-restaurant-2355-schoenersville-rd-bethlehem/5997112

Existing social URL: https://www.facebook.com/GeorgesOasisRestaurant

Inventory contact candidates: gsitaras90@gmail.com for event/group inquiries and galatou@msn.com for general contact. These are routing candidates for review, not authorization to send test messages. Configure the selected address once after confirmation. Obtain the approved ordinary table-reservation destination from the existing configuration or owner rather than inventing a new booking system.
