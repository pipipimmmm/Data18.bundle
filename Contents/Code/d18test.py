# -*- coding: utf-8 -*-

import random
import re, math
import urllib
import traceback
import datetime
from collections import namedtuple
from functools import reduce

VERSION_NO    = '1.2016.07.24.1'

DEV           = True # Set to false on a real Plex Media Server.
if DEV: from dev import *

REQUEST_DELAY = 0 # Delay used when requesting HTML
CACHE_TIME    = CACHE_1DAY
USER_AGENT    = ''.join(['Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.2; ',
                         'Trident/4.0; SLCC2; .NET CLR 2.0.50727; ',
                         '.NET CLR 3.5.30729; .NET CLR 3.0.30729; ',
                         'Media Center PC 6.0)'])

if not DEV:
    def request_html(url):
        return HTML.ElementFromURL(
                url, sleep = REQUEST_DELAY, cacheTime = CACHE_TIME,
                headers = {'Accept-Encoding':'gzip'})

INIT_SCORE   = 100    # Starting value for score before deductions are taken.
GOOD_SCORE   = 98     # Score required to short-circuit matching and stop searching.
MORE_SCORE   = 66     # Pull more info for movies >= this score.
IGNORE_SCORE = 45     # Any score lower than this will be ignored.
DATE_SCORE_BASE = 2/3 * math.e  # The power to raise the date (year) difference to.
SCENE_SCORE_ADD = 10  # Score to add for a correct scene number.
SCENE_SCORE_ACTOR_ADD = 5 # Score to add for a correct actor in scene.

REPLACEMENTS = {':': [u"\uff1a", u"\uA789"], '-': [u"\u2014"], '.': [u"\uFE52"]}

D18_MODE_STRINGS = ['content', 'movies', 'scenes']

# Let's be super fault tolerant in accepted input:
D18_FIXED_SEARCH = re.compile(
    r'(?:http\:\/\/)?(?:www\.)?(?:data18)?(?:\.com)?\/?' +
    r'(content|movies?|scenes?)/(\d+)(?:/(\d+))?', flags = re.I)

D18_BASE_URL     = 'http://www.data18.com/'
D18_MOVIE_INFO   = D18_BASE_URL + 'movies/%s'
D18_CONTENT_INFO = D18_BASE_URL + 'content/%s'
D18_MODE_URL     = [D18_CONTENT_INFO, D18_MOVIE_INFO, D18_CONTENT_INFO]

D18_SEARCH_URL        = D18_BASE_URL + 'search/?k=%s&t=0'
D18_CONNECTIONS_URL   = D18_BASE_URL + 'connections/?v1=%s&v2=%s'
D18_CONNECTIONS_LIMIT = 5

D18_PHOTOSET_REF = D18_BASE_URL + 'viewer/%s/01'

IMAGE_PROXY_URL = Prefs['imageproxyurl']
IMAGE_MAX       = int(Prefs['sceneimg']  or 10)

REGEX   = {
    'CONN': re.compile(r"\s+in\s+", flags = re.I),
}

XPATHS2 = {
    # Searching:
    'SEARCH_CONTENT':  '//div[div/p/a/img[@class="yborder"]]',
    'SEARCH_MOVIE':    '//div[a/img[@class="yborder"]]',
    'SEARCH_SCENES':   '//div[p/span[@class="gen"]/b[contains(text(), "Scene %s")]]',
    'SCENES_STARRING': '//p[contains(text(), "Starring")]//a/text()',
    'SEARCH_CONNS':    '//div/div/div[p[contains(text(), "Results:")]]/span[position() <= %s]/a/@href' % D18_CONNECTIONS_LIMIT,
    'SCENE_MOVIE_FIX': '//div[following-sibling::div[p[contains(text(), "Related Movie")]]]//a',

    # Collection:
    'NETWORK': '//a[contains(@href,"http://www.data18.com/sites/") and following-sibling::i[position()=1][text()="Network"]]',
    'SITE':    '//a[contains(@href,"http://www.data18.com/sites/") and following-sibling::i[position()=1][text()="Site"]]',
    'STUDIO':  '//a[contains(@href,"http://www.data18.com/studios/") and following-sibling::i[position()=1][text()="Studio"]]',
    'SERIE':   '//a[contains(@href,"/series/") and preceding-sibling::b[contains(text(), "Serie")]]',

    # Summary:
    'SUMMARY': '//*[b[contains(text(),"%s:")]]',

    # People:
    'DIRECTOR':       '//p[b[contains(text(),"Director:")]]/a[2]/text()',
    'ACTOR_MOVIE':    '//div[p/span[contains(text(), "Cast of")]]//img[@class="yborder"]',
    'ACTOR_CONTENT':  '//div[p/b[contains(text(), "Who\'s Who")]]//ul/li/a/img[@class="yborder"]',
    'ACTOR_DEV':      '//div[p/b[contains(text(), "Who\'s Who")]]//p[b[contains(text(), "Dev")]]/a/text()',
    'ACTOR_FALLBACK': '//p[b[contains(text(), "Starring")]]/a/text()',

    # Genre:
    'GENRE_CONTENT':  '//div[b[contains(text(),"Categories")]]/div/a/text()',
    'GENRE_MOVIE':    '//p[b[contains(text(),"Categories")]]/a/text()',

    # Duration:
    'DURATION':       '//p[b[contains(text(), "Movie Length")]]/text()',
    'DURATION2':      '//p[contains(text(), "Duration")]/b',

    # Images:
    'POSTER_MAIN':       "id('moviewrap')/img",
    'POSTER_MAIN_MOVIE': '//a[@rel="covers"]/img[contains(@alt, "Cover")]',
    'MOV_PHOTOS_LIST':   '//img[@class="yborder" and contains(@alt, "scene Array")]',
    'MOV_PHOTOS_COUNT':  '//div[@class="p8 mt5"]//span[1][contains(text(), " Pictures")]/text()',
    'MOV_PHOTOS_REF':    '//div[@class="p8 mt5"]//a[span[1][contains(text(), " Pictures")]]',
    'VIDEOSTILLS_COUNT': '//p[span/b[contains(text(), "Video Stills")]]/b',
    'VIDEOSTILLS_OLD':   '//div[div[contains(text(), "Video Stills")]]//img',
    'QUICKTIMELINE_OLD': '//div[div[span[contains(text(), "Quick Timeline")]]]//img',
    'PHOTOSET_COUNT':    '//p[span/b[contains(text(), "Photo Set")]]/b',
    'PHOTOSET_LIST':     '//a[contains(@href, "http://www.data18.com/viewer/")]/img',

    # Release date:
    'RELEASE_DATE1':  '//p[text()[contains(translate(.,"relasdt","RELASDT"),"RELEASE DATE")]]//a',
    'RELEASE_DATE2': '//*[span[contains(text(),"Release date")]]//a[@title="Show me all updates from this date"]',
    'RELEASE_DATE3': '//*[span[contains(text(),"Release date")]]/span[@class="gen11"]/b',
    'RELEASE_DATEU': '//*[span[contains(text(),"Release date")]]/span[@class="gen11"]/i',
    'RELEASE_DATEM': '//p[contains(text(),"Release date")]',
}

