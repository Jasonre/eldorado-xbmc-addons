import xbmc, xbmcgui, xbmcplugin
import urllib
import re, sys, os

try:
    from sqlite3 import dbapi2 as sqlite
    print "Loading sqlite3 as DB engine"
except:
    from pysqlite2 import dbapi2 as sqlite
    print "Loading pysqlite2 as DB engine"

import urlresolver

try:
    from addon.common.addon import Addon
    from addon.common.net import Net
except:
    print 'Failed to import script.module.addon.common'
    xbmcgui.Dialog().ok("PFTV Import Failure", "Failed to import addon.common", "A component needed by PFTV is missing on your system", "Please visit www.xbmchub.com for support")

net = Net()
addon = Addon('plugin.video.solarmovie', sys.argv)

try:
    from metahandler import metahandlers
except:
    print 'Failed to import script.module.metahandler'
    xbmcgui.Dialog().ok("PFTV Import Failure", "Failed to import Metahandlers", "A component needed by PFTV is missing on your system", "Please visit www.xbmchub.com for support")


DB = os.path.join(addon.get_profile(), 'solarmovie.db')
BASE_URL = 'http://www.solarmovie.so'


enableMeta = True
if addon.get_setting('enableMeta') == 'false':
        enableMeta = False

GENRES = ['Action', 'Adventure', 'Animation', 'Biography', 'Comedy', 
          'Crime', 'Documentary', 'Drama', 'Family', 'Fantasy', 'Film-Noir', 'Game-Show'
          'History', 'Horror', 'Music', 'Musical', 
          'Mystery', 'News', 'Reality-TV', 'Romance', 'Sci-Fi', 'Short', 'Sport', 'Talk-Show'
          'Thriller', 'War', 'Western']

##### Queries ##########
mode = addon.queries['mode']
url = addon.queries.get('url', None)
section = addon.queries.get('section', None)
img = addon.queries.get('img', None)
genre = addon.queries.get('genre', None)
year = addon.queries.get('year', None)
letter = addon.queries.get('letter', None)
page = addon.queries.get('page', None)
episodes = addon.queries.get('episodes', None)
listitem = addon.queries.get('listitem', None)
query = addon.queries.get('query', None)
startPage = addon.queries.get('startPage', None)
numOfPages = addon.queries.get('numOfPages', None)
play = ''

addon.log('---------------------------------------------------------------')
addon.log('--- Addon Version: ' + addon.get_version())
addon.log('--- Mode: ' + str(mode))
addon.log('--- URL: ' + str(url))
addon.log('--- Genre: ' + str(genre))
addon.log('--- Section: ' + str(section))
addon.log('--- Letter: ' + str(letter))
addon.log('--- Year: ' + str(year))
#addon.log('--- IMDB: ' + str(imdb_id))
#addon.log('--- Season: ' + str(season))
#addon.log('--- Episode: ' + str(episode))
addon.log('---------------------------------------------------------------')


def get_html(page_url):
    
    addon.log("Retrieving URL: %s" % page_url)
    html = net.http_GET(page_url).content
    
    import HTMLParser
    h = HTMLParser.HTMLParser()
    html = h.unescape(html)
    return html.encode('utf-8')


def initDatabase():
    addon.log("Building solarmovie Database")
    if ( not os.path.isdir( os.path.dirname(
                ) ) ):
        os.makedirs( os.path.dirname( DB ) )
    db = sqlite.connect( DB )
    cursor = db.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS seasons (season UNIQUE, contents);')
    cursor.execute('CREATE TABLE IF NOT EXISTS favorites (type, name, url, img);')
    db.commit()
    db.close()


def SaveFav(type, name, url, img, year):
   if type != 'tv': type = 'movie'
   db = sqlite.connect( DB )
   cursor = db.cursor()
   statement  = 'INSERT INTO favorites (type, name, url, year) VALUES (?,?,?,?)'
   try: 
      cursor.execute(statement, (type, urllib.unquote_plus(name.decode('utf-8')), url, year))
      builtin = 'XBMC.Notification(Save Favorite,Added to Favorites,2000)'
      xbmc.executebuiltin(builtin)
   except sqlite.IntegrityError: 
      builtin = 'XBMC.Notification(Save Favorite,Item already in Favorites,2000)'
      xbmc.executebuiltin(builtin)
   db.commit()
   db.close()


