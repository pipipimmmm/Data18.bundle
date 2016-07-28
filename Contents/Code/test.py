from __init__ import *

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
                       roles, duration, extras):
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
        self.extras         = extras
        self.collections    = collections
        self.genres         = genres
        self.roles          = roles
        self.content_rating = content_rating
        self.originally_available_at = year

Media = namedtuple('Media',
            ['title', 'name', 'year', 'primary_metadata', 'filename'])

def UPDATE_TEST_BASE(id):
    name     = "thetitle"
    media    = Media(title = name, name  = name, year  = 1999,
                     primary_metadata = None, filename = None)

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

    metadata = Metadata(id = id,
                        year = 1999,
                        title = name,
                        duration = None,
                        studio   = 'thestudio',
                        tagline  = "thetagline",
                        summary  = 'thesummary',
                        content_rating = 'therating',
                        posters  = {},
                        art      = {},
                        extras   = Container(),
                        roles    = roles,
                        genres   = genres,
                        directors   = direct,
                        collections = colls)

    update(metadata, media, None)

def UPDATE_TEST(test):
    UPDATE_TEST_BASE(UTESTS[test].replace(D18_BASE_URL, ''))

def SEARCH_TEST(test):
    name    = STESTS[test]
    media   = Media(title = name, name = name, year = 2016,
                    primary_metadata = None, filename = None)
    results = Container()
    search(results, media, None)
    print(results)

def FSEARCH_TEST(test):
    fname   = FTESTS[test][0]
    name    = FTESTS[test][1]
    media   = Media(title = name, name = name, year = 2016,
                    primary_metadata = None, filename = fname)
    results = Container()
    search(results, media, None)
    print(results)

def FUPDATE_TEST(test): UPDATE_TEST_BASE(FUTESTS[test])

FTESTS  = [('[Fantasy HD] [August Ames] Handcuffed Hottie', 'Handcuffed Hottie'),
           ('[Exotic4k] DD Devyn Divine', 'DD Devyn Divine')]
FUTESTS = ['fantasy-hd$handcuffed-hottie',
           'exotic4k$dd-devyn-divine']

STESTS  = ["Jillian Janson in My Sister's Hot Friend",                   #  0
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

UTESTS  = ['http://www.data18.com/movies/1148631',                       #  0
           'http://www.data18.com/scenes/5423315-1148631',               #  1
           'http://www.data18.com/content/1161227',                      #  2
           'http://www.data18.com/content/1163750',                      #  3
           'http://www.data18.com/content/591261',                       #  4
           'http://www.data18.com/content/1148345',                      #  5
           'http://www.data18.com/content/1123820',                      #  6
           'http://www.data18.com/content/1124154',                      #  7
           'http://www.data18.com/content/1126544',                      #  8
           'http://www.data18.com/content/1125523',                      #  9
           'http://www.data18.com/content/1126410',                      #  10
           'http://www.data18.com/content/1126515',                      #  11
           'http://www.data18.com/content/1126893',                      #  12
           'http://www.data18.com/content/1129700',                      #  13
           'http://www.data18.com/content/319842',                       #  14
           'http://www.data18.com/content/5170363',                      #  15
           'http://www.data18.com/content/5170413',                      #  16
           'http://www.data18.com/content/1164368',                      #  17
           'http://www.data18.com/content/1164821',                      #  18
           'http://www.data18.com/content/2222107',                      #  19
           'http://www.data18.com/content/1161682',                      #  20
           'http://www.data18.com/content/2222109',                      #  21
           'http://www.data18.com/content/332598',                       #  22
           'http://www.data18.com/content/323844',                       #  23
           'http://www.data18.com/content/159593',                       #  24
           'http://www.data18.com/movies/1147862']                       #  25

#UPDATE_TEST(25)
#FSEARCH_TEST(1)
FUPDATE_TEST(1)