def Start():
    #HTTP.ClearCache()
    HTTP.CacheTime = CACHE_1DAY
    HTTP.SetHeader('User-agent', USER_AGENT)
    HTTP.Headers['Accept-Encoding'] = 'gzip'

def clog(cond, log):
    if cond: Log(log)

def log_header( header ):
    Log('Data18 Version : ' + VERSION_NO)
    Log('************** ' + header + ' ****************')

def log_section():
    Log('-----------------------------------------------------------------------')

def make_result(_id, _name, _score, _lang, _thumb = None):
    return MetadataSearchResult(id = _id, name = _name, score = _score,
                                lang = _lang, thumb = _thumb)

def join_slug(parts): return '-'.join(parts)

def request_data_html(mode, id):
    return request_html(D18_MODE_URL[mode] % id)

def try_lam(lam, *args):
    try:    return lam(*args)
    except: return None

def try_lam2(lam, *args):
    try:
        return lam(*args)
    except:
        traceback.print_exc()
        return None

def try_xpath_direct(node, xpath):
    return try_lam(lambda: node.xpath(xpath)[0].text_content().strip())

def norm_text_xpath(node, xpath):
    return normalize_ws(try_xpath_direct(node, xpath))

def parse_document_network(node): return norm_text_xpath(node, XPATHS2['NETWORK'])
def parse_document_studio(node):  return norm_text_xpath(node, XPATHS2['STUDIO'])
def parse_document_site(node):    return norm_text_xpath(node, XPATHS2['SITE'])
def parse_document_serie(node):   return norm_text_xpath(node, XPATHS2['SERIE'])

def parse_document_title(html):
    return normalize_ws(html.xpath('//div/h1/text()')[0].strip())

def date_from_string(string):
    try:
        return Datetime.ParseDate(string).date()
    except:
        try:
            return datetime.datetime.strptime(string, '%B %d, %Y').date().replace(day=1)
        except:
            return datetime.datetime.strptime(string, '%B, %Y').date().replace(day=1)

def xp_first_text(nodes): return nodes and nodes[0].text_content().strip()

def parse_document_date(html):
    try:
        if string_xpath(html, XPATHS2['RELEASE_DATEU']):
            return None

        try:
            year = xp_first_text(html.xpath(XPATHS2['RELEASE_DATE1']))
            date = re.search(r'(\d{8})', year).group(0)
            return date_from_string(curdate)
        except:
            try:
                date = xp_first_text(html.xpath(XPATHS2['RELEASE_DATE2']))
                return date_from_string(date)
            except:
                date = xp_first_text(html.xpath(XPATHS2['RELEASE_DATE2']))
                return date_from_string(date)
    except:
        string  = xp_first_text(html.xpath(XPATHS2['RELEASE_DATEM']))
        return date_from_string(string.rsplit(':')[-1].strip())

def format_search_title(title, curdate, extras = []):
    if title.count(', The'):
        title = 'The ' + title.replace(', The', '', 1)

    extra = '/'.join([e for e in extras if e])
    extra = ', '.join([e for e in [str(curdate), extra] if e]).strip()

    if len(extra) > 0:
        title = title + ' (' + extra + ')'

    return title.strip()

class SearchMode(object):
    def __init__(self, mode, id, sid = None):
        self.mode = mode
        self.id   = int(id)
        self.sid  = int(sid) if sid else None

    def is_content(self): return self.mode == 0
    def is_movie(self):   return self.mode == 1
    def is_scene(self):   return self.mode == 2
    def scene_id(self):   return self.sid
    def __str__(self):    return self.slug()
    def __repr__(self):   return self.slug()
    def slug(self):
        mstr = D18_MODE_STRINGS[self.mode]
        end  = [str(self.sid)] if self.is_scene() else []
        return join_slug([mstr, str(self.id)] + end)

    def url(self):
        mstr = D18_MODE_STRINGS[1 if self.mode == 1 else 0]
        end  = [str(self.sid)] if self.is_scene() else []
        return D18_BASE_URL + '/'.join([mstr, str(self.id)] + end)

    def combine(self, scene): return SearchMode(2, self.id, scene.id)
    def scene_mov(self): return SearchMode(1, self.sid)

    @staticmethod
    def from_slug(slug):
        RE = re.compile(r'[^a-zA-Z0-9]', flags = re.I)
        parts = RE.split(slug, 2)

        if len(parts) < 2: return SearchMode(0, parts[0])
        try:
            mode = D18_MODE_STRINGS.index(parts[0])
        except:
            mode = D18_MODE_STRINGS.index(parts[0] + 's')
        id    = parts[1]
        sid   = parts[2] if len(parts) > 2 else None
        return SearchMode(mode, id, sid)