def GetTitles(section, url, html= None, episode = False, startPage= '1', numOfPages= '1'): # Get Titles
        addon.log('Solarmovie get Titles Menu %s \n' % url)

        # handle paging
        pageUrl = url
        if int(startPage)> 1:
                pageUrl = url + '?page=' + startPage
        if html == None:
                html = get_html(pageUrl)

        start = int(startPage)
        end = start + int(numOfPages)
        last = 2
        match  = re.findall('<li><a href=.+?page=([\d]+)"', html)
        if match:
                last = match[-1]
        #print start + ':' + end + ':' + last
        for page in range( start, min(last, end)):
                if ( page != start):
                        pageUrl = url + '?page=' + str(page)
                        html = get_html(pageUrl)                
                match = re.compile('class="coverImage" title="(.+?)".+?href="(.+?)".+?src="(.+?)".+?<a title=".+?\(([\d]+)\)', re.MULTILINE | re.IGNORECASE | re.DOTALL).findall(html)
                for name, movie_url, img, year in match:
                        if section == 'tv' and episode == False:
                                if enableMeta:
                                        meta = metaget.get_meta('tvshow', name, year)
                                        if meta['imdb_id'] =='' and meta['tvdb_id'] =='':
                                                meta = metaget.get_meta('tvshow', name)
                                        #addon.add_directory({'mode': 'GetSeasons', 'section': section, 'url': BASE_URL + movie_url, img= meta['cover_url']}, meta, img=meta['cover_url'], fanart=meta['backdrop_url'], total_items=len(match))
                                else:        
                                        addon.add_directory({'mode': 'GetSeasons', 'section': section, 'url': BASE_URL + movie_url, 'img': img }, {'title':  name}, img= img)
                        else:
                                cm = []
                                if section == 'movie' and enableMeta:
                                        meta = metaget.get_meta('movie', name, year)
                                        if meta['imdb_id'] =='':
                                                meta = metaget.get_meta('movie', name)
                                        if 'trailer_url' in meta and meta['trailer_url']:
                                                trurl = meta['trailer_url']
                                                trurl = re.sub('&feature=related','',trurl)
                                                trurl = trurl.encode('base-64').strip()
                                                runstring = 'XBMC.RunPlugin(%s?mode=PlayTrailer&url=%s)' %(sys.argv[0], trurl)
                                                cm.append(('Watch Trailer', runstring))
                                        cm.append(('Show Information', 'XBMC.Action(Info)'))        
                                        addon.add_directory({'mode': 'GetLinks', 'section': section, 'url': BASE_URL + movie_url}, meta,
                                                img= meta['cover_url'], fanart= meta['backdrop_url'], contextmenu_items= cm, context_replace=True)
                                else:       
                                        addon.add_directory({'mode': 'GetLinks', 'section': section, 'url': BASE_URL + movie_url}, {'title':  name}, img= img)
        # keep iterating until the laast page is reached
        if end < last:
                addon.add_directory({'mode': 'GetTitles', 'url': url, 'startPage': str(end), 'numOfPages': numOfPages}, {'title': 'Next...'})
        addon.end_of_directory()


def PlayTrailer(url):
    url = url.decode('base-64')
    addon.log('Attempting to resolve and play trailer at %s' % url)
    sources = []
    hosted_media = urlresolver.HostedMediaFile(url=url)
    sources.append(hosted_media)
    source = urlresolver.choose_source(sources)
    if source: stream_url = source.resolve()
    else: stream_url = ''
    xbmc.Player().play(stream_url)


