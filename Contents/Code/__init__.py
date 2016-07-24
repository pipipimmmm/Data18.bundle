# -*- coding: utf-8 -*-

# Data18
import re, types, traceback, math, calendar, datetime, urllib
import Queue
from lxml.etree import tostring
from functools import partial

VERSION_NO = '1.2015.03.28.3'

# URLS
D18_BASE_URL = 'http://www.data18.com/'
D18_ID_URL = {'movie': D18_BASE_URL + 'movies/%s', 'content': D18_BASE_URL + 'content/%s'}
D18_SEARCH_URL = D18_BASE_URL + 'search/?k=%s&t=0'
D18_CONNECTIONS_URL = D18_BASE_URL + 'connections/?v1=%s&v2=%s'
D18_CONNECTIONS_LIMIT = 5
D18_STAR_PHOTO = D18_BASE_URL + 'img/stars/120/%s.jpg'

# Other stuff:
MODES = ['content', 'movie', 'scene']
REPLACEMENTS = {':': [u"\uff1a", u"\uA789"], '-': [u"\u2014"], '.': [u"\uFE52"]}

REQUEST_DELAY = 0       # Delay used when requesting HTML, may be good to have to prevent being banned from the site

INITIAL_SCORE = 100     # Starting value for score before deductions are taken.
GOOD_SCORE = 98         # Score required to short-circuit matching and stop searching.
IGNORE_SCORE = 45       # Any score lower than this will be ignored.

THREAD_MAX = 20

def make_slug(self, name):
    s = '-'.join(x.lower() for x in re.split('\s+', name, 0, re.I))
    self.Log('slug: %s' % s)
    return s

def join_slug(parts):
    return '-'.join(parts)

def sluggify_name(self, name):
    return make_slug(self, re.sub(r"[\W\_]+", ' ', name, 0, re.I))

def url_root_title(self, url, rootPath, titlePath):
    self.Log("url: %s" % url)
    root = self.requestHTML(url).xpath(rootPath)[0]
    title = root.xpath(titlePath)[0].strip()
    return (url, root, title)

def make_result(key, slug, title, thumb, lang):
    return [MetadataSearchResult(id = '%s$%s' % (join_slug(key), slug), name = title, score = 100, thumb = thumb, lang = lang)]

def site_search(self, cb_urt, key, name, lang, thumbPath):
    try:
        slug = sluggify_name(self, name)
        url, root, title = cb_urt(slug)
        return make_result(key, slug, title, root.xpath(thumbPath)[0], lang)
    except Exception, e:
        return False

def metadata_init(metadata, studio, slug, cb_urt):
    url, root, title = cb_urt(slug)
    metadata.roles.clear()
    metadata.genres.clear()
    metadata.directors.clear()
    metadata.collections.clear()
    metadata.tagline = url
    metadata.title = title
    metadata.title_sort = metadata.title
    metadata.studio = studio
    metadata.collections.add(metadata.studio)
    return (url, root, title)

def site_generic_url_root_title(url_base, self, slug):
    return url_root_title(self, 'http://%s/video/%s' % (url_base, slug), '//*[@id="content"]', './/h2//*[@class="title"]/em/text()')

def site_generic_search(url_base, self, key, name, lang):
    return site_search(self, partial(site_generic_url_root_title, url_base, self), key, name, lang, './/*[@class="preview-images"]/img[1]/@src')

def site_generic_update(url_base, studio, self, slug, metadata, media, lang):
    url, root, title = metadata_init(metadata, studio, slug, partial(site_generic_url_root_title, url_base, self))
    metadata.summary = ""
    self.updateDate(metadata, self.getDateFromString(root.xpath('.//abbr[@class="timeago"]/@title')[0].split(' ')[0]))
    for actor in root.xpath('.//p[@class="actor"]//a'):
        role = metadata.roles.new()
        role.actor = actor.xpath('./text()')[0]
        photoRoot = self.requestHTML('http://%s%s' % (url_base, actor.get('href')))
        role.photo = self.getImageUrlFromXPath(photoRoot, '//*[@class="actorthumb"]')
    self.getImageSet(metadata, [[image, url, True, 0, 1] for image in root.xpath('.//*[@class="preview-images"]/img/@src')])

def site_generic_pair(studio, base_url):
    return [partial(site_generic_search, base_url), partial(site_generic_update, base_url, studio)]

def site_colette_url_root_title(self, slug):
    return url_root_title(self, 'http://coletteporn.com/%s' % slug, '//body/div[@class="container"]', './/ol[@class="breadcrumb"]/li[@class="active h1"]/text()')

def site_colette_search(self, key, name, lang):
    return site_search(self, partial(site_colette_url_root_title, self), key, name, lang, './/*[@id="mustified"]/*[@class="galItem"][1]/a/@href')

