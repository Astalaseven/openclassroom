import os
import requests as req
from BeautifulSoup import BeautifulSoup

URL = 'http://fr.openclassrooms.com'


def get_sections():
    content = BeautifulSoup(req.get(URL).text)
    sections = content.findAll('li', {'class': "dropdown-menu-item "})
    
    for section in sections:
        if not 'data-name' in str(section):
            sections.remove(section)

    return sections


def get_list_courses(section):
    url = '%s%s' % (URL, section.find('a')['href'])
    content = BeautifulSoup(req.get(url).text)
    courses = []

    pages = content.findAll('div', {'class': "paginationContent"})
    nb_pages = int(pages[0].findAll('a')[-1].text) if pages else 1


    for page in xrange(1, nb_pages + 1):
        page_url = '%s?status=published&page=%s' % (url, page)
        content = BeautifulSoup(req.get(page_url).text)
        courses += content.findAll('a', {'class': "course-title course-title-2"})

    return courses


def clean_html(url, name, soup):
    to_extract = [
        ['footer', None],
        ['script', None],
        ['section', {'class': "inset no-padding"}],
        ['section', {'class': "advertise"}],
        ['section', {'id': "oc-header"}],
        ['div', {'class': "header-inner"}],
        ['div', {'class': "course-part-summary__main-icon"}],
        ['div', {'class': "course-part-summary__switch-icon"}],
        ['div', {'class': "course-header__details"}],
        ['div', {'class': "col-nav__inner"}],
        ['div', {'class': "timeline"}],
        ['aside', {'class': "course-registration"}],
        ['aside', {'class': "course-pagination  space-bottom clearfix"}],
        ['aside', {'class': "course-pagination course-pagination--single space-bottom clearfix"}],
        ['aside', {'class': "col3 col4-s col-nav col-nav--floating js-sidebar"}],
    ]
       
    for list in to_extract:
        found = soup.findAll(list[0], list[1])
        for f in found:
            f.extract()

    if not url.split('/')[-1] == name:
        header = soup.find('section', {'class': "alt-section course-header "})
        headernoicon = soup.find('section', {'class': "alt-section course-header course-header--no-icon"})
        author = soup.find('section', {'class': "alt-section"})
        if header:
            header.extract()
        if headernoicon:
            headernoicon.extract()
        if author:
            author.extract()

    return soup


def download_course(course):
    urls = get_course_urls(course)
    path = urls[0].split('/')[3]
    name = urls[0].split('/')[5]

    if not os.path.exists(path):
        os.makedirs(path)

    soup = BeautifulSoup(req.get(urls[0]).content)
    h2titles = {}
    for title in soup.findAll('li', {'class': "course-part-summary "}):
        h2titles.update(dict((u.text.encode('utf-8'), u.get('href')) for u in title.findAll('a')))

    final = ""

    for url in urls:
        content = req.get(url)

        soup = BeautifulSoup(content.text)
        content = clean_html(url, name, soup)
        content = link2anchor(content, h2titles)
        final += convert_urls(str(content))

    with open('%s/%s.html' % (path, name), 'w') as f:      
        f.write(final)

    uploads = [url.get('href') for url in soup.findAll('a') if 'uploads.siteduzero.com' in url.get('href', '')]
    uploads += [url.get('src') for url in soup.findAll('img') if 'uploads.siteduzero.com' in url.get('src', '')]
    
    download_files(uploads)


def download_files(uploads):
    for url in uploads:
        path = '/'.join(url.split('/')[3:-1])
        name = url.split('/')[-1]

        if not os.path.exists(path):
            os.makedirs(path)

        with open('%s/%s' % (path, name), 'wb') as f:
            try:
                f.write(req.get(url).content)
            except req.exceptions.ConnectionError:
                print('Error: %s' % (url))
                pass

def download_css():
    urls = BeautifulSoup(req.get(URL).text).findAll('link', {'type': "text/css"})
    for url in urls:
        name = url['href'].split('/')[-1].split('?')[0]

        if not os.path.exists('css'):
            os.mkdir('css')

        with open('css/' + name, 'w') as f:
            f.write(req.get(URL + url['href']).text.encode('utf-8'))

 
def convert_urls(html):
    to_replace = {
        r'href="/': r'href="../',
        r'sciences/cours': r'sciences',
        r'entreprise/cours': r'entreprise',
        r'informatique/cours': r'informatique',
        r'bundles/common/css': r'css',
        r'http://uploads.siteduzero.com/files/': r'../files/',
    }

    for regex in to_replace:
        html = html.replace(regex, to_replace[regex])
    
    return html

def link2anchor(soup, h2titles):
    for title in soup.findAll('li', {'class': "course-part-summary "}):
        for url in title.findAll('a'):
            if url.get('href'):
                url['href'] = '#%s' % url['href'].split('/')[-1]

    h2 = soup.find('h2', {'class': "part-title"})

    if h2titles and h2:
        h2['id'] = h2titles.get(h2.text.encode('utf-8')).split('/')[-1]

    return soup

def get_course_urls(course):
    url = '%s%s'% (URL, course['href'])
    content = BeautifulSoup(req.get(url).text)
    parts = content.findAll('ul', {'class': "course-part js-course-part"})
    urls = []
    urls.append(url)

    if parts:
        parts = parts[0].findAll('li', {'class': "course-part-summary "})
        for part in parts:
            urls += ['%s%s' % (URL, str(url['href'])) for url in part.findAll('a') if 'href=' in str(url)]

    return urls
    
if __name__ == '__main__':
    from glob import glob

    sections = get_sections()
    courses = []

    for section in sections:
        print('Getting list of courses for %s' % (section.text))
        courses += get_list_courses(section)
    print('%s tutorials found' % (len(courses)))
    download_css()

    if sections:
        paths = [glob('%s/*' % (section.find('a').text.lower())) for section in sections]
        files = [path.split('/')[-1] for path in paths[0]]

    for course in courses:
        name = course.get('href').split('/')[-1] if course.get('href') else None
        if not '%s.html' % (name) in files:
            print('Downloading %s' % (name))
            download_course(course)
