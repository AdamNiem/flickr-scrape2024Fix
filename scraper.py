#Source: https://github.com/antiboredom/flickr-scrape/tree/master
#Author: antibordeom
#Edited to explain what everything does and to simplify it
#Also I added the request parameters to ask for relevant images since originally the script did not do this
# and so this script used to recieve very irrelevant images
#the relevant parameter implementation is based off of this script from this:
#https://github.com/adrianmrit/flickrdatasets
#author of above script: Adrian Martinez

from __future__ import print_function #this is for older python interpreters that did not use print as a function but rather as a keyword. It forces these older interpeters to use print as a function (like we do in python3). This is only needed if you're running something older than python3
import time #standard python library to deal with time (duh)
import sys #std py library lets you access or change system related things like user input, arguments passed to command, etc.
import json #standard python library lets you parse json into a python dict
import re #standard py library to perform regExp which lets you search through a string
import os #lets you perform operating related tasks like deleting files
import requests #used to perform http requests with python very common library although not standard
from tqdm import tqdm #3rd party library used to make pretty loading bars (I like this one)
from bs4 import BeautifulSoup #popular 3rd party library used for html & XML webscraping

with open('credentials.json') as infile: #opens the credentials.json file and loads it to get a py Dict of the api key and api secret for the flickr api
    creds = json.load(infile)

KEY = creds['KEY'] #this stores the flickr api key
SECRET = creds['SECRET'] #this stores the flickr api secret

def download_file(url, local_filename):
    if local_filename is None:
        local_filename = url.split('/')[-1] #split url by backslashes and get the index at the very end (which would be the filename part of the url)
    r = requests.get(url, stream=True) #stream=true stops the request from downloading the image url immediately and instead saves it so that it can be saved using r.iter_content and processed gradually like a 'stream' down below (this way is better for downloading large files like images)
    #with is used to automatically close the opened file below
    with open(local_filename, 'wb') as f: #'wb' writes to the file and does it in binary since if 'b' is not specified then python tries to encode the data as text but that is wrong since we are downloading an image
        for chunk in r.iter_content(chunk_size=1024): #used to iterate through the file image requested and gradually write it all to memory of the file referred to as local_filename
            #chunk size of 1024 is equal to one Kibibyte since chunk size is measured in bytes
            if chunk: #check if chunk exists?
                f.write(chunk) #writes that chunk to memory
    return local_filename #just a return nothing special


def get_group_id_from_url(url):
    #the params below are used to send a json request to the flickr api to get the groupId from the url. This will be used to get all the photos that have that same group id
    params = {
        'method' : 'flickr.urls.lookupGroup',
        'url': url,
        'format': 'json',
        'api_key': KEY,
        'format': 'json',
        'nojsoncallback': 1
    }
    results = requests.get('https://api.flickr.com/services/rest', params=params).json()
    return results['group']['id']


def get_photos(qs, qg, page=1, original=False, bbox=None):
    
    #pass some parameters for the json rquest to the flickr rest api
    #old param is commented out
    '''
    params = {
        'content_type': '7',
        'per_page': '500',
        'media': 'photos',
        'format': 'json',
        'advanced': 1,
        'nojsoncallback': 1,
        'extras': 'media,license,realname,%s,o_dims,geo,tags,machine_tags,date_taken' % ('url_o' if original else 'url_l'), #url_c,url_l,url_m,url_n,url_q,url_s,url_sq,url_t,url_z',
        'page': page,
        'api_key': KEY
    }
    '''
    params = {
        'sort': 'relevance',
        'privacy_filter': 1,
        'per_page': '50',
        'format': 'json',
        'advanced': 1,
        'nojsoncallback': 1,
        'extras': 'media,license,realname,url_o, url_k, url_h, url_l, url_c,o_dims,tags,machine_tags', #url_c,url_l,url_m,url_n,url_q,url_s,url_sq,url_t,url_z',
        'page': page,
        'api_key': KEY
    }

    #these if statements use the different method to either search by term or by group
    if qs is not None:
        params['method'] = 'flickr.photos.search',
        params['text'] = qs
    elif qg is not None:
        params['method'] = 'flickr.groups.pools.getPhotos',
        params['group_id'] = qg

    # bbox should be: minimum_longitude, minimum_latitude, maximum_longitude, maximum_latitude
    if bbox is not None and len(bbox) == 4:
        params['bbox'] = ','.join(bbox)

    results = requests.get('https://api.flickr.com/services/rest', params=params).json() #send the rest api request to flickr api. The .json() gets the json data from the request and also converts it into a python dict
    if "photos" not in results: #if "photos" is not in the dict provided by the api then return None and since something went wrong
        print(results)
        return None
    return results["photos"]