def site_colette_update(self, slug, metadata, media, lang):
    url, root, title = metadata_init(metadata, 'Colette', slug, partial(site_colette_url_root_title, self))
    metadata.summary = root.xpath('.//p[@class="daContent"]/text()[1]').strip()
    for actor in root.xpath('.//ol[@class="breadcrumb"]/li[2]/a/text()'):
        role = metadata.roles.new()
        role.actor = actor
    self.getImageSet(metadata, [[image, url, False, 0, 1] for image in root.xpath('.//*[@id="mustified"]/*[@class="galItem"]/a/@href')])

FOREIGN_DISPATCH = {
    ('colette',): [site_colette_search, site_colette_update],
    ('fantasy', 'hd'): site_generic_pair('Fantasy HD', 'fantasyhd.com'),
    ('exotic4k',): site_generic_pair('Exotic4k', 'exotic4k.com'),
    ('passion', 'hd'): site_generic_pair('Passion HD', 'passion-hd.com'),
    ('my', 'very', 'first', 'time'): site_generic_pair('My Very First Time', 'myveryfirsttime.com')
}

def Start():
    #HTTP.ClearCache()
    HTTP.CacheTime = CACHE_1WEEK
    HTTP.Headers['User-agent'] = 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.2; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0)'
    HTTP.Headers['Accept-Encoding'] = 'gzip'

