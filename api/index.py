#!/usr/bin/env python
from flask import (
    Flask,
    render_template,
    request
)

from bs4 import BeautifulSoup
import requests
import random

app = Flask(__name__)

class Film:
    def __init__(self, name, url):
        self.name = name
        self.url = url

class Page():
    def __init__(self, url, num):
        self.url = url
        self.num = num
        self.page = None
        self.soup = None
        self.ready = False
    def Load(self):
        self.page = requests.get(self.url)
        self.soup = BeautifulSoup(self.page.text,'html.parser')
        self.ready = True

@app.route("/")
@app.route("/home")
def home(): 
    return render_template('home.html')

def getPosters(pageObject) -> list: # get posters from page
    if pageObject.ready is False: 
        pageObject.Load() # load page if not loaded

    filmList = []
    posterContainer = pageObject.soup.find(class_='poster-list') # read posters
    # posterContainer: <ul class="js-list-entries poster-list -p125 -grid film-list">
    if posterContainer: # <img alt="John Wick: Chapter 4" class="image">
        posterImgs = posterContainer.find_all('img')
        posterDivs = posterContainer.find_all('div')

        for filmNo in range(len(posterImgs)):
            name = posterImgs[filmNo].attrs['alt']
            name.encode('utf-8') # encode name to utf-8
            url = posterDivs[filmNo].attrs['data-target-link']
            filmList.append(Film(name, url))

    return filmList

def chooseRandomItemNo(items): 
    return random.randint(0,len(items)-1)

def getListLastPageNo(listObject): # get last page number from dom
    pageCount = 1
    try:
        # try li tag
        pageDiscoveryList = listObject.soup.find_all('li', class_='paginate-page')
        pageCount = int(pageDiscoveryList[len(pageDiscoveryList)-1].a.get_text())
    except IndexError:
        # try meta tag
        metaDescription = listObject.soup.find('meta', attrs={'name':'description'}).attrs['content']
        filmCounts = int(metaDescription[metaDescription.find('A list of')+9:
                                         metaDescription.find('films')].strip().replace(',',''))
        if filmCounts < 101:
            pageCount = 1
        if filmCounts > 100:
            pageCount = int(pageCount/100) + (0 if pageCount % 100 == 0 else 1)
    return pageCount

@app.route("/handle_data", methods=['POST', 'GET'])
def handle_data():
    if request.method == 'POST':
        userFormUrls = []

        for key, val in request.form.items():
            if key.startswith("url"): # url1: https://letterboxd.com/
                if val: 
                    if val not in userFormUrls:
                        userFormUrls.append(val)
                    else:
                        print(f"Duplicate url: {key} -> {val}")
                else:
                    print(f"Empty url: {key} -> {val}")

        exampleUrl = 'https://letterboxd.com/username/list/list-name/'
        exampleUrlMsg = f'Example list url: {exampleUrl}'
        context = {'info_msg': exampleUrlMsg,}

        if not userFormUrls: # is at least one url provided
            context |= {'warn_msg': 'An url list is required.',}

            return render_template('home.html', **context)
           
        else: # does the url belong to letterboxd.com
            for listUrl in userFormUrls:
                if not listUrl.startswith('https://letterboxd.com/'):
                    err_msg = f'The url is not letterboxd.com: {listUrl}'
                    context |= {'err_msg': err_msg}
                    return render_template('home.html', **context)
                else:
                    if "list" not in listUrl:
                        err_msg = f'The url is letterboxd.com but not a list url: {listUrl}'
                        context |= {'err_msg': err_msg}
                        return render_template('home.html', **context)
            else: # all urls are valid
                pass

        listUrl = userFormUrls[chooseRandomItemNo(userFormUrls)]
        firstPage = Page(listUrl, 1)
        firstPage.Load()

        # site maintenance check
        if firstPage.soup.find('body', class_='error'): 
            site_msg = firstPage.soup.find('section', class_='message').p.get_text()
            context = {'err_msg': site_msg}
            return render_template('home.html', **context)

        listLastPage = getListLastPageNo(firstPage) # get last page from first page
        listPages =  []
        pageListLen = len(listPages)

        for current_page_no in range(1 + pageListLen, listLastPage + 1):
            current_page_url = f'{listUrl}/page/{str(current_page_no)}/' # create page url
            current_page = Page(current_page_url, current_page_no) # create page object
            listPages.append(current_page) # add page object to list

        randomlySelectedListPageNo = chooseRandomItemNo(listPages) # randomly selected list number from all pages
        randomlySelectedPage = listPages[randomlySelectedListPageNo] # randomly selected page object
        movieList = []
        movieList = getPosters(randomlySelectedPage) # get posters from randomly selected page

        randomlySelectedListMovieNo = chooseRandomItemNo(movieList)
        movie = movieList[randomlySelectedListMovieNo]
        movieName, movieUrl = movie.name, 'https://letterboxd.com' + movie.url

        print(f'[{listUrl}] -> [{randomlySelectedListPageNo}][{randomlySelectedListMovieNo}]: {movieName}')

        page_plural = 'page' if listLastPage == 1 else 'pages'
        # ordinal number of movie in list
        movie_ordinal = f'{randomlySelectedListMovieNo+1}th' if randomlySelectedListMovieNo else 'first'
        # ordinal number of page in list
        link_text =     f'{randomlySelectedListPageNo+1}th page.' if randomlySelectedListPageNo else 'the first page.'
        movie_info = f'In the list of {listLastPage} {page_plural}, we selected the {movie_ordinal} movie from '

        context = {
            'link': movieUrl,
            'name': movieName,
            'movie_info': movie_info,
            'list_page_url': randomlySelectedPage.url,
            'link_text': link_text}
        
    else:
        context = {'err_msg': 'The request method is not POST.'}

    return render_template('home.html', **context)

if __name__ == '__main__': # if script is run directly
    app.run(debug=True) # run app in debug mode