# Find and normalize search mode:
def determine_search_fixed(test, c = True):
    def log(s): clog(c, s)

    test_parts = test.rsplit('/')
    if all(x.isdigit() for x in test_parts):
        if len(test_parts) == 1:
            log('Search needle is numeric, assuming: content/<id>')
            return SearchMode(0, test_parts[0], None)
        else:
            log('Search needle is <id>/<id>, assuming: scene/<content-id>/<movie-id>')
            return SearchMode(2, test_parts[0], test_parts[1])

    log('Attempting search via regex, D18_FIXED_SEARCH')
    rmatch = D18_FIXED_SEARCH.match(test)
    if not rmatch:
        log('No match with regex')
        return None

    log('Found via regex, D18_FIXED_SEARCH')
    (mode, id, sid) = rmatch.groups()
    try:
        mode = 0 if sid else D18_MODE_STRINGS.index(mode)
    except: 
        mode = D18_MODE_STRINGS.index(mode + 's')

    return SearchMode(mode, id, sid)

# Handle fixed URLs & IDs.
def search_fixed(results, test, lang = None):
    smode = determine_search_fixed(test)
    if not smode:
        log_section()
        return False

    Log("search_fixed: %s" % smode )

    # Fetch HTML for primary:
    html = request_data_html(1 if smode.is_movie() else 0, smode.id)

    curdate = parse_document_date(html)
    network = parse_document_network(html)
    site    = parse_document_site(html)
    title   = parse_document_title(html)
    title   = format_search_title(title, curdate, [network, site])

    Log('search_fixed found: %s' % title)

    # Make sure movie ID is correct, should throw otherwise.
    if smode.is_scene():
        movie_title = parse_document_title(request_data_html(1, smode.sid))
        Log('belongs to movie with title:  %s' % movie_title )

    # Set the result
    results.Append(make_result(smode.slug(), title, 100, lang))
    log_section()
    return True

# Normalize the name:
def normalize_name(name):
    stripped = str(String.StripDiacritics(name))
    return name if len(stripped) == 0 else stripped

def attr_if(node, query, attr):
    r = node.xpath(query)
    r = r and r[0].get(attr)
    r = r and r.strip()
    return r

def anchor_xpath(source, query):    return attr_if(source, query, 'href')
def image_url_xpath(source, query): return attr_if(source, query, 'src')
def alt_xpath(source, query):       return attr_if(source, query, 'alt')

def string_xpath(source, query):
    node = source.xpath('string(' + query + ')')
    return node.strip() if node else None

TempResult = namedtuple('TempResult',
    ['score', 'smode', 'url', 'title', 'date', 'thumb',
     'site', 'network', 'studio', 'format_title'])

CompareData = namedtuple('CompareData', ['title', 'year'])

def movie_html_extras(smode):
    html    = request_data_html(smode.mode, smode.id)
    site    = parse_document_site(html)
    studio  = parse_document_studio(html)
    network = parse_document_network(html)
    return (html, site, network, studio)

def scene_add_actorscores(scnode, actors):
    score = 0
    for scactor in scnode.xpath(XPATHS2['SCENES_STARRING']):
        scactor = scactor.strip().lower()
        if scactor in actors: ratio = 1
        else: ratio = 1 - min([Util.LevenshteinRatio(sactor, a) for a in actors])
        score += SCENE_SCORE_ACTOR_ADD * ratio
    return score

def compute_scene_node(scene_test, html):
    if scene_test.scene:
        node = html.xpath(XPATHS2['SEARCH_SCENES'] % scene_test.scene)
        if node: return (node[0], SCENE_SCORE_ADD)

    if scene_test.actor:
        actors = [a.strip().lower() for a in scene_test.actor.split(',')]
        nodes = []
        for n in html.xpath(XPATHS2['SEARCH_SCENES'] % ""):
            nodes.append((n, scene_add_actorscores(n, actors)))
        return next(sorted(nodes, key = lambda e: e[1], reverse = True), None)

    return None

def extract_movie(compare, node, scene_test = None):
    murl    = anchor_xpath(node, 'a[2]')
    smode   = determine_search_fixed(murl, False)
    date    = date_from_string(string_xpath(node, 'text()[1]'))
    thumb   = image_url_xpath(node, 'a/img')
    title   = string_xpath(node, 'a[2]')
    site    = None
    network = None
    studio  = None
    score   = compute_score(compare, title, date)

    if scene_test:
        html, site, network, studio = movie_html_extras(smode)
        r = compute_scene_node(scene_test, html)
        if r:
            scene_node, scene_score = r
            scene_score += score

            try:
                scene_thumb   = image_url_xpath(scene_node, 'div/a[1]/img')
                content_url   = anchor_xpath(scene_node, 'div/a[1][img]')
                content_smode = determine_search_fixed(content_url, False)
                scene_smode   = content_smode.combine(smode)
                scene_title   = scene_test.template.format(
                                    movie = title,
                                    scene = scene_test.scene,
                                    actor = scene_test.actor)
                scene_ftitle  = format_search_title(
                                  scene_title, date, [network, site, studio])
                return TempResult(scene_score, scene_smode,
                                  scene_smode.url(), scene_title, date, scene_thumb,
                                  site, network, studio, scene_ftitle)
            except:
                Log.Error(traceback.format_exc())

    if not scene_test and score >= MORE_SCORE:
        html, site, network, studio = movie_html_extras(smode)

    return TempResult(score, smode, murl, title, date, thumb,
                      site, network, studio,
                      format_search_title(title, date, [network, site, studio]))

