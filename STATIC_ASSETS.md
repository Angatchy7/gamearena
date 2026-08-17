# GameArena Static Assets

The project now includes optimized WebP assets for the final UI:

- `static/images/hero/gamearena_hero.webp`
- `static/images/games/*.webp`
- `static/images/defaults/*.webp`

Uploaded game logos, tournament covers/banners, and team logos continue to use the existing Cloudinary-backed Django media fields when present. Static WebP files are used as local/default fallbacks.

Fallback priority:

1. Uploaded Cloudinary media
2. Game-specific/static WebP artwork
3. Generic WebP fallback
