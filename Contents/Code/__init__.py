# PMS plugin framework
from PMS import *
from PMS.Objects import *
from PMS.Shortcuts import *
import urllib2
import re

####################################################################################################

VIDEO_PREFIX = "/video/sc10"
NAME = L('Title')

DEFAULT_CACHE_INTERVAL = 1800
OTHER_CACHE_INTERVAL = 300

ART           = 'ch10-background.jpg'
ICON          = 'icon-default.jpg'

BASE = "http://ten.com.au/watch-tv-episodes-online.htm"
TOKEN_URL = "http://api.v2.movideo.com/rest/session?key=movideoNetwork10&applicationalias=main-player"
#TOP_URL = "http://api.v2.movideo.com/rest/playlist/41326?depth=2"
TOP_URL = "http://api.v2.movideo.com/rest/playlist/"
TOP_SUFFIX = "&mediaLimit=50&omitFields=client,copyright,mediaSchedules,creationDate,cuePointsExist,defaultImage,encodingProfiles,filename,imageFilename,mediaFileExists,mediaType,lastModifiedDate,ratio,status,syndicated,tagProfileId"
SERIES_URL = "http://api.v2.movideo.com/rest/playlist/"
SERIES_SUFFIX = "&includeMedia=true&mediaLimit=50&omitFields=client%2CmediaSchedules"
PLAYER_URL = "http://ten.com.au/video-player.htm?"
CONFIG_URL = "http://ten.com.au/ten.video-settings.js"
CONFIG = {}
TOKEN = ""


####################################################################################################

def Start():
    global CONFIG
    global TOKEN
    
    
    TOKEN = str(OldGetToken())
    Log("Got Token: " + str(TOKEN))
    
    Plugin.AddPrefixHandler(VIDEO_PREFIX, VideoMainMenu, L('VideoTitle'), ICON, ART)

    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")

    MediaContainer.art = R(ART)
    MediaContainer.title1 = NAME
    DirectoryItem.thumb = R(ICON)
    
    HTTP.SetCacheTime(DEFAULT_CACHE_INTERVAL)
    #HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:2.0.1) Gecko/20100101 Firefox/4.0.1'

####################################################################################################

def GetGlobalConfig(URL):
   
    response = urllib2.urlopen(URL)
    conf = response.read();
    
    #pull out playlist and info to retrieve tokens
    split = re.findall('"[\w|\s|\-|:|\.|\/]*"',conf)
    configPlaylists = []
    client = {}
    clientFound = 0
    firstTime = 1
    prev = ""
    
    for x in split:
        if ('"client' in x) & (clientFound == 0):
            clientFound = 1
            
        if ('"client' in x) & (clientFound == 1):
            if client != {}:
                #client['playlistData'] = XML.ElementFromURL(TOP_URL + client['playlist'] + "?depth=2&token=" + client['token'] + TOP_SUFFIX)
                configPlaylists.append(client)
                
            client = {}
            client['clientID'] = re.search("[0-9]+",x).group(0)
        
        if (firstTime == 1) & (clientFound == 1) & ('"client' not in x):
            firstTime = 0
            prev = x.replace("\"","")
            
            
        elif (firstTime == 0) & (clientFound == 1):
            firstTime = 1
            if (prev == 'token'):
                tokenURL = "http://api.v2.movideo.com/rest/session?key=" + client['apiKey'] + "&applicationalias=" + client['flashAppName']
                Log("TOKEN URL>> "+ tokenURL)
                client[prev] = GetToken(tokenURL)
                Log(prev + " >> " + client[prev])
            else:
                client[prev] = x.replace("\"","")
                Log(prev + " >> " + x.replace("\"",""))
            
                
    return configPlaylists
    
def OldGetToken():
    xml = XML.ElementFromURL(TOKEN_URL)
    Log("In GetToken")
    Log(xml)
    return xml.xpath('/session')[0].find("token").text
    
    
def GetToken(URL):
    xml = XML.ElementFromURL(URL)
    return xml.xpath('/session')[0].find("token").text    

