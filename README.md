# Kuhi Proxy

AniList GraphQL wrapper — drop-in replacement for Kuhi (`anime-api-nine-red.vercel.app`).
Outputs the exact same JSON format AnimeReza v3 expects.

## Deploy to Vercel (free)

1. Push this repo to GitHub
2. Go to vercel.com → New Project → import the repo
3. Framework: **Other** — leave everything default
4. Click Deploy

Your URL will be: `https://your-project-name.vercel.app`

## Then in AnimeReza config.php

Change one line:
```php
// in includes/api.php or wherever KUHI is defined
const KUHI = 'https://your-project-name.vercel.app';
```

## Endpoints (identical to Kuhi)

| Endpoint | Description |
|---|---|
| `/anime/spotlight` | Hero slider — top 6 trending airing |
| `/anime/trending?per_page=20` | Trending anime |
| `/anime/popular?per_page=20` | Most popular |
| `/anime/upcoming?per_page=12` | Not yet released |
| `/anime/recent?per_page=24` | Recent additions |
| `/anime/filter?sort=SCORE_DESC&status=FINISHED` | Filtered browse |
| `/anime/schedule` | Weekly schedule grouped by day |
| `/anime/search?query=blue+lock&per_page=20` | Search |
| `/anime/suggestions?query=blue` | Autocomplete suggestions |
| `/anime/info/{anilist_id}` | Full anime detail |
| `/anime/mal/{mal_id}` | Lookup by MAL ID → AniList ID |
| `/anime/episodes/{anilist_id}` | Episode list |
| `/anime/{id}/recommendations` | Recommendations |
| `/anime/{id}/relations` | Relations (sequels, prequels) |
| `/anime/{id}/characters` | Characters + voice actors |
| `/status` | Health check |

## Filter params

`sort`: `TRENDING_DESC` `POPULARITY_DESC` `SCORE_DESC` `START_DATE_DESC`
`status`: `RELEASING` `FINISHED` `NOT_YET_RELEASED`
`genre`: any genre string e.g. `Action`
`year`: e.g. `2024`
`season`: `WINTER` `SPRING` `SUMMER` `FALL`
`format`: `TV` `MOVIE` `OVA` `ONA` `SPECIAL`