def extract_content_site(node, key):
    return string_xpath(node, 'p[contains(text(), "%s:")]/a/text()' % key)

def extract_content(compare, node):
    murl         = anchor_xpath(node, 'p[2]/a[1]')
    smode        = determine_search_fixed(murl, False)
    date         = date_from_string(string_xpath(node, 'p[1]/text()[1]'))
    title        = string_xpath(node, 'p[2]/a[1]')
    thumb        = image_url_xpath(node, 'div[1]/p[1]/a[1]/img[1]')
    site         = extract_content_site(node, 'Site')
    network      = extract_content_site(node, 'Network')
    score        = compute_score(compare, title, date)
    format_title = format_search_title(title, date, [network, site])
    return TempResult(score, smode, murl, title, date, thumb,
                      site, network, None, format_title)

def search_html(query):
    return request_html(D18_SEARCH_URL % String.URLEncode(query))

def search_basic(compare, query):
    html = search_html(query)
    f = []

    # Extract movie section:
    for n in html.xpath(XPATHS2['SEARCH_MOVIE']):
        f.append(extract_movie(compare, n))

    # Extract "content" section, shorter clips, etc:
    for n in html.xpath(XPATHS2['SEARCH_CONTENT']):
        f.append(extract_content(compare, n))

    return temps_filter_sort(f)

def filter_temps(found): return list(filter(lambda f: f.smode, found))

def score_sort(found):
    return sorted(found, key=lambda f: f.score, reverse=True)

def temps_filter_sort(found): return score_sort(filter_temps(found))

def log_found(found, query, year):
    log_section()
    Log('Found %s result(s) for query "%s" (%s)' % (len(found), query, year))

    below = False
    for i, f in enumerate(found):
        if not below and f.score < IGNORE_SCORE:
            below = True
            Log("These were below the score limit (%s)" % IGNORE_SCORE)
        Log('\t%s.\t[%s] [%s]\t[%s]\t%s' % (i, str(f.date), f.smode, f.score, f.title))

    log_section()

def leventh_dist(x, y):
    return Util.LevenshteinDistance(x.lower(), y.lower())

def compute_score(compare, title, date):
    # Compute 
    score = INIT_SCORE - leventh_dist(compare.title, title)
    if date is None or compare.year is None:
        Log('Date: No date found')
    else:
        Log('Found Date = %s' % date)
        # Wrong year must cost a lot in score.
        score -= math.pow(abs(int(compare.year) - int(date.year)), DATE_SCORE_BASE)
    return score

def replace_special(title):
    # Swap fullwidth and halfwidth replacements of colons, commas, etc.:
    # - Why Colon? Windows doesn't allow colons.
    r = [(r, n[0]) for n in REPLACEMENTS.items() for r in n[1]]
    return reduce(lambda a, e: a.replace(e[0], e[1]), r, title)

if DEV: replace_special2 = replace_special
else:
    def replace_special2(title):
        return replace_special(title.decode("utf-8")).encode('utf-8')

# Builds regex for search_scene(...):
def build_scene_regex():
    """
    Tested with these:
    S_TEST = ['India Summer, And Abd in How to Make a Cheap Porno - Scene 1',
              'How to make a cheap porno - Scene 1',
              'Alina Li - Scene 1 in How to make a cheap porno',
              'Scene 1 - Alina Li in How to make a cheap porno',
              'Scene 1 in How to make a cheap porno',
              'Scene 1 - How to make a cheap porno',
              'Scene 1: How to make a cheap porno']
    """
    re_PRO = r"\s*\b(?:in|from|at)\b\s*"
    re_NOS = lambda n: r"scene\s*(?P<scene%s>\d+)" % n
    re_NOL = lambda n: r"(?:%s(?:\s*[:-]?\s+)?)"   % re_NOS(n)
    re_NOR = lambda n: r"(?:(?:\s+[:-]?\s+)?%s)"   % re_NOS(n)
    re_STA = lambda s: r"(?P<actor%s>(?:\b[\w]+\b[,\s]*)+?\b[\w]+\b)" % s
    def re_MOV(m, greedy = True):
        g = r"*" if greedy else r"+?"
        return r"(?P<movie%s>(?:\b[\w#\.]+\b[,\s]*)%s\b[\w#\.]+\b)" % (m, g)

    re_A   = re_STA(1) + re_PRO + re_MOV(1, False) + re_NOR(1)
    re_B   = re_STA(2) + re_NOR(2) + re_PRO + re_MOV(2)
    re_C   = re_MOV(3, False) + re_NOR(3)
    re_D   = re_NOL(4) + re_STA(4) + re_PRO + re_MOV(4)
    re_E   = re_NOL(5) + re_PRO + re_MOV(5)
    re_F   = re_STA(6) + re_PRO + re_MOV(6)
    re_G   = re_NOL(7) + re_MOV(7)
    regex  = r"^(?:%s)$" % r"|".join([re_A, re_B, re_C, re_D, re_E, re_F, re_G])
    return re.compile(regex, flags = re.I)

REGEX['SEARCH_SCENE'] = build_scene_regex()

