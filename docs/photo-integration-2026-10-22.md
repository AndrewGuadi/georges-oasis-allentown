# Responsive photo integration — October 22, 2026

Integrated the user-supplied `build_docs/Georges-Oasis-Responsive-Photos.zip` into the existing Flask website. Reviewed the package README, placement/integration notes, public asset manifest and a contact sheet of 52 base subjects. The bundle supplies 101 source-photo records and 303 WebP variants. All variants are installed under `static/images/oasis/`; pages render a curated selection rather than the entire collection.

## Placement decisions

| Area | Integration |
| --- | --- |
| Homepage hero | Sunny daytime dining room, replacing the exterior/car/pavement background. Family-recipe message and Menu/Visit actions retained. |
| Four experience cards | French toast, golfers at the waterfall, sundae, outdoor gathering. The group portrait uses a whole-image frame. |
| Homepage kitchen | Window-side dining tables accompany the tomato-soup recipe copy. The collection has no confirmed soup image, so neither a burger nor an unrelated food photo represents that dish. |
| Homepage gatherings | One actual outdoor gathering replaces the composite image; guests remain in frame. |
| Homepage golf | Players at the waterfall, with the full landscape retained. |
| Menu | Food-spread introduction and relevant breakfast, lunch, dinner, children/senior dining-space and dessert category imagery. All 212 selections, prices and ordering behavior retained. Only a generic soft-serve photo is newly attached to an individual menu item; precise unconfirmed specialty names were not inferred from pictures. |
| Mini golf | Scenic bridge/pond hero; three distinct scenic/player photographs. Existing lightbox opens the new full-size exports. |
| Ice cream | Sundae introduction, soft-serve cone and outdoor seating photographs. Existing availability guidance retained. |
| Gatherings | Window-table introduction, buffet arrangement, outdoor guests and a decorated indoor celebration shown separately. |
| Visit | Responsive exterior recognition image, entrance welcome detail and outdoor tables. No parking/access claims inferred from photographs. |
| Our Story | Existing historic family image retained. Current dining room and family décor added. No new names or historical facts inferred. |
| Specials | Burger photo supports the general introduction; no archived chalkboard offers are published as current specials. |
| Gallery | 25 photographs across the five existing categories, with specific captions. Seven distinct food views, two dessert views, three course views, three gathering views, seven atmosphere details and the preserved historic photograph. Shortened introduction brings photos higher. |
| Order | One actual burger-and-fries photograph follows the existing provider choices. |
| Sharing | The daytime dining-room photo is used for social previews and the homepage Restaurant image. |

## Rendering and maintenance

`georges_oasis/oasis_images.py` registers the public manifest once per application startup. The included `oasis_image` macro emits accurate width descriptors and deduplicates equal source widths for smaller originals. `site_image` also supports the existing optimized-image filenames so historic and previously published assets remain usable.

Photos include dimensions, descriptive alternatives or an empty alternative for the decorative homepage background, responsive `srcset`/`sizes`, and lazy loading below the introduction. Only a page's main introduction image is marked eager/high priority. The old homepage background/preload was removed to prevent a second hero download. Homepage/social placement keys live in `site.json` under `photo_placements`; restart Flask after replacing the image manifest.

The source IDs, source hashes and private source manifest remain in the original archive, outside the public static directory. The archive, originals and historical family photograph were preserved. Near-duplicate, seasonal Easter, old chalkboard and photographed menu-display images are available in the bundle but not selected for public galleries.

## Verification

- 37 Python tests passed, including manifest/file dimensions and byte counts for all 303 variants, unique/accurate `srcset` descriptors for all 101 assets, public rendering and source paths, priority/lazy-loading behavior, and preservation of the complete menu.
- Content validation and Git whitespace checks passed.
- Browser review covered all ten public pages at phone, tablet and desktop widths; final browser results are recorded with the local review artifacts in `/tmp/oasis-photo-review`.

Outstanding content: a real photograph of Homemade Tomato Soup or its preparation; identification/caption details for the historic family photograph. No missing business schedules, specials or recipe-history details were invented. No deployment or external publication was performed.

Final browser results: all ten public pages passed at 320, 390, 768, 1024 and 1440 px (50 route/viewport combinations), with loaded photos and no horizontal overflow. A 320×568 check kept both homepage actions above the mobile dock. Independent browser contexts selected mobile, tablet and desktop hero variants at the expected widths; the old exterior background was not requested. Golf lightbox navigation/Escape/focus return and the 212-item menu search passed. Desktop and mobile screenshots were visually reviewed.