def GetLinks(section, url): # Get Movie Links
        addon.log('In GetLinks %s' % url)
        html = get_html(url)
        sources = []
        listitem = xbmcgui.ListItem()
        if  ( section == 'tv'):
                match = re.search('bradcramp.+?href=".+?>(.+?)<.+?href=".+?>        Season (.+?) .+?[&nbsp;]+Episode (.+?)<', html, re.MULTILINE | re.IGNORECASE | re.DOTALL)
                listitem.setInfo('video', {'TVShowTitle': match.group(1), 'Season': int(match.group(2)), 'Episode': int(match.group(3)) } )
        else:
                match = re.search('float:left;">(.+?)<em.+?html">[\n]*(.+?)</a>', html, re.MULTILINE | re.IGNORECASE | re.DOTALL)
                listitem.setInfo('video', {'Title': 'blah', 'Year': 2013})

        match =  re.compile('<tr id=.+?href="(.+?)">(.+?)<.+?class="qualityCell">(.+?)<', re.MULTILINE | re.DOTALL | re.IGNORECASE).findall(html)
        addon.log(' length of match is %d' % len(match))
        if len(match) > 0:
                count = 1
                for url, host, quality in match:
                        name = str(count) + ". " + host +  ' - ' + quality.strip()
                        if urlresolver.HostedMediaFile(host=host, media_id='xxx'):
                                addon.add_directory({'mode': 'PlayVideo', 'url': url, 'listitem': listitem}, {'title':  name})
                                count = count + 1 
                addon.end_of_directory()
        else:
                return