def dict_first_prefix_key(g, prefix):
    pres = filter(lambda e: e[0].startswith(prefix), g)
    return next(filter(lambda e: e[1], pres), None)

def disjoint_spans_replace(original, spans):
    if not spans: return original
    accum       = ""
    prev_end    = 0
    for (start, end), instead in sorted(spans, key=lambda span: span[0]):
        accum   += original[prev_end:start] + instead
        prev_end = end
    accum       += original[prev_end:]
    return accum

def match_item_span(match, prefix):
    item = dict_first_prefix_key(match.groupdict().items(), prefix)
    return (item and item[1].strip(), item and match.span(item[0]))

SearchSceneTest = namedtuple('SearchSceneTest',
                            ['name', 'movie', 'scene', 'actor', 'template'])

def compute_scene_test(name):
    # Search for a scene in a movie:
    Log("Testing scene search for: %s." % name)

    match = REGEX['SEARCH_SCENE'].match(name)
    if not match:
        Log("Regex for scene search didn't match.")
        return

    movie, mspan = match_item_span(match, "movie")
    scene, sspan = match_item_span(match, "scene")
    actor, aspan = match_item_span(match, "actor")

    print(" * movie:    \t" + str(movie))
    print(" * scene:    \t" + str(scene))
    print(" * actor:    \t" + str(actor))

    if not movie or not (scene or actor):
        Log("Irrecoverable error: no movie or neither of scene and actor found")
        return

    replaces = [(mspan, "{movie}")]
    if sspan: replaces.append((sspan, "{scene}"))
    if aspan: replaces.append((aspan, "{actor}"))
    template = disjoint_spans_replace(name, replaces)
    print(" * template: \t"+ str(template))
    log_section()

    return SearchSceneTest(name, movie, scene, actor, template)

def search_scene(comp1, name):
    scene_test = compute_scene_test(name)
    if not scene_test: return []
    comp2 = CompareData(scene_test.movie, comp1.year)
    nodes = search_html(scene_test.movie).xpath(XPATHS2['SEARCH_MOVIE'])
    return  temps_filter_sort([extract_movie(comp2, n, scene_test) for n in nodes])

# Search for a connection:
def search_connection(compare, name):
    Log('Trying connections search.')
    log_section()

    parts = REGEX['CONN'].split(name)
    if len(parts) < 2:
        Log('Cant separate query into actor and site.')
        return

    # Take the first actor and the website name to search +
    # NA site, Pull & visit connections:
    actors = parts[0].split(',')
    actor  = String.URLEncode(actors[0].strip().lower())
    site   = String.URLEncode(parts[1].strip().lower())

    Log("Connections query: {actor: %s, site: %s}" % (actor, site))
    html   = request_html(D18_CONNECTIONS_URL % (actor, site))
    found  = []
    for conn in html.xpath(XPATHS2['SEARCH_CONNS']):
        Log("Connection url: %s" % conn)
        for n in request_html(conn).xpath(XPATHS2['SEARCH_CONTENT']):
            found.append(extract_content(compare, n))

    return temps_filter_sort(found)

def search(results, media, lang, manual = False):
    log_header('SEARCH')

    title = media.name

    if search_fixed(results, title, lang): return

    # @TODO
    year = media.year
    if media.primary_metadata is not None:
        year = media.primary_metadata.year
        Log('Searching for Year: %s' % year)

    # @TODO
    if media.primary_metadata is not None:
        title = media.primary_metadata.title
    title = replace_special2(title)
    Log('Searching for Title: %s' % title)

    # Normalize title:
    query = normalize_name(title)
    Log('Title (Normalized): "%s", Title (Before): "%s"' % (query, title))

    # Basic search:
    Log('***** SEARCHING FOR "%s" (%s) - DATA18 *****' % (query, year))
    compare = CompareData(title, year)
    found   = search_basic(compare, query)
    log_found(found, query, year)

    # Strip and research:
    query2 = title.lstrip('0123456789')
    if query != query2:
        found2 = search_basic(compare, query2)
        log_found(found2, query, year)
        found.extend(found2)

    # Perhaps this a scene in a movie, try to search for the movie instead:
    if not found:
        Log('No results found for query, so far "%s"\n' % query2)
        scenes = search_scene(compare, query)
        log_found(scenes, query, year)
        found.extend(scenes)

        # Next: try a connection:
        if not found:
            Log('Still no results found even with scenes...\n')
            conns = search_connection(compare, query)
            log_found(conns, query, year)
            found.extend(conns)

    # Walk the found items and gather extended information
    for i, f in enumerate(score_sort(found)):
        Log('* Score:   \t%s' % f.score)
        Log('* Slug:    \t%s' % f.smode)
        Log('* Title:   \t%s' % f.title)
        Log('* FTitle:  \t%s' % f.format_title)
        Log('* Date:    \t%s' % f.date)
        Log('* Thumb:   \t%s' % f.thumb)
        Log('* Site:    \t%s' % f.site)
        Log('* Network: \t%s' % f.network)
        Log('* Studio:  \t%s' % f.studio)

        if f.score < IGNORE_SCORE:
            Log('*          \tScore is below ignore boundary (%s)... Skipping!' % IGNORE_SCORE)
        else:
            results.Append(make_result(
                f.smode.slug(), f.format_title, f.score, lang, f.thumb))

        if i != len(found): log_section()

        if not manual and len(found) > 1 and f.score >= GOOD_SCORE:
            Log('*** Found result above GOOD_SCORE, stopping! ***')
            break

def LogList(what, items, cb = lambda e: e):
    if not items: return
    try:
        Log(what)
        for e in items: Log('| ---- %s' % cb(e))
    except:
        pass

