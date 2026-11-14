# Full menu publication — October 16, 2026

Implemented the user's request to put every published menu item on `/food-and-ice-cream`, with imagery. Publication is authorized by that request; it does not imply a new confirmation of current prices by George.

## Inventory and source

The restaurant's [published menu page](https://www.georgesoasis.com/menus.html) contains seven images in its HTML. Six match the previous local source files byte-for-byte. The seventh, `58827-dinner-menu-page-new-print-2025-v3_orig.png`, supplied the missing dinner entrées and senior selections. All seven were visually reviewed. Original files and lightweight thumbnails are now available from the menu page; their URLs, SHA-256 hashes and review date are recorded in `site.json` under `menu_sources`.

| Section | Named selections |
| --- | ---: |
| Breakfast | 56 |
| Lunch & Dinner | 80 |
| Dinner Entrées | 21 |
| Children’s Menu | 8 |
| Senior Selections | 12 |
| Ice Cream & Desserts | 30 |
| Bakery & Greek Desserts | 5 |
| Total | 212 |

Sizes, portions and alternative preparations remain attached to the relevant selection rather than being counted as separate dishes. Hard ice cream flavors, yogurt options, non-dairy milk availability, toppings and additions are included. The unpriced baklava/Greek pastry listings use “Ask for today’s price”; no price was invented. The dessert source prints both takeout malt sizes at $5.75; both values are preserved.

## Corrections made during review

Removed draft options that were indiscriminately repeated across groups: the Benedict substitution, lox egg addition, Carnitas avocado, build-your-own omelet toppings, Farmer’s Melt meat, oatmeal fruit, burger-specific cheese/bacon, steak-sandwich cheese and grilled-cheese vegetables now belong only to their applicable items. Corrected the vegan flatbread's olive oil, vegetable wrap ingredients, steak hoagie ingredients, and children's inclusions. Editorial draft warnings no longer appear as customer copy.

## Images

Used actual restaurant photographs from [its gallery](https://www.georgesoasis.com/gallery.html), optimized as WebP. Categories have genuine food or dining-space imagery; individual matching photographs are attached to avocado toast, vegetable flatbread, shrimp, soft serve and baklava. Not every dish has a distinct photograph available. No stock or generated dish photographs were substituted. The optional image-preference question received no answer during implementation, so the stated default of real category imagery was used.

Each new photo's source URL and descriptive alternative text is retained with its record. All seven printed menu images are also visible as clickable thumbnails. Source originals load only when opened; thumbnails and lower-page photos are lazy loaded.

## Behavior and verification

- Full menu is rendered by Flask and available without JavaScript. Search progressively enhances it, matches item names, descriptions, groups and category names, and announces result counts.
- Category navigation clears search before jumping to the selected section. Options remain native keyboard-accessible disclosures.
- Dessert page reuses the same published records, preventing a second set of prices.
- 35 Python tests passed, including complete inventory/source assets, publication filtering, accurate options, missing-price behavior, internal links and shared dessert content.
- Content validation passed; `git diff --check` passed.
- Chromium checks at 320, 390, 768 and 1440 px passed: 212 items, seven categories, loaded images, no horizontal overflow, search/reset/no-results, category navigation and keyboard disclosure operation.
- 200% root text size, reduced motion and no-JavaScript visibility checks passed.
- No production deployment or live order was performed. Prices reflect the restaurant's published menus as checked on the date above.
