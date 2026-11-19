# Jam Lab redesign

Astro static site for https://jamlaboratory.com.

## Install

1. Upload these files into the root of the existing `JamLaboratory/Jam-Lab` GitHub repository, **preserving the existing `public/fonts/` folder** (the zip does not contain font binaries).
2. Run `npm install` and `npm run build` to test locally, or allow Cloudflare Pages to deploy from `main` with build command `npm run build` and output directory `dist`.
3. For safety, upload to a new GitHub branch first if possible, then merge after preview.

## Publishing content

Edit `src/lib/content.js` to add reviews, articles, or rankings. The arrays start empty intentionally; the site does not fabricate content. Body fields are arrays of paragraph strings. Image fields are site-relative paths such as `/images/album.jpg`; upload licensed images to `public/images/`.

A review score uses exactly five numeric values (composition, writing, performance, production, intangibles), each 1.0–10.0, with equal weighting. Use one decimal place. The overall score is calculated automatically.

A ranking retains its slug and `published` date when edited; set `updated` for meaningful changes. Set `bumped` to a date to move a significantly revised ranking to the top of the archive. Set `featured:true` to include it on the homepage.

Example review object:

```js
{
 slug:'example-album', artist:'Example Artist', album:'Example Album', year:2026,
 genre:'Rock', published:'2026-11-18', cover:'/images/example.jpg',
 scores:{composition:8.0,writing:8.5,performance:9.0,production:8.0,intangibles:8.5},
 body:['Opening paragraph.','Another paragraph.']
}
```

**Note:** The example is documentation only, not a published review. `public/fonts/` must be retained from the current site. Verify the Anchor Jack web embedding license. Homepage and About copy are based on approved conversational drafts and can be adjusted at any time.