### Writes metadata information to log.
def log_metadata(metadata, header):
    Log(header)
    log_section()
    Log(    '* ID/Slug:...........%s' % metadata.id)
    Log(    '* URL:...............%s' % SearchMode.from_slug(metadata.id).url())
    Log(    '* Title:.............%s' % metadata.title)
    Log(    '* Release date:......%s' % str(metadata.originally_available_at))
    Log(    '* Year:..............%s' % str(metadata.year))
    Log(    '* TagLine:...........%s' % str(metadata.tagline))
    Log(    '* Content rating:....%s' % metadata.content_rating)
    Log(    '* Duration (min):....%s' % (metadata.duration and 
                                         metadata.duration / 1000 / 60))
    Log(    '* Studio:............%s' % str(metadata.studio))
    Log(    '* Summary:...........%s' % metadata.summary)
    LogList('* Directors:',             metadata.directors)
    LogList('* Poster URL:',            metadata.posters.keys())
    LogList('* Art:',                   metadata.art.keys())
    LogList('* Collections:',           metadata.collections)
    LogList('* Genres:',                metadata.genres)
    LogList('* Starring:',              metadata.roles,
            lambda e: "%s (%s)" % (e.actor, e.photo))
    log_section()

def photoset_count(html, xpkey):
    return try_lam(lambda:
                int(re.search(r'(\d+)',
                    string_xpath(html, XPATHS2[xpkey])).group(1)))

ImageJob = namedtuple('ImageJob',
                     ['url', 'referer', 'type', 'sort_order', 'preview'])

def media_proxy(img):
    if DEV: return img.url

    url     = img.url
    referer = img.referer or img.url

    if IMAGE_PROXY_URL:
        url = IMAGE_PROXY_URL + ('?url=%s&referer=%s' % (url, referer))

    content = HTTP.Request(url, headers = {'Referer': referer}).content

    if img.preview:
        return Proxy.Preview(content, sort_order = img.sort_order)
    else:
        return Proxy.Media(content,   sort_order = img.sort_order)

@parallelize
def download_images(metadata, images):
    for img in images:
        @task
        def downloader(metadata = metadata, img = img):
            Log("Downloading image: %s" % str(img))

            typ = img.type
            url = img.url

            if   typ == 'art':
                metadata.art[url]     = media_proxy(img)
            elif typ == 'poster':
                metadata.posters[url] = media_proxy(img)
            elif typ == 'banner':
                metadata.banners[url] = media_proxy(img)

        if DEV: downloader(metadata, img)

def fetch_poster_main(images, sort_order, referer, html):
    if sort_order >= IMAGE_MAX: return sort_order
    image_url     = image_url_xpath(html, XPATHS2['POSTER_MAIN'])
    if not image_url:
        image_url = image_url_xpath(html, XPATHS2['POSTER_MAIN_MOVIE'])
    if not image_url: return sort_order
    images.append(ImageJob(image_url, referer, 'poster', sort_order, False))
    sort_order += 1

def fetch_photosets(images, sort_order, smode, html):
    if sort_order >= IMAGE_MAX: return sort_order

    # Get count:
    referer = D18_PHOTOSET_REF % smode.id
    count   = photoset_count(html, 'PHOTOSET_COUNT')
    if not count:
        count = photoset_count(html, 'VIDEOSTILLS_COUNT')
        if not count:
            count = photoset_count(html, 'MOV_PHOTOS_COUNT')
            if count:
                referer = anchor_xpath(html, XPATHS2['MOV_PHOTOS_REF'])
            else:
                Log("No count found for photo sets")
                return sort_order

    # Get base url:
    if smode.is_movie():
        ubase = html.xpath(XPATHS2['MOV_PHOTOS_LIST'])[0].get('src')
    else:
        ubase = image_url_xpath(html, XPATHS2['PHOTOSET_LIST'])

    ubase = ubase.split('/')[:-2]
    ubase = '/'.join(ubase)

    # Add the images:
    for idx in range(1, count):
        if sort_order >= IMAGE_MAX: return sort_order
        str_index = '0' + str(idx) if idx < 10 else str(idx)
        image_url = ubase + '/' + str_index + '.jpg'
        images.append(ImageJob(image_url, referer, 'art', sort_order, False))

        sort_order += 1

    return sort_order

# Old videostills:
def fetch_videostills_old(images, sort_order, referer, html):
    if sort_order >= IMAGE_MAX: return sort_order

    vidstills     = html.xpath(XPATHS2['VIDEOSTILLS_OLD'])
    if not vidstills:
        vidstills = html.xpath(XPATHS2['QUICKTIMELINE_OLD'])
    if not vidstills: return sort_order

    for still in vidstills:
        if sort_order >= IMAGE_MAX: return sort_order
        image_url = still.get('src').strip()
        images.append(ImageJob(image_url, referer, 'poster', sort_order, False))
        sort_order += 1

    return sort_order

def update_images(html, smode, metadata):
    log_section()
    Log('Finding images:')
    log_section()

    url        = smode.url()
    images     = []

    sort_order = 0
    sort_order = try_lam2(fetch_poster_main,     images, sort_order, url,   html) or sort_order
    sort_order = try_lam2(fetch_photosets,       images, sort_order, smode, html) or sort_order
    sort_order = try_lam2(fetch_videostills_old, images, sort_order, url,   html) or sort_order

    download_images(metadata, images)

    log_section()

def update_tagline(metadata, smode):
    tagline = smode.url()
    if smode.is_scene(): tagline += ' , ' + smode.scene_mov().url()
    metadata.tagline = tagline