def GetSeriesForCategory(category):
    
    seriesSummaries = []
    Log("attempting>>"+ TOP_URL + category['playlist'] + "?depth=2&token=" + category['token'] + TOP_SUFFIX)   
    xml = XML.ElementFromURL(TOP_URL + category['playlist'] + "?depth=2&token=" + category['token'] + TOP_SUFFIX)
    
    #loop throough child playlist for selected category - pulling out show titles
    for series in xml.xpath('/playlist/childPlaylists/playlist/childPlaylists/playlist'):
        seriesSummary = {}
        seriesSummary['id'] = series.find('id').text
        title = series.find('title').text
        title = title.partition('|')[2] 
        seriesSummary['title'] = title
        seriesSummary['keywords'] = category
        seriesSummary['thumb'] = ""
        seriesSummaries.append(seriesSummary)
                
    return seriesSummaries


def GetSeriesInfo(seriesId):
    xml = XML.ElementFromURL(SERIES_URL + seriesId + "?token=" + TOKEN + SERIES_SUFFIX)
    SERIES_PLAYLIST_ID = xml.xpath('/playlist/childPlaylists/playlist')[0].find("id").text
    xml = XML.ElementFromURL(SERIES_URL + SERIES_PLAYLIST_ID + "?token=" + TOKEN + SERIES_SUFFIX)
    episodes = []
    
    #todo: handle genre/series#
    #todo handle playerURL
    for show in xml.xpath('/playlist/mediaList/media'):
        episode = {}
        episode['title'] = show.find('title').text
        episode['id'] = show.find('id').text
        #episode['filename'] = show.find('filename').text
        episode['description'] = show.find('description').text
        played = show.find('creationDate').text.partition("T")
        playedTime = played[2]
        playedDate = played[0]
        episode['airedDate'] = playedDate
        episode['airedTime'] = playedTime
        episode['thumb'] = show.find('imagePath').text + "96x128.png"
        episode['playerUrl'] = PLAYER_URL + "movideo_p="+ SERIES_PLAYLIST_ID + "&movideo_m=" + show.find('id').text
        episodes.append(episode)
    return episodes
    
def GetSeriesInfosForCategory(category):
    return GetSeriesForCategory(category)

#setup the Main Video Menu - ie. get Top level categories
def VideoMainMenu():
    dir = MediaContainer(viewGroup="InfoList")
    conf = GetGlobalConfig(CONFIG_URL)
    for x in conf:
        dir.Append(Function(DirectoryItem(CategoryMenu, x['accName']), category=x))    
    return dir

#Handle drill down on a category
def CategoryMenu(sender, category):
    
    seriesInfos = GetSeriesInfosForCategory(category)
    Log(str(seriesInfos))
    
    #if category != "recent":
    #   seriesInfos.sort(key=lambda si: si["title"].lower())
    
    dir = MediaContainer(viewGroup="InfoList", title2=category['accName'])
    
    for seriesInfo in seriesInfos:
        dir.Append(Function(DirectoryItem(SeriesMenu, seriesInfo['title'], thumb=seriesInfo['thumb']), 
                   series = seriesInfo[xml])
    
    return dir

#Handle drill down on a series - ie. get episodes
def SeriesMenu(sender, seriesId, title2):
    dir = MediaContainer(viewGroup="InfoList", title2=title2)
    GetSeriesInfo(seriesId)
    for episode in GetSeriesInfo(seriesId):
        # This is supposed to be the broadcast date to give an idea of how recent the episode is.  The
        # element in the json that seems to be broadcast date doesn't always seem to be populated though.
        # Hopefully the episodes are usually uploaded on the same day as they're broadcast.
        
        description = "Broadcast " + episode['airedDate'] + " at " + episode['airedTime'] + "." +"\n"
        description += "\n" + episode['description'] + "\n"
        
        dir.Append(WebVideoItem(episode['playerUrl'], title=episode['title'], subtitle="",
                               summary=description, thumb=episode['thumb'], duration=""))
    return dir


