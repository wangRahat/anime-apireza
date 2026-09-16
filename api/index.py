from http.server import BaseHTTPRequestHandler
import json, urllib.request, urllib.parse, re, time

ANILIST = 'https://graphql.anilist.co'

# ─── AniList field sets ───────────────────────────────────────────

ANIME_FIELDS = """
  id idMal
  title { romaji english native }
  status format episodes duration
  description(asHtml: false)
  season seasonYear
  averageScore popularity
  genres hashtag isAdult source siteUrl
  coverImage { extraLarge large medium }
  bannerImage
  startDate { year month day }
  endDate   { year month day }
  nextAiringEpisode { airingAt timeUntilAiring episode }
  studios { nodes { id name isAnimationStudio } }
  trailer { id site }
"""

DETAIL_EXTRA = """
  tags            { name rank isMediaSpoiler category }
  externalLinks   { site url }
  streamingEpisodes { title thumbnail url site }
  rankings        { rank type context season year allTime }
  staff(perPage:8, sort:RELEVANCE) {
    edges {
      role
      node { id name { full native } image { large } }
    }
  }
"""

# ─── GraphQL helper ───────────────────────────────────────────────

def gql(query, variables=None):
    payload = json.dumps({'query': query, 'variables': variables or {}}).encode()
    req = urllib.request.Request(
        ANILIST,
        data=payload,
        headers={'Content-Type': 'application/json', 'Accept': 'application/json',
                 'User-Agent': 'KuhiProxy/1.0'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception:
        return None

# ─── Normalizer — output matches what v3 normalizeKuhi() expects ──

def to_kuhi(a):
    if not a:
        return None
    return {
        'id':                a.get('id'),
        'idMal':             a.get('idMal'),
        'title':             a.get('title', {}),
        'status':            a.get('status'),
        'format':            a.get('format'),
        'episodes':          a.get('episodes'),
        'duration':          a.get('duration'),
        'description':       a.get('description', ''),
        'season':            a.get('season'),
        'seasonYear':        a.get('seasonYear'),
        'averageScore':      a.get('averageScore'),
        'popularity':        a.get('popularity'),
        'genres':            a.get('genres', []),
        'hashtag':           a.get('hashtag'),
        'isAdult':           a.get('isAdult', False),
        'source':            a.get('source'),
        'siteUrl':           a.get('siteUrl'),
        'coverImage':        a.get('coverImage', {}),
        'bannerImage':       a.get('bannerImage'),
        'startDate':         a.get('startDate', {}),
        'endDate':           a.get('endDate', {}),
        'nextAiringEpisode': a.get('nextAiringEpisode'),
        'studios':           a.get('studios', {'nodes': []}),
        'tags':              a.get('tags', []),
        'externalLinks':     a.get('externalLinks', []),
        'streamingEpisodes': a.get('streamingEpisodes', []),
        'rankings':          a.get('rankings', []),
        'staff':             a.get('staff', {'edges': []}),
        'trailer':           a.get('trailer'),
    }

def page_resp(raw, key='media'):
    if not raw:
        return {'results': [], 'total': 0, 'totalPages': 1}
    page    = raw.get('data', {}).get('Page', {})
    items   = [to_kuhi(a) for a in page.get(key, []) if a]
    pg      = page.get('pageInfo', {})
    return {
        'results':     items,
        'total':       pg.get('total', len(items)),
        'totalPages':  pg.get('lastPage', 1),
        'currentPage': pg.get('currentPage', 1),
    }

# ─── Route handlers ───────────────────────────────────────────────

def spotlight(p):
    q = """query{Page(page:1,perPage:6){
      media(sort:TRENDING_DESC,status:RELEASING,type:ANIME,isAdult:false){%s}
    }}""" % ANIME_FIELDS
    raw   = gql(q)
    items = [to_kuhi(a) for a in
             (raw or {}).get('data', {}).get('Page', {}).get('media', []) if a]
    return {'results': items}

def trending(p):
    q = """query($pg:Int,$pp:Int){Page(page:$pg,perPage:$pp){
      pageInfo{total lastPage currentPage}
      media(sort:TRENDING_DESC,type:ANIME,isAdult:false){%s}
    }}""" % ANIME_FIELDS
    return page_resp(gql(q, {'pg': int(p.get('page', 1)),
                              'pp': min(int(p.get('per_page', 20)), 50)}))

def popular(p):
    q = """query($pg:Int,$pp:Int){Page(page:$pg,perPage:$pp){
      pageInfo{total lastPage currentPage}
      media(sort:POPULARITY_DESC,type:ANIME,isAdult:false){%s}
    }}""" % ANIME_FIELDS
    return page_resp(gql(q, {'pg': int(p.get('page', 1)),
                              'pp': min(int(p.get('per_page', 20)), 50)}))

def upcoming(p):
    q = """query($pg:Int,$pp:Int){Page(page:$pg,perPage:$pp){
      pageInfo{total lastPage currentPage}
      media(sort:POPULARITY_DESC,status:NOT_YET_RELEASED,type:ANIME,isAdult:false){%s}
    }}""" % ANIME_FIELDS
    return page_resp(gql(q, {'pg': int(p.get('page', 1)),
                              'pp': min(int(p.get('per_page', 20)), 50)}))

def recent(p):
    q = """query($pg:Int,$pp:Int){Page(page:$pg,perPage:$pp){
      pageInfo{total lastPage currentPage}
      media(sort:START_DATE_DESC,type:ANIME,isAdult:false){%s}
    }}""" % ANIME_FIELDS
    return page_resp(gql(q, {'pg': int(p.get('page', 1)),
                              'pp': min(int(p.get('per_page', 20)), 50)}))

def filter_anime(p):
    sort_map = {
        'TRENDING_DESC':   'TRENDING_DESC',
        'POPULARITY_DESC': 'POPULARITY_DESC',
        'SCORE_DESC':      'SCORE_DESC',
        'START_DATE_DESC': 'START_DATE_DESC',
        'UPDATED_AT_DESC': 'UPDATED_AT_DESC',
    }
    sort   = sort_map.get(p.get('sort', 'POPULARITY_DESC'), 'POPULARITY_DESC')
    pg     = int(p.get('page', 1))
    pp     = min(int(p.get('per_page', 20)), 50)

    decls   = ['$pg:Int', '$pp:Int', '$sort:[MediaSort]']
    vals    = {'pg': pg, 'pp': pp, 'sort': [sort]}
    filters = ['type:ANIME', 'isAdult:false', 'sort:$sort']

    def add(key, gql_name, gql_type, cast=str):
        if p.get(key):
            decls.append(f'${key}:{gql_type}')
            vals[key] = cast(p[key])
            filters.append(f'{gql_name}:${key}')

    add('status', 'status',     'MediaStatus')
    add('genre',  'genre',      'String')
    add('year',   'seasonYear', 'Int',   int)
    add('season', 'season',     'MediaSeason')
    add('format', 'format',     'MediaFormat')

    q = """query(%s){Page(page:$pg,perPage:$pp){
      pageInfo{total lastPage currentPage}
      media(%s){%s}
    }}""" % (', '.join(decls), ', '.join(filters), ANIME_FIELDS)
    return page_resp(gql(q, vals))

def schedule(p):
    q = """query{Page(page:1,perPage:40){
      media(sort:POPULARITY_DESC,status:RELEASING,type:ANIME,isAdult:false){%s}
    }}""" % ANIME_FIELDS
    raw   = gql(q)
    items = [to_kuhi(a) for a in
             (raw or {}).get('data', {}).get('Page', {}).get('media', []) if a]

    days = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
    sched = {d: [] for d in days}
    sched['tba'] = []

    for item in items:
        nae = item.get('nextAiringEpisode')
        if nae and nae.get('airingAt'):
            # strftime %w: 0=Sunday … 6=Saturday
            dow = int(time.strftime('%w', time.gmtime(nae['airingAt'])))
            day = days[dow - 1] if dow > 0 else days[6]
            sched[day].append(item)
        else:
            sched['tba'].append(item)

    return {'schedule': sched, 'results': items}

def anime_info(anilist_id):
    q = """query($id:Int){Media(id:$id,type:ANIME){%s %s}}
    """ % (ANIME_FIELDS, DETAIL_EXTRA)
    raw = gql(q, {'id': int(anilist_id)})
    a   = (raw or {}).get('data', {}).get('Media')
    return to_kuhi(a) if a else None

def anime_mal(mal_id):
    q = """query($mal:Int){Media(idMal:$mal,type:ANIME){
      id idMal title{romaji english}
    }}"""
    raw = gql(q, {'mal': int(mal_id)})
    a   = (raw or {}).get('data', {}).get('Media')
    if not a:
        return None
    return {'id': a['id'], 'idMal': a['idMal'],
            'anilistId': a['id'], 'title': a.get('title', {})}

def search(p):
    query = p.get('query', '').strip()
    if not query:
        return {'results': [], 'total': 0, 'totalPages': 1}
    q = """query($s:String,$pg:Int,$pp:Int){Page(page:$pg,perPage:$pp){
      pageInfo{total lastPage currentPage}
      media(search:$s,type:ANIME,isAdult:false,sort:SEARCH_MATCH){%s}
    }}""" % ANIME_FIELDS
    return page_resp(gql(q, {
        's':  query,
        'pg': int(p.get('page', 1)),
        'pp': min(int(p.get('per_page', 20)), 50),
    }))

def suggestions(p):
    query = p.get('query', '').strip()
    if not query:
        return {'results': []}
    q = """query($s:String){Page(page:1,perPage:8){
      media(search:$s,type:ANIME,isAdult:false,sort:SEARCH_MATCH){%s}
    }}""" % ANIME_FIELDS
    raw   = gql(q, {'s': query})
    items = [to_kuhi(a) for a in
             (raw or {}).get('data', {}).get('Page', {}).get('media', []) if a]
    return {'results': items}

def episodes(anilist_id):
    q = """query($id:Int){Media(id:$id,type:ANIME){
      id episodes
      streamingEpisodes { title thumbnail url site }
      airingSchedule(notYetAired:false,perPage:150){
        nodes { episode airingAt }
      }
    }}"""
    raw = gql(q, {'id': int(anilist_id)})
    m   = (raw or {}).get('data', {}).get('Media', {})
    if not m:
        return {'episodes': []}

    stream_eps = m.get('streamingEpisodes', [])
    eps = []
    if stream_eps:
        for i, ep in enumerate(stream_eps, 1):
            eps.append({
                'number':    i,
                'episode':   i,
                'title':     ep.get('title', f'Episode {i}'),
                'thumbnail': ep.get('thumbnail', ''),
            })
    else:
        total = m.get('episodes') or 0
        for i in range(1, total + 1):
            eps.append({'number': i, 'episode': i,
                        'title': f'Episode {i}', 'thumbnail': ''})

    return {'episodes': eps, 'total': len(eps)}

def recommendations(anilist_id, p):
    pp = min(int(p.get('per_page', 16)), 25)
    q  = """query($id:Int,$pp:Int){Media(id:$id,type:ANIME){
      recommendations(perPage:$pp,sort:RATING_DESC){
        nodes { mediaRecommendation{%s} }
      }
    }}""" % ANIME_FIELDS
    raw   = gql(q, {'id': int(anilist_id), 'pp': pp})
    nodes = ((raw or {}).get('data', {}).get('Media', {})
             .get('recommendations', {}).get('nodes', []))
    items = [to_kuhi(n['mediaRecommendation'])
             for n in nodes if n.get('mediaRecommendation')]
    return {'results': items}

def relations(anilist_id):
    q = """query($id:Int){Media(id:$id,type:ANIME){
      relations{
        edges{
          relationType(version:2)
          node{%s}
        }
      }
    }}""" % ANIME_FIELDS
    raw   = gql(q, {'id': int(anilist_id)})
    edges = ((raw or {}).get('data', {}).get('Media', {})
             .get('relations', {}).get('edges', []))
    out = []
    for e in edges:
        node = e.get('node')
        if node:
            out.append({'relationType': e.get('relationType'),
                        'node': to_kuhi(node)})
    return {'edges': out}

def characters(anilist_id, p):
    pp = min(int(p.get('per_page', 25)), 25)
    q  = """query($id:Int,$pp:Int){Media(id:$id,type:ANIME){
      characters(perPage:$pp,sort:ROLE){
        edges{
          role
          node{
            id
            name { full native }
            image { large }
            description gender age
          }
          voiceActors(language:JAPANESE){
            id
            name { full native }
            image { large }
            languageV2
          }
        }
      }
    }}"""
    raw   = gql(q, {'id': int(anilist_id), 'pp': pp})
    edges = ((raw or {}).get('data', {}).get('Media', {})
             .get('characters', {}).get('edges', []))
    return {'edges': edges}

# ─── Router ───────────────────────────────────────────────────────

def route(path, p):
    path = path.rstrip('/')

    if path == '/anime/spotlight':                    return spotlight(p)
    if path == '/anime/trending':                     return trending(p)
    if path == '/anime/popular':                      return popular(p)
    if path == '/anime/upcoming':                     return upcoming(p)
    if path == '/anime/recent':                       return recent(p)
    if path == '/anime/filter':                       return filter_anime(p)
    if path == '/anime/schedule':                     return schedule(p)
    if path == '/anime/search':                       return search(p)
    if path == '/anime/suggestions':                  return suggestions(p)

    m = re.fullmatch(r'/anime/info/(\d+)', path)
    if m:
        r = anime_info(m.group(1))
        return (r, 200) if r else ({}, 404)

    m = re.fullmatch(r'/anime/mal/(\d+)', path)
    if m:
        r = anime_mal(m.group(1))
        return (r, 200) if r else ({}, 404)

    m = re.fullmatch(r'/anime/episodes/(\d+)', path)
    if m:                                             return episodes(m.group(1))

    m = re.fullmatch(r'/anime/(\d+)/recommendations', path)
    if m:                                             return recommendations(m.group(1), p)

    m = re.fullmatch(r'/anime/(\d+)/relations', path)
    if m:                                             return relations(m.group(1))

    m = re.fullmatch(r'/anime/(\d+)/characters', path)
    if m:                                             return characters(m.group(1), p)

    if path in ('', '/', '/status'):
        return {'status': 'ok', 'version': '1.0.0', 'source': 'AniList GraphQL'}

    return ({}, 404)

# ─── Vercel WSGI handler ──────────────────────────────────────────

class handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # silence Vercel access log

    def _respond(self, body, status=200):
        payload = json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type',                  'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin',   '*')
        self.send_header('Access-Control-Allow-Methods',  'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers',  'Content-Type')
        self.send_header('Content-Length',                str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self):
        self._respond({})

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path   = parsed.path
        params = dict(urllib.parse.parse_qsl(parsed.query))
        result = route(path, params)

        if isinstance(result, tuple):
            body, status = result
        else:
            body, status = result, 200

        self._respond(body, status)