def update_release_date(metadata, html, shtml):
    try:
        date = parse_document_date(html)
    except:
        date = parse_document_date(shtml)

    if not date: return

    metadata.originally_available_at = date
    metadata.year = date.year
    Log('Release Date Sequence Updated')

def update_director(metadata, html):
    director = string_xpath(html, XPATHS2['DIRECTOR'])
    if not director: return
    metadata.directors.clear()
    metadata.directors.add(normalize_ws(director))
    Log('Director Updated')

def update_summary(metadata, html, smode, prefix):
    summ   = xp_first_text(html.xpath(XPATHS2['SUMMARY'] % prefix))
    if not summ: return False
    summ   = summ.replace('&13;', '').strip(' \t\n\r"') + "\n"
    summ   = re.sub(r'%s:' % prefix, '', summ.strip('\n')).strip()
    metadata.summary = normalize_ws(summ)
    Log('Summary Sequence Updated')
    return True

def normalize_ws(string):
    RE = re.compile(r'\s+')
    return RE.sub(' ', string) if string else string

def update_genres(metadata, html, smode):
    metadata.genres.clear()
    gen_xp = 'GENRE_MOVIE' if smode.is_movie() else 'GENRE_CONTENT'
    for gen in html.xpath(XPATHS2[gen_xp]):
        metadata.genres.add(normalize_ws(gen))
    Log('Genre Sequence Updated')

def update_starring(metadata, html, smode):
    stars_xp = 'ACTOR_MOVIE' if smode.is_movie() else 'ACTOR_CONTENT'
    starring = html.xpath(XPATHS2[stars_xp])
    if not starring: return False

    metadata.roles.clear()
    for star in starring:
        name  = normalize_ws(alt_xpath(star, '.'))
        photo = image_url_xpath(star, '.')
        photo = re.sub(r'/stars/[^/]+/', '/stars/pic/', photo)
        role  = metadata.roles.new()
        role.actor = name
        role.name  = name
        role.photo = photo

    Log('Starring Sequence Updated')
    return True

def update_starring_fb(metadata, html, clear):
    if not clear: metadata.roles.clear()

    starring     = set(html.xpath(XPATHS2['ACTOR_DEV']) or [])
    if not clear:
        starring = starring.union(html.xpath(XPATHS2['ACTOR_FALLBACK']) or [])
    if not starring: return False

    for star in starring:
        name = normalize_ws(star)
        role = metadata.roles.new()
        role.name  = name
        role.actor = name
        role.photo = None

    Log('Starring Sequence Updated')
    return True

def update_duration(metadata, html, smode):
    if metadata.duration and metadata.duration > 1: return True

    try:
        string   = string_xpath(html, XPATHS2['DURATION'])
        duration = int(re.search(r'(\d+)', string).group(1)) * 60 * 1000
        metadata.duration = duration
        return True
    except:
        string   = string_xpath(html, XPATHS2['DURATION2'])
        if not string: return None
        RE = re.compile(r'(\d+)\s*mins?,?\s*(\d+)\s*secs?', flags = re.I)
        match    = RE.search(string).groups(0)
        duration = 1000 * (int(match[0]) * 60 + int(match[1]))
        metadata.duration = duration
        return True

# Connect content + movie when it is a scene
def update_related_movie(metadata, html, smode):
    try:
        href   = anchor_xpath(html, XPATHS2['SCENE_MOVIE_FIX'])
        msmode = determine_search_fixed(href, False)
        if msmode:
            smode = smode.combine(msmode)
            metadata.id = smode.slug()
            return smode
    except:
        pass

    return smode

def update(metadata, media, lang, force = False):
    smode = SearchMode.from_slug(metadata.id)

    log_header('UPDATE "%s" SLUG: %s' % (media.title, smode.slug()))
    log_metadata(metadata, "Current metadata:")

    # Set basic stuff:
    metadata.id = smode.slug()
    metadata.content_rating = 'NC-17'
    update_tagline(metadata, smode)

    html  = request_data_html(smode.mode, smode.id)
    smode = update_related_movie(metadata, html, smode)
    shtml = request_data_html(1, smode.sid) if smode.is_scene() else html

    # Title:
    metadata.title = parse_document_title(html)
    Log('Title Updated')

    try_lam2(update_release_date,    metadata, html,  shtml)

    try_lam2(update_director,        metadata, html)

    if not try_lam2(update_duration, metadata, html,  smode):
        try_lam2(update_duration,    metadata, shtml, smode)

    if not try_lam2(update_summary,  metadata, html,  smode, 'Story'):
        try_lam2(update_summary,     metadata, shtml, smode, 'Description')

    try_lam2(update_genres,          metadata, html,  smode)

    sclear  = try_lam2(update_starring,    metadata, html, smode)
    sclear  = try_lam2(update_starring_fb, metadata, html, sclear)

    site    = try_lam2(parse_document_site,     html)
    network = try_lam2(parse_document_network,  html)
    studio  = try_lam2(parse_document_studio,   html) or network or site
    serie   = try_lam2(parse_document_serie,    html)

    if studio:
        metadata.studio = studio
        Log('Studio Sequence Updated')

    # Collections:
    collection = set(filter(None, [site, network, studio, serie]))
    if collection:
        metadata.collections.clear()
        for c in collection: metadata.collections.add(c)
        Log('Collection Sequence Updated')

    update_images(html, smode, metadata)

    log_metadata(metadata, "New metadata:")

class Data18(Agent.Movies):
    name             = 'Data18'
    languages        = [Locale.Language.English]
    accepts_from     = ['com.plexapp.agents.localmedia']
    primary_provider = True

    def search(self, results, media, lang, manual = False):
        search(results, media, lang, manual)

    def update(self, metadata, media, lang, force = False):
        update(metadata, media, lang, force)