class Data18(Agent.Movies):
    name = 'Data18'
    languages = [Locale.Language.NoLanguage]
    primary_provider = True
    accepts_from = ['com.plexapp.agents.localmedia']

    prev_search_provider = 0

    def Log(self, message, *args):
        if Prefs['debug']:
            Log(message, *args)

    def getDateFromString(self, string):
        try:
            return Datetime.ParseDate(string).date()
        except:
            return None

    def getStringContentFromXPath(self, source, query):
        return source.xpath('string(' + query + ')')

    def getAnchorUrlFromXPath(self, source, query):
        anchor = source.xpath(query)

        if len(anchor) == 0:
            return None

        return anchor[0].get('href')

    def getImageUrlFromXPath(self, source, query):
        img = source.xpath(query)

        if len(img) == 0:
            return None

        return img[0].get('src')

    def findDateInTitle(self, title):
        result = re.search(r'(\d+-\d+-\d+)', title)
        if result is not None:
            return Datetime.ParseDate(result.group(0)).date()
        return None

    def extractDateXPath(self, element):
        return self.getDateFromString(self.getStringContentFromXPath(element, 'text()[1]'))

    def urlQuote(self, string):
        return String.Quote((string).encode('utf-8'), usePlus=True)

    def doSearchBasic(self, url, scene_data = None):
        html = self.requestHTML(url)
        found = []

        # Extract movie section:
        for r in html.xpath('//div[a/img[@class="yborder"]]'):
            murl = self.getAnchorUrlFromXPath(r, 'a[2]')
            date = self.extractDateXPath(r)
            thumb = self.getImageUrlFromXPath(r, 'a/img')
            title = self.getStringContentFromXPath(r, 'a[2]')

            # We actually have to open the document to get the scene link:
            if scene_data:
                try:
                    # Fetch HTML
                    movie_html = self.requestHTML(murl)
                    content_url = movie_html.xpath('//*[@id="related"]//a[contains(text(), "Scene %s")]' % scene_data[1])[0].get('href')
                    title = scene_data[2] % (title)
                    found.append({'url': content_url, 'movie_url': murl, 'title': title, 'date': date, 'thumb': thumb, 'mode': 'scene'})
                except Exception, e:
                    Log.Error(traceback.format_exc())
            else:
                found.append({'url': murl, 'title': title, 'date': date, 'thumb': thumb, 'mode': 'movie'})

        # Extract "content" section, shorter clips, etc:
        for r in html.xpath('//div[@class="contenedor"]/div[@class="bscene genmed"]'):
            date = self.extractDateXPath(r)
            title = self.getStringContentFromXPath(r, 'p[2]/span[1]/a[1]')
            murl = self.getAnchorUrlFromXPath(r, 'p[2]/span[1]/a[1]')
            thumb = self.getImageUrlFromXPath(r, 'p[1]/a[1]/img[1]')

            found.append({'url': murl, 'title': title, 'date': date, 'thumb': thumb, 'mode': 'content'})

        return found

    def doSearch(self, name, scene_data = []):
        return self.doSearchBasic(D18_SEARCH_URL % (self.urlQuote(name)), scene_data)

    def itemId(self, url):
        return url.split('/', 4)[4]

    def requestHTML(self, url):
        return HTML.ElementFromURL(url, sleep=REQUEST_DELAY)

    def requestDataHTML(self, mode, id):
        return self.requestHTML(D18_ID_URL[mode] % id)

    def urlToId(self, url):
        test = url
        if test.startswith(D18_BASE_URL):
            # URL -> [mode, id, <optional-id>]
            parts = test.rsplit('/')[3:]
            if len(parts) == 3:
                parts[0] = 'scene'
            elif parts[0] == 'movies':
                parts[0] = 'movie'
            test = '-'.join(parts)
        return test

    def searchFixed(self, results, media, lang):
        def all(iterable):
            for element in iterable:
                if not element:
                    return False
            return True

        fixed_test = self.urlToId(media.name)
        fixed_test_parts = [x.strip() for x in fixed_test.split('-', 3)]
        if len(fixed_test_parts) == 1 or not len(fixed_test_parts[0]):
            # Default to content mode.
            fixed_test_parts.insert(0, 'content')

        if fixed_test_parts and all(x.isdigit() for x in fixed_test_parts[1:]):
            if fixed_test_parts[0] in MODES:
                self.Log('Given an exact ID: %s, no searching needed.' % fixed_test)
                self.Log('Working in mode: %s' % fixed_test_parts[0])

                # Fetch HTML for primary:
                html = self.requestDataHTML('content' if fixed_test_parts[0] != 'movie' else 'movie', fixed_test_parts[1])
                name = self.getStringContentFromXPath(html, '//h1')

                self.Log('Name of exact ID: %s' % name)

                # Make sure movie ID is correct, should throw otherwise.
                if fixed_test_parts[0] == 'scene':
                    self.getStringContentFromXPath(self.requestDataHTML('movie', fixed_test_parts[2]), '//h1')

                # Set the result
                results.Append(MetadataSearchResult(id = fixed_test, name = name, score = '100', lang = lang))
                return True

        return False

    def searchScene(self, name, found):
        # Tested with these:
        # Alina Li in How to make a cheap porno - Scene 1
		# How to make a cheap porno - Scene 1
        # Alina Li - Scene 1 in How to make a cheap porno
		# Scene 1 - Alina Li in How to make a cheap porno
		# Scene 1 in How to make a cheap porno
		# Scene 1 - How to make a cheap porno
        # Scene 1: How to make a cheap porno

        # Search for a scene in a movie:
        regex = r"^(?:(?:(?:.+?\s+)?scene\s*(\d+)(?:\s*\W?\s+|\s+))?(?:(?:in|from|at)\s+|.+?\s+(?:in|from|at)\s+)?)?(.+?)(?(1)|(?:\s*\W?\s+|\s+)scene\s*(\d+))$"
        match = re.search(regex, name, flags=re.I)
        if not match:
            self.Log("Scene not found!")
            return

        # Pull details, create a template: data = [movie, scene, template], Make a search
        movie_span = match.span(2)
        data = [match.group(2).strip(), match.group(1) or match.group(3), name[:movie_span[0]] + '%s' + name[movie_span[1]:]]
        self.Log('Rescue attempt: A scene in a movie? Testing!')
        self.Log('Scene: {movie = %s, scene = %s, template = %s}' % tuple(data))
        found.extend(self.doSearch(data[0], data))

    def searchConnection(self, normalizedName, found):
        # Search for a connection:
        parts = re.compile(r"\s+in\s+", flags=re.I).split(normalizedName)
        if len(parts) < 2:
            return

        second = self.urlQuote(parts[1])

        # Handle multiple performers, branch out to each of them:
        for first in [self.urlQuote(x.strip()) for x in parts[0].split(',')]:
            # Pull & visit connections, we limit them or risk super lag:
            html = self.requestHTML(D18_CONNECTIONS_URL % (first, second))
            for conn in html.xpath('//div/div/div[p[contains(text(), "Results:")]]/span[position() <= %s]/a/@href' % D18_CONNECTIONS_LIMIT):
                found.extend(self.doSearchBasic(conn))

    def searchForeign(self, normalizedName, media, results, lang):
        if not media.filename: return
        path = urllib.unquote(media.filename)
        filename = path.split('/')[-1]
        self.Log("Searching via foreign sites, filename: %s" % filename)
        splitter = re.compile(r"[\W\_]", re.I)
        for match in re.findall(r"\[([^\[\]]+)\]", filename, re.I):
            key = tuple([x.lower() for x in splitter.split(match)])
            if key not in FOREIGN_DISPATCH: continue
            self.Log("Searching %s for: %s" % (key, media.name))
            returned = FOREIGN_DISPATCH[key][0](self, key, normalizedName, lang)
            if returned:
                self.Log("found via %s!" % (list(key)))
                for r in returned: results.Append(r)
                return True
        self.Log("not found via foreign sites.")
        return False

    def search(self, results, media, lang, manual=False):
        # Handle fixed URLs & IDs.
        if self.searchFixed(results, media, lang):
            return

        # Deduce year if not already done.
        yearFromNamePattern = r'\(\d{4}\)'
        yearFromName = re.search(yearFromNamePattern, media.name)
        if not media.year and yearFromName is not None:
            media.year = yearFromName.group(0)[1:-1]
            media.name = re.sub(yearFromNamePattern, '', media.name).strip()
            self.Log('Found the year %s in the name "%s". Using it to narrow search.', media.year, media.name)

        # Clean up year.
        searchYear = u' (' + safe_unicode(media.year) + u')' if media.year else u''

        # Swap fullwidth and halfwidth replacements of colons, commas, etc.:
        # - Why Colon? Windows doesn't allow colons.
        r = [(r, n[0]) for n in REPLACEMENTS.items() for r in n[1]]
        media.name = reduce(lambda a, e: a.replace(e[0], e[1]), r, media.name.decode("utf-8")).encode('utf-8')

        # Normalize the name:
        normalizedName = String.StripDiacritics(media.name)
        if len(normalizedName) == 0:
            normalizedName = media.name

        # These sites are known to have problems in data18, do special search:
        if self.searchForeign(normalizedName, media, results, lang):
        	return

        self.Log('***** SEARCHING FOR "%s"%s - DATA18 v.%s *****', normalizedName, searchYear, VERSION_NO)
        self.Log('Name (Normalized): "%s", Name(Before): "%s"' % (normalizedName, media.name))

        # Do the search:
        found = self.doSearch(normalizedName)
        found2 = media.name.lstrip('0123456789')
        if normalizedName != found2:
            found.extend(self.doSearch(found2))

        # Write search result status to log
        if not found:
            self.Log('No results found for query "%s"%s', normalizedName, searchYear)

            # Huston, we have a problem: perhaps this a scene in a movie, try to search for the movie instead!
            self.searchScene(normalizedName, found)

            if not found:
                # Next: try a connection:
                self.searchConnection(normalizedName, found)
        else:
            self.Log('Found %s result(s) for query "%s"%s', len(found), normalizedName, searchYear)
            i = 1
            for f in found:
                self.Log('    %s. %s [%s] (%s) {%s}', i, f['title'], f['url'], str(f['date']), f['thumb'])
                i += 1

        self.Log('-----------------------------------------------------------------------')
        # Walk the found items and gather extended information
        info = []
        i = 1
        for f in found:
            url = f['url']
            mode = f['mode']
            title = f['title']
            thumb = f['thumb']
            date = f['date']
            year = ''

            if re.search(r'http://www\.data18\.com/(?:movies|content)/.+', url) is None:
                continue

            # Get the id
            item_id = self.itemId(url)
            if len(item_id) == 0:
                continue

            self.Log('* ID is                 %s', item_id)

            # Compute final ID:
            final_id = [mode, item_id]

            if mode == 'scene':
                movId = self.itemId(f['movie_url'])
                if len(item_id) == 0:
                    continue
                final_id.append(movId)

            final_id = '-'.join(final_id)

            # Evaluate the score
            scorebase1 = media.name
            scorebase2 = title.encode('utf-8')

            if date is not None:
                year = date.year

            if media.year:
                scorebase1 += ' (' + media.year + ')'
                scorebase2 += ' (' + str(year) + ')'

            score = INITIAL_SCORE - Util.LevenshteinDistance(scorebase1, scorebase2)

            self.Log('* Title is              %s', title)
            self.Log('* Date is               %s', str(date))
            self.Log('* Score is              %s', str(score))

            if score >= IGNORE_SCORE:
                info.append({'id': final_id, 'title': title, 'year': year, 'date': date, 'score': score, 'thumb': thumb})
            else:
                self.Log('# Score is below ignore boundary (%s)... Skipping!', IGNORE_SCORE)

            if i != len(found):
                self.Log('-----------------------------------------------------------------------')

            i += 1

        info = sorted(info, key=lambda inf: inf['score'], reverse=True)

        # Output the final results.
        self.Log('***********************************************************************')
        self.Log('Final result:')
        i = 1
        for r in info:
            self.Log('    [%s]    %s. %s (%s) {%s} [%s]', r['score'], i, r['title'], r['year'], r['id'], r['thumb'])
            results.Append(MetadataSearchResult(id = r['id'], name = r['title'] + ' [' + str(r['date']) + ']', score = r['score'], thumb = r['thumb'], lang = lang))

            # If there are more than one result, and this one has a score that is >= GOOD SCORE, then ignore the rest of the results
            if not manual and len(info) > 1 and r['score'] >= GOOD_SCORE:
                self.Log('            *** The score for these results are great, so we will use them, and ignore the rest. ***')
                break
            i += 1

    def updateDate(self, metadata, date):
        metadata.originally_available_at = date
        metadata.year = date.year

    def update(self, metadata, media, lang, force=False):
        # Set content rating to XXX.
        metadata.content_rating = 'XXX'

        # Foreign site update:
        id_parts = metadata.id.split('$', 2)
        if len(id_parts) > 1:
            key = tuple(id_parts[0].split('-'))
            self.Log('***** UPDATING "%s" MODE: %s, ID: %s - DATA18 v.%s *****', media.title, key, id_parts[1], VERSION_NO)
            FOREIGN_DISPATCH[key][1](self, id_parts[1], metadata, media, lang)
            self.writeInfo(metadata.tagline, metadata)
            return

        # extract mode & id.
        id_parts = metadata.id.split('-', 3)
        mode, id = id_parts[0:2]

        self.Log('***** UPDATING "%s" MODE: %s, ID: %s - DATA18 v.%s *****', media.title, mode, id, VERSION_NO)

        # Movie or content?
        is_content, is_movie, is_scene = [x == mode for x in MODES]
        urlMode = MODES[0:2][int(is_movie)]

        # Make url
        url = D18_ID_URL[urlMode] % id

        try:
            # Fetch HTML
            html = self.requestHTML(url)

            # Set tagline to URL
            metadata.tagline = url

            # Get the date
            date = self.findDateInTitle(media.title)

            # Find info div, optimization:
            rootElem = html.xpath('//div[@class="p8" and .//h1][1]')[0]

            # Set the date and year if found.
            if date is not None:
                self.updateDate(metadata, date)
            else: # try to find release date by other means:
                dateText = rootElem.xpath('.//p[contains(text(), "Release date")]//text()[last()][1]')[0].split('|')[-1].split(':')[-1].strip()
                self.updateDate(metadata, self.getDateFromString(dateText))

            # Get the title
            metadata.title = self.getStringContentFromXPath(rootElem, '//h1')
            metadata.title_sort = metadata.title

            # If Scene mode, open up movie to get summary, etc.:
            special_root = self.requestDataHTML('movie', id_parts[2]).xpath('//div[@class="p8" and .//h1][1]')[0] if is_scene else rootElem

            # Set the summary
            summary_title = ('Story' if is_content else 'Description') + ':'
            paragraph = special_root.xpath('.//div/p[b[contains(text(),"' + summary_title + '")]]/.')
            if paragraph:
                summary = paragraph[0].text_content().strip('\n').strip()
                summary = re.sub(summary_title, '', summary).strip()
                metadata.summary = summary

            # Set the studio, series, and director
            if is_content:
                # "Site" = Studio
                xpath = '//i[contains(text(), "Site")]/preceding-sibling::a[contains(@href, "http://www.data18.com/site")][1]/text()'
                metadata.studio = self.getStringContentFromXPath(html, xpath)

                metadata.collections.clear()
                xpath = '//i/preceding-sibling::a[contains(@href, "http://www.data18.com/site")][1]/text()'
                for c in html.xpath(xpath):
                    metadata.collections.add(c)
            else:
                xpath_base = './/p[b[contains(text(),"%s:")]]/a[1]/text()'
                studio, director, series = [(special_root.xpath(xpath_base % x) or [''])[0].strip() for x in ['Studio', 'Director', 'Serie']]
                metadata.collections.clear()
                metadata.directors.clear()
                if studio: metadata.studio = studio
                if director: metadata.directors.add(director)
                if series:
                    self.Log("Series: %s" % series)
                    metadata.collections.add(series)

            # Add the genres
            metadata.genres.clear()
            genres = rootElem.xpath('.//div[b[contains(text(),"Categories")]]/div/a/text()|//div[b[contains(text(),"Categories:")]]/a/text()')
            for genre in genres:
                genre = genre.strip()
                if genre and re.match(r'View Complete List', genre) is None:
                    metadata.genres.add(genre)

            # Add the performers
            metadata.roles.clear()
            performerXPathBase = 'p[@class="line1"]' if is_movie else 'div/ul/li'

            for performer in rootElem.xpath('.//' + performerXPathBase + '/a/img[@class="yborder"]'):
                role = metadata.roles.new()
                role.actor = performer.get('alt').strip()

                # Get the url for performer photo
                role.photo = re.sub(r'/stars/60/', '/stars/pic/', performer.get('src'))

            # Get posters and fan art.
            self.getImages(url, rootElem, metadata, is_movie, force)
        except Exception, e:
            Log.Error('Error obtaining data for item with id %s (%s) [%s] ', metadata.id, url, e.message)
            Log.Error( traceback.format_exc() )

        self.writeInfo(url, metadata)

    def hasProxy(self):
        return Prefs['imageproxyurl'] is not None

    def makeProxyUrl(self, url, referer):
        return Prefs['imageproxyurl'] + ('?url=%s&referer=%s' % (url, referer))

    def worker(self, queue, stoprequest):
        while not stoprequest.isSet():
            try:
                func, args, kargs = queue.get(True, 0.05)
                try: func(*args, **kargs)
                except Exception, e: self.Log(e)
                queue.task_done()
            except Queue.Empty:
                continue

    def addTask(self, queue, func, *args, **kargs):
        queue.put((func, args, kargs))

    def getImages(self, url, mainHtml, metadata, is_movie, force):
        queue, stoprequest = self.startImageQueue()
        results = []

        self.addTask(queue, self.getPosters, url, mainHtml, metadata, results, is_movie, force, queue)

        scene_image_max = 20
        try:
            scene_image_max = int(Prefs['sceneimg'])
        except:
            Log.Error('Unable to parse the Scene image count setting as an integer.')

        if scene_image_max >= 0:
            if is_movie:
                for i, scene in enumerate(mainHtml.xpath('.//div[p//b[contains(text(),"Scene ")]]')):
                    sceneName = self.getStringContentFromXPath(scene, 'p//b[contains(text(),"Scene ")]')
                    sceneUrl = self.getAnchorUrlFromXPath(scene, './/a[contains(@href, "go.data18.com") and img]')
                    if sceneUrl is not None:
                        #download all the images directly when they are referenced offsite
                        self.Log('Found scene (%s) - Getting art directly', sceneName)
                        anchorXPath = './/a[not(contains(@href, "download") ) and img]'
                        self.addTask(queue, self.getSceneImagesFromAlternate, i, scene, anchorXPath, url, metadata, scene_image_max, results, force, queue)
                        continue

                    sceneUrl = self.getAnchorUrlFromXPath(scene, './/a[not(contains(@href, "download") ) and img]')
                    if sceneUrl is None:
                        continue

                    self.Log('Found scene (%s) - Trying to get fan art from [%s]', sceneName, sceneUrl)

                    self.addTask(queue, self.getSceneImages, i, sceneUrl, metadata, scene_image_max, results, force, queue)
            else:
                internalRoot = mainHtml.xpath('.//div[p/b[contains(text(), " images")] and contains(p/text()[normalize-space()][1], "Total:")]')
                if len(internalRoot) > 0:
                    internalRoot = internalRoot[0]
                    # Take the first link, check how many images we have, pull them all directly:
                    internalCount = int(self.getStringContentFromXPath(internalRoot, './p/b[1]').split(' ', 2)[0])
                    internalReferer = internalRoot.xpath('.//div[1]/a')[0]
                    internalRefererBase = internalReferer.get('href').rsplit('/', 2)[0]
                    internalBaseUrl = '/'.join(internalReferer.xpath('./img')[0].get('src').split('/')[0:-2]) + '/'

                    #padCount = int(math.ceil(math.log10(internalCount)))
                    padCount = 2

                    for i in range(1, internalCount):
                        add = str(i).zfill(padCount)
                        imageUrl = internalBaseUrl + add  + '.jpg'
                        referer = internalRefererBase + add
                        self.addTask(queue, self.downloadImage, imageUrl, imageUrl, referer, False, 0, 1, results)
                else:
                    pathA = './/div[p[contains(text(), "Video Stills:")] and ./p/a]//a'
                    pathB = './/div[span[contains(text(), "Quick Timeline:")]]/following::div//li'
                    paths = pathA + '|' + pathB
                    self.addTask(queue, self.getSceneImagesFromAlternate, 1, mainHtml, pathA, url, metadata, scene_image_max, results, force, queue)

        self.setImages(queue, stoprequest, metadata, results)

    def getImageSet(self, metadata, tasks):
        queue, stoprequest = self.startImageQueue(len(tasks))
        results = []
        for t in tasks:
            self.addTask(queue, self.downloadImage, t[0], t[0], t[1], t[2], t[3], t[4], results)
        self.setImages(queue, stoprequest, metadata, results)

    def startImageQueue(self, limit = THREAD_MAX):
        queue = Queue.Queue(min(limit, THREAD_MAX))
        stoprequest = Thread.Event()
        for _ in range(THREAD_MAX): Thread.Create(self.worker, self, queue, stoprequest)
        return (queue, stoprequest)

    def setImages(self, queue, stoprequest, metadata, results):
        queue.join()
        stoprequest.set()
        from operator import itemgetter
        for i, r in enumerate(sorted(results, key=itemgetter('scene', 'index'))):
            proxy = Proxy.Preview(r['image'], sort_order=i+1) if r['isPreview'] else Proxy.Media(r['image'], sort_order=i+1)
            if r['scene'] > -1:
                metadata.art[r['url']] = proxy
            else:
                #self.Log('added poster %s (%s)', r['url'], i)
                metadata.posters[r['url']] = proxy

    def getPosters(self, url, mainHtml, metadata, results, is_movie, force, queue):
        get_poster_alt = Prefs['posteralt']
        i = 0

        #get full size posters
        #for poster in mainHtml.xpath('//a[@data-lightbox="covers"]/@href'):
        for poster in mainHtml.xpath('//a[@rel="covers"]/@href'):
            #self.Log('found %s', poster)
            if 'frontback' in poster:
                continue
            if poster in metadata.posters.keys() and not force:
                continue
            self.addTask(queue, self.downloadImage, poster, poster, url, False, i, -1, results)
            i += 1
        #Check for combined poster image and use alternates if available
        if get_poster_alt and i == 0:
            self.getPosterFromAlternate(url, mainHtml, metadata, results, force, queue)
            i = len(metadata.posters)

        if not is_movie:
            imageUrl = self.getImageUrlFromXPath(mainHtml, './/*[@id="moviewrap"]/img[contains(@src, "big.jpg")]')
            self.addTask(queue, self.downloadImage, imageUrl, imageUrl, url, False, i, -1, results)

        #Always get the lower-res poster from the main page that tends to be just the front cover.  This is close to 100% reliable
        imageUrl = self.getImageUrlFromXPath(mainHtml, '//img[@alt="Cover"]')
        self.addTask(queue, self.downloadImage, imageUrl, imageUrl, url, False, i, -1, results)

    def getSceneImages(self, sceneIndex, sceneUrl, metadata, sceneImgMax, result, force, queue):
        sceneHtml = self.requestHTML(sceneUrl)
        sceneTitle = self.getStringContentFromXPath(sceneHtml, '//h1[@class="h1big"]')

        imgCount = 0
        images = sceneHtml.xpath('//a[img[contains(@alt,"image")]]/img')
        if images is not None and len(images) > 0:
            firstImage = images[0].get('src')
            thumbPatternSearch = re.search(r'(th\w*)/', firstImage)
            thumbPattern = None
            if thumbPatternSearch is not None:
                thumbPattern = thumbPatternSearch.group(1)
            #get viewer page
            firstViewerPageUrl = images[0].xpath('..')[0].get('href')
            html = self.requestHTML(firstViewerPageUrl)

            imageCount = None
            imageCountSearch = re.search(r'Image \d+ of (\d+)', html.text_content())
            if imageCountSearch is not None:
                imageCount = int(imageCountSearch.group(1))
            else:
                # No thumbs were found on the page, which seems to be the case for some scenes where there are only 4 images
                # so let's just pretend we found thumbs
                imageCount = 4

            # plex silently dies or kills this off if it downloads too much stuff, especially if there are errors. have to manually limit numbers of images for now
            # workaround!!!
            if imageCount > 3:
                imageCount = 3

            # Find the actual first image on the viewer page
            imageUrl = self.getImageUrlFromXPath(html, '//div[@id="post_view"]//img')

            # Go through the thumbnails replacing the id of the previous image in the imageUrl on each iteration.
            for i in range(1,imageCount+1):
                imgId = '%02d' % i
                imageUrl = re.sub(r'\d{1,3}.jpg', imgId + '.jpg', imageUrl)
                thumbUrl = None
                if thumbPattern is not None:
                    thumbUrl = re.sub(r'\d{1,3}.jpg', imgId + '.jpg', firstImage)

                if imgCount > sceneImgMax:
                    #self.Log('Maximum background art downloaded')
                    break
                imgCount += 1

                if self.hasProxy():
                    imgUrl = self.makeProxyUrl(imageUrl, firstViewerPageUrl)
                    thumbUrl = None
                else:
                    imgUrl = imageUrl
                    thumbUrl = None

                if not imgUrl in metadata.art.keys() or force:
                    if thumbUrl is not None:
                        self.addTask(queue, self.downloadImage, thumbUrl, imgUrl, firstViewerPageUrl, True, i, sceneIndex, result)
                    else:
                        self.addTask(queue, self.downloadImage, imgUrl, imgUrl, firstViewerPageUrl, False, i, sceneIndex, result)

        if imgCount == 0:
            # Use the player image from the main page as a backup
            playerImg = self.getImageUrlFromXPath(sceneHtml, '//img[@alt="Play this Video" or contains(@src,"/hor.jpg")]')
            if playerImg is not None and len(playerImg) > 0:
                if self.hasProxy():
                    img = self.makeProxyUrl(playerImg, sceneUrl)
                else:
                    img = playerImg

                if not img in metadata.art.keys() or force:
                    self.addTask(queue, self.downloadImage, img, img, sceneUrl, False, 0, sceneIndex, result)

    #download the images directly from the main page
    def getSceneImagesFromAlternate(self, sceneIndex, sceneHtml, xpath, url, metadata, sceneImgMax, result, force, queue):
        self.Log('Attempting to get art from main page')
        i = 0
        for imageUrl in sceneHtml.xpath(xpath + '/img/@src'):
            if sceneImgMax > 0 and i + 1 > sceneImgMax:
                break

            if self.hasProxy():
                imgUrl = self.makeProxyUrl(imageUrl, url)
            else:
                imgUrl = imageUrl

            if not imgUrl in metadata.art.keys() or force:
                #self.Log('Downloading %s', imageUrl)
                self.addTask(queue, self.downloadImage, imgUrl, imgUrl, url, False, i, sceneIndex, result)
                i += 1

    def getPosterFromAlternate(self, url, mainHtml, metadata, results, force, queue):
        provider = ''

        # Prefer AEBN, since the poster seems to be better quality there.
        altUrl = self.getAnchorUrlFromXPath(mainHtml, './/a[b[contains(text(),"AEBN")]]')
        if altUrl is not None:
            provider = 'AEBN'
        else:
            provider = 'Data18Store'
            altUrl = self.getAnchorUrlFromXPath(mainHtml, './/a[contains(text(),"Available for")]')


        if altUrl is not None:
            self.Log('Attempting to get poster from alternative location (%s) [%s]', provider, altUrl)

            providerHtml = self.requestHTML(altUrl)
            frontImgUrl = None
            backImgUrl = None

            if provider is 'AEBN':
                frontImgUrl = self.getAnchorUrlFromXPath(providerHtml, './/div[@id="md-boxCover"]/a[1]')
                if frontImgUrl is not None:
                    backImgUrl = frontImgUrl.replace('_xlf.jpg', '_xlb.jpg')
            else:
                frontImgUrl = self.getImageUrlFromXPath(providerHtml, './/div[@id="gallery"]//img')
                if frontImgUrl is not None:
                    backImgUrl = frontImgUrl.replace('h.jpg', 'bh.jpg')

            if frontImgUrl is not None:
                if not frontImgUrl in metadata.posters.keys() or force:
                    self.addTask(queue, self.downloadImage, frontImgUrl, frontImgUrl, altUrl, False, 1, -1, results)

                if not backImgUrl is None and (not backImgUrl in metadata.posters.keys() or force):
                    self.addTask(queue, self.downloadImage, backImgUrl, backImgUrl, altUrl, False, 2, -1, results)
                return True
        return False

    def downloadImage(self, url, referenceUrl, referer, isPreview, index, sceneIndex, results):
        results.append({'url': referenceUrl, 'image': HTTP.Request(url, cacheTime=0, headers={'Referer': referer}, sleep=REQUEST_DELAY).content, 'isPreview': isPreview, 'index': index, 'scene': sceneIndex})

    def logList(self, what, l, l_loop, cb = lambda e: e):
    	if len(l) > 0:
    		self.Log('|\\')
    		for e in (l_loop or l): self.Log('| * %s:    %s' % (what, cb(e)))

    ### Writes metadata information to log.
    def writeInfo(self, url, metadata):
        self.Log('New data')
        self.Log('-----------------------------------------------------------------------')
        self.Log('* ID:              %s', metadata.id)
        self.Log('* URL:             %s', url)
        self.Log('* Title:           %s', metadata.title)
        self.Log('* Release date:    %s', str(metadata.originally_available_at))
        self.Log('* Year:            %s', metadata.year)
        self.Log('* Studio:          %s', metadata.studio)
        self.Log('* Director:        %s', metadata.directors[0] if len(metadata.directors) > 0  else '')
        self.Log('* Tagline:         %s', metadata.tagline)
        self.Log('* Summary:         %s', metadata.summary)
        self.logList('Collection', metadata.collections, 0)
        self.logList('Starring', metadata.roles, 0, lambda e: "%s (%s)" % (e.actor, e.photo))
        self.logList('Genre', metadata.genres, 0)
        self.logList('Poster URL', metadata.posters, metadata.posters.keys())
        self.logList('Fan art URL', metadata.art, metadata.art.keys())
        self.Log('***********************************************************************')

def safe_unicode(s, encoding='utf-8'):
    if s is None:
        return None
    if isinstance(s, basestring):
        if isinstance(s, types.UnicodeType):
            return s
        else:
            return s.decode(encoding)
    else:
        return str(s).decode(encoding)