def PlayVideo(url, listitem):
        addon.log('in PlayVideo')
        match = re.search( '/.+?/.+?/(.+?)/', url)
        videoId = match.group(1)
        url = BASE_URL + '/link/play/' + videoId + '/'
        html = get_html(url)
        match = re.search( '<iframe.+?src="(.+?)"', html, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        link = match.group(1)
        link = link.replace('/embed/', '/file/')
        stream_url = urlresolver.HostedMediaFile(link).resolve()
        print stream_url
        xbmc.Player().play(stream_url, listitem)


def GetDomain(url):
        tmp = re.compile('//(.+?)/').findall(url)
        domain = 'Unknown'
        if len(tmp) > 0 :
            domain = tmp[0].replace('www.', '')
        return domain


def LoadCategories(section): #Categories
    addon.add_directory({'mode': 'BrowseLatest', 'section': section}, {'title':  'Latest'})
    addon.add_directory({'mode': 'BrowsePopular', 'section': section}, {'title':  'Popular'})
    addon.add_directory({'mode': 'BrowseYear', 'section': section}, {'title':  'Year'})
    addon.add_directory({'mode': 'BrowseGenre', 'section': section}, {'title':  'Genres'})
    #addon.add_directory({'mode': 'BrowseAtoZ', 'section': section}, {'title':  'A-Z'})
    addon.add_directory({'mode': 'GetSearchQuery', 'section': section}, {'title':  'Search'})
    #addon.add_directory({'mode': 'GetTitles', 'section': section}, {'title':  'Favorites'})
    addon.end_of_directory()


def BrowseLatest(section=None):
    addon.log('Browse Latest screen')
    html = get_html(BASE_URL)
    titles = ""
    if section == 'movies':
        match1 = re.search('id="tab-latest"', html)
        match2 = re.search('<h2>Latest TV Shows</h2>', html)
        titles = html[match1.end():match2.start()]
    else:
        match1 = re.search('<h2>Latest TV Shows</h2>', html)
        match2 = re.search('<div id="sidebar">', html)
        titles = html[match1.end():match2.start()]
    GetTitles(section, "", html=titles, episode=True, startPage= 1, numOfPages= 2)


def BrowsePopular(section=None):
    addon.log('Browse Popular screen')
    url = BASE_URL
    if section == 'tv':
        url = BASE_URL + '/tv'
    html = get_html(url)
    titles = ""
    if section == 'movies':
        match1 = re.search('id="tab-popular">', html)
        match2 = re.search('id="tab-latest"', html)
        titles = html[match1.end():match2.start()]
    else:
        match1 = re.search('id="topcontent"', html)
        match2 = re.search('id="sidebar"', html)
        titles = html[match1.end():match2.start()]
    GetTitles(section, "", html=titles, startPage= 1, numOfPages= 2)


def BrowseAtoZ(section=None, genre=None): 
    addon.log('Browse by alphabet screen')
    addon.add_directory({'mode': 'GetResults', 'section': section, 'genre': genre, 'letter': '-'}, {'title':  '#123'})
    for character in AZ_DIRECTORIES:
                addon.add_directory({'mode': 'GetResults', 'section': section, 'genre': genre, 'letter': character}, {'title':  character})
    addon.end_of_directory()


def BrowseYear(section=None, genre=None):
    addon.log('Browse by year screen')
    url = ''
##  if section == 'movies':
##                url = BASE_URL + '/years.html'
##        else:
##                url = BASE_URL + '/' + section + '/years.html'
##        html = net.http_GET(url).content
##        match = re.search('<div class="genresPage">', html, re.MULTILINE | re.DOTALL )
##        html = html[match.end():]
##        years = re.compile('href="(.+?)".+?class="tag\d+">(.+?)<', re.MULTILINE | re.DOTALL).findall(html)
##        if section == 'movies':
##                url = '/watch-movies-of-2012.html'
##                addon.add_directory({'mode': 'GetTitles', 'url': BASE_URL + url, 'section': section, 'genre': genre}, {'title':  '2012'})
##                url = '/watch-movies-of-2011.html'
##                addon.add_directory({'mode': 'GetTitles', 'url': BASE_URL + url, 'section': section, 'genre': genre}, {'title':  '2011'})
##        else:
##                url = '/tv/watch-tv-shows-2012.html'
##                addon.add_directory({'mode': 'GetTitles', 'url': BASE_URL + url, 'section': section, 'genre': genre}, {'title':  '2012'})
##                url = '/tv/watch-tv-shows-2011.html'
##                addon.add_directory({'mode': 'GetTitles', 'url': BASE_URL + url, 'section': section, 'genre': genre}, {'title':  '2011'})
    for year in range(2013, 1930, -1):
        if section == 'movies':
            url = BASE_URL + '/watch-movies-of-' + str(year) + '.html'
        else:
            url = BASE_URL + '/tv/watch-tv-shows-' + str(year) + '.html'
        addon.add_directory({'mode': 'GetTitles', 'url': url, 'section': section, 'genre': genre, 'startPage': '1', 'numOfPages': '3'}, {'title':  str(year)})
    addon.end_of_directory()


def BrowseGenre(section=None, year=None): 
    addon.log('Browse by genres screen')
    url = ''
    #if section == 'movies':
        #        url = BASE_URL + '/genres.html'
        #else:
        #       url = BASE_URL + '/' + section + '/genres.html'
        #html = net.http_GET(url).content
        #match = re.search('<div class="genresPage">', html, re.MULTILINE | re.DOTALL )
        #html = html[match.end():]
        #genres = re.compile('href="(.+?)".+?class="tag\d+">(.+?)<', re.MULTILINE | re.DOTALL).findall(html)
    for genre in GENRES:
                if section == 'movies':
                        url = BASE_URL + '/watch-' + genre + '-movies.html'
                else:
                        url = BASE_URL + '/tv/watch-' + genre + '-tv-shows.html'
                addon.add_directory({'mode': 'GetTitles', 'url': url, 'section': section, 'year': year, 'startPage': '1', 'numOfPages': '3'}, {'title':  genre})
    addon.end_of_directory()


def GetSearchQuery(section):
    last_search = addon.load_data('search')
    if not last_search: last_search = ''
    keyboard = xbmc.Keyboard()
    if section == 'tv': keyboard.setHeading('Search TV Shows')
    else: keyboard.setHeading('Search Movies')
    keyboard.setDefault(last_search)
    keyboard.doModal()
    if (keyboard.isConfirmed()):
        query = keyboard.getText()
        addon.save_data('search',query)
        Search(section, query)
    else:
        return

 
def Search(section, query):
        cat = 'tv'
        if section == 'movies':
                cat = 'movie'
        url = BASE_URL + '/' + cat + '/search/' + query + '/'
        GetTitles(section, url, startPage= 1, numOfPages= 3)


def GetResults(section=None, genre=None, letter=None, page=None): 
    
    if section == 'tv': xbmcplugin.setContent( int( sys.argv[1] ), 'tvshows' )
    else: xbmcplugin.setContent( int( sys.argv[1] ), 'movies' )

    suffix = '/' + genre + '/'
    
    if not letter:
            suffix = suffix + 'ALL/'
    else:
            suffix = suffix + letter + '/'
            
    url = BASE_URL + '/browse/' + section + suffix
    GetTitles(section, url, startPage= 1, numOfPages= 3)


def GetSeasons(section, url, img):
    xbmcplugin.setContent( int( sys.argv[1] ), 'seasons' )
    addon.log('Seasons for TV Show')
    html = get_html(url)
    match = re.search( 'coverImage">.+?src="(.+?)"', html, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    img = match.group(1)
    shows = re.compile('<a class="behavior_trigger_season.+?id="trigger_(.+?)"(.+?)<h4>', re.DOTALL).findall(html)   
    if not shows:
        addon.log('couldn\'t find seasons')
    else:
        for season_name, episodes in shows:
            season_name = season_name.replace( '_',  ' ')
            addon.add_directory({'mode': 'GetEpisodes', 'section': section, 'img': img, 'episodes': episodes.encode('utf-8')}, {'title':  season_name}, img= img)
    addon.end_of_directory()


def GetEpisodes(section, img, episodes):
    addon.log('in Get Episodes')
    xbmcplugin.setContent( int( sys.argv[1] ), 'episodes' )
    episodes = re.compile('epnomber.+?href="(.+?)">(.+?)<.+?/episode-.+?/">(.+?)<.+?/episode-.+?/.+?>(.+?)<', re.IGNORECASE | re.MULTILINE | re.DOTALL).findall(episodes)
    for epurl, epnbr, title, numOfLinks in episodes:
        addon.add_directory({'mode': 'GetLinks', 'section': section, 'url': BASE_URL + epurl}, {'title':  epnbr + ' - ' + title +  ' (' + numOfLinks.strip() + ')'}, img= img)
    addon.end_of_directory()


if play:

    try:
        import urlresolver
    except:
        addon.log_error("Failed to import script.module.urlresolver")
        xbmcgui.Dialog().ok("Solar Movie Import Failure", "Failed to import URLResolver", "A component needed by PFTV is missing on your system", "Please visit www.xbmchub.com for support")


if mode == 'main': 
     addon.log('in main menu')
     addon.add_directory({'mode': 'LoadCategories', 'section': 'movies'}, {'title':  'Movies'})
     addon.add_directory({'mode': 'LoadCategories', 'section': 'tv'}, {'title':  'TV Shows'})
     addon.add_directory({'mode': 'ResolverSettings'}, {'title':  'Resolver Settings'})
     addon.end_of_directory()


elif mode == 'LoadCategories': 
    LoadCategories(section)
elif mode == 'BrowseAtoZ': 
    BrowseAtoZ(section)
elif mode == 'BrowseYear': 
    BrowseYear(section)
elif mode == 'BrowseGenre': 
    BrowseGenre(section)
elif mode == 'BrowseLatest': 
    BrowseLatest(section)
elif mode == 'BrowsePopular': 
    BrowsePopular(section)
elif mode == 'GetResults': 
    GetResults(section, genre, letter, page)
elif mode == 'GetTitles': 
    GetTitles(section, url, startPage= startPage, numOfPages= numOfPages)
elif mode == 'GetLinks':
    GetLinks(section, url)
elif mode == 'GetSeasons':
    GetSeasons(section, url, img)
elif mode == 'GetEpisodes':
    GetEpisodes(section, img, episodes)
elif mode == 'GetSearchQuery':
    GetSearchQuery(section)
elif mode == 'Search':
    Search(section, query)
elif mode == 'PlayVideo':
    PlayVideo(url, listitem)
elif mode == 'ResolverSettings':
     urlresolver.display_settings()
