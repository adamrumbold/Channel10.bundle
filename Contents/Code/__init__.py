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
TOP_SUFFIX = "&omitFields=client,copyright,creationDate,cuePointsExist,defaultImage,encodingProfiles,filename,mediaFileExists,mediaType,lastModifiedDate,ratio,status,syndicated,tagProfileId"
CONFIG_URL = "http://ten.com.au/ten.video-settings.js"
API_URL = "http://api.v2.movideo.com/rest/"

####################################################################################################

def Start():
    
    Plugin.AddPrefixHandler(VIDEO_PREFIX, VideoMainMenu, L('VideoTitle'), ICON, ART)
    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")

    MediaContainer.art = R(ART)
    MediaContainer.title1 = NAME
    DirectoryItem.thumb = R(ICON)
    
    HTTP.SetCacheTime(DEFAULT_CACHE_INTERVAL)
    
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
            if (client != {}) :
                if (client['accName'] != 'TEN News') & (client['token'] != ""):
                    #now we have token get parent playlist as required for some client configs
                    rootPlaylistURL = API_URL + "playlist/" + client['playlist'] + "/firstRootPlaylist?token=" + client['token']
                    newPlaylistID = GetRootPlaylist(rootPlaylistURL)
                    Log("playlist >>>> " + newPlaylistID)
                    client['playlist'] = newPlaylistID
                    configPlaylists.append(client)
                    
            client = {}
            client['clientID'] = re.search("[0-9]+",x).group(0)
        
        if (firstTime == 1) & (clientFound == 1) & ('"client' not in x):
            firstTime = 0
            prev = x.replace("\"","")
                        
        elif (firstTime == 0) & (clientFound == 1):
            firstTime = 1
            if (prev == 'token'):
                tokenURL = API_URL + "session?key=" + client['apiKey'] + "&applicationalias=" + client['flashAppName']
                Log("TOKEN URL>> "+ tokenURL)
                try:
                    client[prev] = GetToken(tokenURL)
                except:
                    client[prev] = ""
                Log(prev + " >> " + client[prev])
            else:
                client[prev] = x.replace("\"","")
                Log(prev + " >> " + x.replace("\"",""))
    return configPlaylists
    
def GetRootPlaylist(URL):
    xml = XML.ElementFromURL(URL)
    return xml.xpath('/playlist')[0].find("id").text    
    
def GetToken(URL):
    xml = XML.ElementFromURL(URL)
    return xml.xpath('/session')[0].find("token").text    

def GetImage(mediaID,token):
    imageURL = API_URL + "media/" + mediaID + "/images?token=" + token
    xml = XML.ElementFromURL(imageURL)
    Log("Image URL>>" + xml.xpath('/list/image/url')[2].text)
    return xml.xpath('/list/image/url')[2].text
    
#use API to get media object for a given playlist
def GetMedia(playlistID,token):
    mediaURL = API_URL + "playlist/" + playlistID + "?depth=2&token=" + token + TOP_SUFFIX
    Log("MediaURL >> " + mediaURL)
    xml = XML.ElementFromURL(mediaURL)
    shows = []
    for media in xml.xpath('/playlist/mediaList/media'):
        show = {}
        show['title'] = media.find('title').text
        show['description'] = media.find('description').text
        show['duration'] = media.find('duration').text
        show['ID'] = media.find('id').text
        try:
            #thumb paths are slow to retrieve and not displaying so ignore
            #show['thumb'] = GetImage(show['ID'],token)
            media.xpath("defaultImage/url")[0].text
        except:
            show['thumb'] = ""            
        try:
            show['airedDate'] = media.xpath("mediaSchedules/mediaSchedule/start")[0].text.partition("T")[0]
            show['airedTime'] = media.xpath("mediaSchedules/mediaSchedule/start")[0].text.partition("T")[2]
        except:
            show['airedDate'] = ""
            show['airedTime'] = ""
        
        shows.append(show)    
    return shows
   
#use API to get child playlist(s) for any given playlist        
def GetChildPlaylists(playlistID,token,videoPageURL):
    childURL = API_URL + "playlist/" + playlistID + "?onlyChildPlaylists=true&depth=2&token=" + token
    Log("attempting child playlist for >>" + childURL )
    xml = XML.ElementFromURL(childURL)
    playlists = []
    try:
        for plist in xml.xpath('/playlist/childPlaylists/playlist'):
            playlist = {}
            playlist['token'] = token
            playlist['videoPageURL'] = videoPageURL
            playlist['ID'] = plist.find('id').text
            playlist['title'] = plist.find('title').text
            playlist['description'] = plist.find('description').text
            playlist['thumb'] = ""
            playlists.append(playlist)
    except:
        pass
    
    return playlists    
        
#setup the Main Video Menu - ie. get Top level categories
def VideoMainMenu():
    dir = MediaContainer(viewGroup="InfoList")
    conf = GetGlobalConfig(CONFIG_URL)
    for x in conf:
        temp = {}
        temp['ID'] = x['playlist']
        temp['token'] = x['token']
        temp['videoPageURL'] = x['videoPageURL']
        temp['title'] = x['accName']
        dir.Append(Function(DirectoryItem(PlaylistMenu, x['accName']), playlist = temp ))    
    return dir

def PlaylistMenu(sender, playlist):
    dir = MediaContainer(viewGroup="InfoList", title2=playlist['title'])
    childPlist = GetChildPlaylists(playlist['ID'],playlist['token'],playlist['videoPageURL'])
    
    if len(childPlist) > 0:
        for plist in childPlist:
            dir.Append(Function(DirectoryItem(PlaylistMenu, plist['title'], thumb=plist['thumb']), 
                       playlist = plist))
    else:
        mediaList = GetMedia(playlist['ID'],playlist['token'])
        for show in mediaList:
            description = "Broadcast " + show['airedDate'] + " at " + show['airedTime'] + "." +"\n"
            description += "\n" + show['description'] + "\n"
            showURL = playlist['videoPageURL'] + "?movideo_p=" + playlist['ID'] + "&movieo_m=" + show['ID']
            Log(show['title'] + " >> " + showURL)
            dir.Append(WebVideoItem(showURL, title=show['title'], subtitle="",
                                   summary=description, thumb=show['thumb'], duration=show['duration']))
    return dir