def search(qs, qg, bbox=None, original=False, max_pages=None, start_page=1, output_dir='images', max_images=None):
    # create a folder for the query if it does not exist
    #looks for every non-word character in the third parameter and replaces it with _ so it can name the created folder something like image/geese or images/geese_gray if output_dir = 'images'
    foldername = os.path.join(output_dir, re.sub(r'[\W]', '_', qs if qs is not None else "group_%s"%qg))
    if bbox is not None:
        foldername += '_'.join(bbox) #adds the bounding box coords and separates each word added with a _ when adding it

    if not os.path.exists(foldername):
        os.makedirs(foldername) #if a folder with that name doesnt exist then make that folder

    jsonfilename = os.path.join(foldername, 'results' + str(start_page) + '.json') #creates the filename for the json file that'll save the dictionaries for each photo. Also includes the folderpath with it so its like folder/json_name

    if not os.path.exists(jsonfilename):

        # save results as a json file
        photos = []
        current_page = start_page

        results = get_photos(qs, qg, page=current_page, original=original, bbox=bbox)
        if results is None:
            return

        total_pages = results['pages']
        if max_pages is not None and total_pages > start_page + max_pages:
            total_pages = start_page + max_pages

        photos += results['photo']

        while current_page < total_pages:
            print('downloading metadata, page {} of {}'.format(current_page, total_pages))
            current_page += 1
            photos += get_photos(qs, qg, page=current_page, original=original, bbox=bbox)['photo']
            time.sleep(0.5) #sleep half a second each iteration not sure why this is here though

        with open(jsonfilename, 'w') as outfile:
            json.dump(photos, outfile) #saves photos dictionary as json objects to json file created earlier

    else:
        with open(jsonfilename, 'r') as infile:
            photos = json.load(infile) #if json file already exists then read the json in it and output it as a dictionary

    # download images2
    print('Downloading images')
    #loop through every photo dictionary saved in the json file we created earlier and get the value of the url_o/url_l property on it so we can get the url link of the image which we can pass to download_file to download the image
    counter = 0
    for photo in tqdm(photos):
        try:
            url = photo.get('url_o' if original else 'url_l')
            extension = url.split('.')[-1] #get the extension for that image file we are downloading EX: domain/name.jpg -> .jpg
            localname = os.path.join(foldername, '{}.{}'.format(photo['id'], extension)) #make name for the photo we will download and also include folder name so like folder/image_name
            if not os.path.exists(localname): #check if there isn't already an image with that name already there
                download_file(url, localname) #localname is the name we'll give to the downloaded image
                counter+=1
                if counter >= max_images: break; print('downloaded {} images'.format(counter));
        except Exception as e:
            continue


if __name__ == '__main__': #this is used to make sure the below only runs when executing this python file as a script and not as an import
    import argparse #standard py library for parsing arguments passed to a python script in terminal
    #all the parser stuff basically adds flags that can be used to add arguments to the script when called in the terminal
    parser = argparse.ArgumentParser(description='Download images from flickr. Note: one page is ~50 images so you should specify the max-pages flag to 1 or expect some crashing. Also in the download folder it leaves a json file of the urls of the images downloaded.')
    parser.add_argument('--search', '-s', dest='q_search', default=None, required=False, help='Search term')
    parser.add_argument('--group', '-g', dest='q_group', default=None, required=False, help='Group url, e.g. https://www.flickr.com/groups/scenery/')
    parser.add_argument('--original', '-o', dest='original', action='store_true', default=False, required=False, help='Download original sized photos if True, large (1024px) otherwise')
    parser.add_argument('--output_dir', '-t', dest='output_dir', default='images', required=False, help='Root directory to download to')
    parser.add_argument('--max-pages', '-m', dest='max_pages', required=False, help='Max pages (default none)')
    parser.add_argument('--start-page', '-st', dest='start_page', required=False, default=1, help='Start page (default 1)')
    parser.add_argument('--bbox', '-b', dest='bbox', required=False, help='Bounding box to search in, separated by spaces like so: minimum_longitude minimum_latitude maximum_longitude maximum_latitude')
    parser.add_argument('--max-images', '-i', dest='max_images', required=False, help='Max images (default None)')
    args = parser.parse_args()

    qs = args.q_search
    qg = args.q_group
    original = args.original
    output_dir = args.output_dir

    if qs is None and qg is None:
        sys.exit('Must specify a search term or group id') #if no query search or query group is provided then exit

    try:
        bbox = args.bbox.split(' ') #tries to split up the bbox arguments by spaces and makes bounding box do nothing if fails
    except Exception as e:
        bbox = None

    if bbox and len(bbox) != 4:
        bbox = None #if bounding box is not four arguments then make bounding box not do anything

    if qg is not None:
        qg = get_group_id_from_url(qg) #used to scrape images based on a url to a certain flickr group

    #the below changes print depending on if searching by group or by search term, uses format and passes gs or "group {qg}" depending on if qs != None is true
    print('Searching for {}'.format(qs if qs is not None else "group %s"%qg))
    if bbox:
        print('Within', bbox) #check if bbox is given and is not just equal to None

    max_pages = None
    if args.max_pages:
        max_pages = int(args.max_pages) #set max_pages to the argument passed and format the argument as an integer

    if args.start_page:
        start_page = int(args.start_page) #set start_page to the argument passed and format the argument as an integer
        
    max_images = None
    if args.max_images:
        max_images = int(args.max_images) #set max_images to the argument passed and format the argument as an integer


    search(qs, qg, bbox, original, max_pages, start_page, output_dir, max_images)