# ==============================================================================
# TESTING:
# ==============================================================================

class Role(object):
    def __init__(self): pass
    def __str__(self): return "{name: %s, photo: %s}" % (self.name, self.photo)
    def __repr__(self): return self.__str__()

class Container():
    def __init__(self, ctor = lambda: None):
        self.ctor = ctor
        self.clear()
    def __iter__(self):
        for x in self.data: yield x
    def __str__(self):   return str(self.data)
    def __repr__(self):  return self.__repr__()
    def clear(self):     self.data = []
    def Append(self, r): self.add(r)
    def add(self, r):    self.data.append(r)
    def new(self):
        r = self.ctor()
        self.data.append(r)
        return r

class Metadata(object):
    def __init__(self, id, content_rating, title, year, tagline, directors,
                       studio, summary, posters, art, collections, genres,
                       roles, duration):
        self.id             = id
        self.guid           = id
        self.title          = title
        self.title_sort     = title
        self.year           = year
        self.duration       = duration
        self.studio         = studio
        self.tagline        = tagline
        self.summary        = summary
        self.directors      = directors
        self.posters        = posters
        self.art            = art
        self.collections    = collections
        self.genres         = genres
        self.roles          = roles
        self.content_rating = content_rating
        self.originally_available_at = year

Media = namedtuple('Media', ['title', 'name', 'year', 'primary_metadata'])

def UPDATE_TEST(slug):
    slug     = slug.replace(D18_BASE_URL, '')
    name     = "thetitle"
    media    = Media(title = name, name  = name, year  = 1999,
                     primary_metadata = None)

    roles    = Container(lambda: Role())
    r        = roles.new()
    r.name   = 'thename'
    r.photo  = 'thephoto'

    colls    = Container()
    colls.add('brazzers')

    genres   = Container()
    genres.add('hardcore')

    direct   = Container()
    direct.add('thedir')

    metadata = Metadata(id = slug,
                        year = 1999,
                        title = name,
                        duration = None,
                        studio   = 'thestudio',
                        tagline  = "thetagline",
                        summary  = 'thesummary',
                        content_rating = 'therating',
                        posters  = {},
                        art = {},
                        roles = roles,
                        genres = genres,
                        directors = direct,
                        collections = colls)

    update(metadata, media, None)

def SEARCH_TEST(test):
    name    = TESTS[test]
    media   = Media(title = name, name = name, year = 2016,
                    primary_metadata = None)
    results = Container()
    search(results, media, None)
    print(results)

TESTS = ["Jillian Janson in My Sister's Hot Friend",                    #  0
         'Kimber Woods in Buttsex Cuties - Scene 1',                    #  1
         'India Summer in How to Make a Cheap Porno - Scene 1',         #  2
         'How to make a cheap porno - Scene 1',                         #  3
         'Alina Li - Scene 1 in How to make a cheap porno',             #  4
         'Scene 1 - Alina Li in How to make a cheap porno',             #  5
         'Scene 1 in How to make a cheap porno',                        #  6
         'Scene 1 - How to make a cheap porno',                         #  7
         'Scene 1: How to make a cheap porno',                          #  8
         'Tight teen pussy',                                            #  9
         'Pussy Feast',                                                 #  10
         'hot teen next door 27',                                       #  11
         'http://www.data18.com/content/1145979',                       #  12
         'www.data18.com/content/1145979',                              #  13
         'http://data18/scene/1145979/1145246',                         #  14
         '1145979',                                                     #  15
         '1145979/1146336',                                             #  16
         'content/1146336',                                             #  17
         'movies/1145979',                                              #  18
         'movie/1145979',                                               #  19
         'scene/1145979',                                               #  20
         'scenes/1145979/1146336',                                      #  21
         'scenes/1145979/1146336']                                      #  22
SEARCH_TEST(11)

#UPDATE_TEST('http://www.data18.com/movies/1148631')
#UPDATE_TEST('http://www.data18.com/scenes/5423315-1148631')
#UPDATE_TEST('http://www.data18.com/content/1161227')
#UPDATE_TEST('http://www.data18.com/content/1163750')
#UPDATE_TEST('http://www.data18.com/content/591261')
#UPDATE_TEST('http://www.data18.com/content/1148345')
#UPDATE_TEST('http://www.data18.com/content/1123820')
#UPDATE_TEST('http://www.data18.com/content/1124154')
#UPDATE_TEST('http://www.data18.com/content/1126544')
#UPDATE_TEST('http://www.data18.com/content/1125523')
#UPDATE_TEST('http://www.data18.com/content/1126410')
#UPDATE_TEST('http://www.data18.com/content/1126515')
#UPDATE_TEST('http://www.data18.com/content/1126893')
#UPDATE_TEST('http://www.data18.com/content/1129700')
#UPDATE_TEST('http://www.data18.com/content/319842')
#UPDATE_TEST('http://www.data18.com/content/5170363')
#UPDATE_TEST('http://www.data18.com/content/5170413')
#UPDATE_TEST('http://www.data18.com/content/1164368')
#UPDATE_TEST('http://www.data18.com/content/1164821')
#UPDATE_TEST('http://www.data18.com/content/2222107')
#UPDATE_TEST('http://www.data18.com/content/1161682')
#UPDATE_TEST('http://www.data18.com/content/2222109')
#UPDATE_TEST('http://www.data18.com/content/332598')
#UPDATE_TEST('http://www.data18.com/content/323844')
#UPDATE_TEST('http://www.data18.com/content/159593')
#UPDATE_TEST('http://www.data18.com/movies/1147862')