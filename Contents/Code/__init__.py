# PMS plugin framework
import re
import urllib
import string
####################################################################################################

VIDEO_PREFIX = "/video/Channel10"
NAME = L('Title')
DEFAULT_CACHE_INTERVAL = 1800
OTHER_CACHE_INTERVAL = 300
ART           = 'ch10-background.jpg'
ICON          = 'icon-default.jpg'
API_URL = "http://api.brightcove.com/services/library"
#API TOKEN retrieved from: http://code.ten.com.au/video/bc.ten_video.common.1.1.js
API_TOKEN = "lWCaZyhokufjqe7H4TLpXwHSTnNXtqHxyMvoNOsmYA_GRaZ4zcwysw.."
#Query to find all TV shows
API_COMMAND_SUFFIX = "&page_size=100&none=prevent_web:true&get_item_count=true&media_delivery=http&video_fields=id,name,endDate,shortDescription,length,tags,thumbnailURL,creationDate,length,FLVURL&custom_fields=tv_channel,tv_show,tv_season,cast,video_type_long_form,video_type_short_form"
API_COMMAND = "command=search_videos"
DEFAULT_SEARCH = "sort_by=PUBLISH_DATE:ASC"
TEN_SHOWS = "http://ten.com.au/NWT_showlist.js"

####################################################################################################

def Start():
    
    Plugin.AddPrefixHandler(VIDEO_PREFIX, VideoMainMenu, L('VideoTitle'), ICON, ART)
    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    MediaContainer.art = R(ART)
    MediaContainer.title1 = NAME
    DirectoryItem.thumb = R(ICON)
    HTTP.SetCacheTime(DEFAULT_CACHE_INTERVAL)
    
####################################################################################################

def QueryShow(showName):
    pageCounter = 0
    searchTerm = "&all=tv_show:"+urllib.quote(showName)
    return GetShowsByCriteria(searchTerm,DEFAULT_SEARCH,pageCounter)

def ParseShow(entry):
        Log("found show" + entry['name'])
        show = {}
        show['title'] =         entry['name']
        show['id'] =            entry['id'] 
        show['description'] =   entry['shortDescription']
        show['creationDate'] = int(entry['creationDate'])
        show['creation_date'] = Datetime.FromTimestamp(0) + Datetime.Delta(milliseconds=int(entry['creationDate']))
        show['thumbnail'] =     entry['thumbnailURL']
        show['length'] =        int(entry['length'])
        try:
            show['season'] =    int(entry['customFields']['tv_season'])
        except:
            show['season'] =    0
        try:
                show['show'] =          entry['customFields']['tv_show']
        except:
                show['show'] = entry['name']
        try:
            show['episode'] = int(Regex('Ep\. (\d+)').search(show['title']).group(0)[4:])
        except:
            show['episode'] = 0
    
        
        show['playerURL'] = 'http://ten.com.au/watch-tv-episodes-online.htm?vid=' + str(show['id'])
        return show
        
def GetShowsByCriteria(searchTerm,searchOrder, pageNumber):
    mediaURL = API_URL + "?"+ API_COMMAND+ searchTerm + "&page_number=" + str(pageNumber) + API_COMMAND_SUFFIX + "&token=" + API_TOKEN
    json = JSON.ObjectFromURL(mediaURL, cacheTime=1800)
    numShows = json['total_count']
    pageLimit = (numShows/100)
    shows = []
    Log("Got shows:")
    Log(str(json))
    for entry in json['items']:
        shows.append(ParseShow(entry))  
    
     
    #sorted(shows, key=lambda show: show[0])
    #Log("First key after sorting: "+ shows[0][0])
    # do we need to get many pages for an individual show?
    
    #for pageCounter in range(1, pageLimit):
    #    Log("Getting page " + str(pageCounter) +" of " + str(pageLimit))
    #    mediaURL = API_URL + "?"+ API_COMMAND+"&" + searchTerm + "&page_number="+str(pageCounter)+API_COMMAND_SUFFIX+"&token="+API_TOKEN
    #    json = JSON.ObjectFromURL(mediaURL, cacheTime=1800)
    #    for entry in json['items']:
    #        shows.append(ParseShow(entry))          
    #
    return shows

def GetShowsByChannel(channel):
    searchTerm = "all=tv_channel:"+channel
    searchOrder = DEFAULT_SEARCH
    return GetShowsByCriteria(searchTerm,searchOrder)
    
@handler('/video/Channel10', NAME)
def VideoMainMenu():
    dir = MediaContainer(viewGroup="InfoList"  )
    result = HTTP.Request(url=TEN_SHOWS, cacheTime=1800)
    result = str(result)[13:]
    
    result = JSON.ObjectFromString(result)
    Log('Shows pre sort:')
    Log(str(result))
    shows = result["shows"]
    
    shows.sort(key=lambda show: show["showName"].lower())
    Log('Shows post sort')
    Log(str(shows))
    for showDetail in shows:
        if showDetail['showName'] != '':
            dir.Append(Function(DirectoryItem(ShowMenu, showDetail['showName']), show=showDetail['showName']))           
    return dir

@route('/video/Channel10/ShowMenu')
def ShowMenu(sender, show):
    episodes = QueryShow(show)
    oc = ObjectContainer(title2=show)
    
    #pad episodes to order eg. S01E12 = 102, vs. S01E1 = 101
    episodes.sort(key=lambda episode: episode['creationDate'], reverse=True)
    
    for episode in episodes:
        Log(str(episode))        
        oc.add(EpisodeObject(   
                    url = episode['playerURL'],
                    rating_key = episode['id'],
                    show = episode['show'],
                    season = episode['season'],
                    absolute_index = episode['episode'],
                    title = episode['title'],
                    summary = episode['description'],
                    originally_available_at = episode['creation_date'],
                    duration = episode['length'],
                    thumb = episode['thumbnail']
                ))
    
    return oc