## Copyright (c) 2015 Emil Atanasov.  All rights reserved.
from __future__ import generators
from spider import Spider
import os
import uuid
import tempfile
import codecs
import re
import hashlib
from bs4 import BeautifulSoup, Comment, Tag
__name__ = 'webfetcher'
__version__ = '0.1'
__author__ = 'Emil Atanasov (heitara@gmail.com)'
# __all__ = ['ftpurls', 'ftppaths', 'weburls', 'ftpmirror', 'ftpspider',
#     'webpaths', 'webreport', 'webmirror', 'webspider', 'urlreport',
#     'badurlreport', 'badhtmreport', 'redireport', 'outreport', 'othereport']

'''Fetch a web page and save it locally. Fix all assets path, which are not in any subfolder.
All assets are fetched in a subfolder structure and all references are updated.
The saved HTML page is not 1:1 with the original, but has minor updates.'''

class WebFetcher:
    
    def __init__(self, url=None, index_path=None):
        '''Initializes a WebFetcher instance and its base attributes'''                             
        # the url which shouldbe fetched
        self._url = url
        self._base_url = self._url
        file_ext = os.path.splitext(url)[1]
        if file_ext:
            # trim the file name
            self._base_url = self._url[:self._url.rindex("/")]
        # the path where everything will be saved
        self._index_path = index_path
        self._spider = Spider()
        self._CSS_RE = re.compile(r"url\(([^\)]*)\)")

    def fetch(self):
        self._spider.webmirror(root=self._index_path,base=self._url)
        html_file = "./" + self._spider.paths[0]  
        self._ad_hash = "ad-hash-key"
        self._assets_list = []
        self._logger = []
        self._rewrite_html_with_local_files(html_file, self._ad_hash, self._url, self._logger)

    @property
    def logger(self):
        return self._logger
    
    def _convert_to_absolute_url(self, relative_url):
        absolute_url = self._base_url
        while relative_url.startswith(".."):
            relative_url = relative_url[3:] # remove ../
            index_of_dash = absolute_url.rindex("/")
            absolute_url = absolute_url[:index_of_dash]
        
        return absolute_url + "/" + relative_url
    
    def _process_assets_queue(self):
        ''' Download all assets which are listed in the list.
        '''
        # fetch all assets
        visited_urls = {}
        for item in self._assets_list:
            url = item["url"]
            if not url in  visited_urls:       
                print "Download %s to %s" % (url, item["local_file"])
                absolute_url = self._convert_to_absolute_url(url)
                print "URL: %s" % absolute_url
                self._spider._ulib.urlretrieve(absolute_url, item["local_file"])
                visited_urls[url] = 1
            # else:
            #     print url

    # TODO: fetch an asset to a local file
    def _fetch_external_resource(self, base_url, relative_url, local_file, logger=None):
        print "Download the file from  %s/%s" % (base_url, relative_url)
        if logger is not None:
            logger.append({'text': "Download external resource.", 'code': "Download the file from  %s/%s" % (base_url, relative_url)})

    # convert an ulr to absolute
    def _rewrite(self, old_url, base_url, image=True):
        if not '://' in old_url:
            if image:
                if old_url.endswith('.png') or old_url.endswith('.jpg') or old_url.endswith('.gif'):
                    return absurl + old_url
            else:
                if old_url != '#' and not old_url.startswith('mailto:'):
                    return absurl + old_url
     
        return old_url

    # TODO: go and identify all links     
    def _fetch_and_rewrite_all(self, elems, attr, base_url, image=True, logger=None):
        for elem in elems:
            # print elem
            # if attr in elem._getAttrMap():
            if attr in elem.attrs:
                old_attr = elem[attr]
                elem[attr] = self._rewrite(elem[attr], base_url, image=image)
                if logger is not None:
                    tag = "Update image url." if image else "Update link url."
                    logger.append({'text': tag, 'code': " %s -> %s" % (old_attr, elem[attr])})
    def _repl(self, m):
        url =  m.group(0)[4:-1]
        file_ext = os.path.splitext(url)[1]
        m = hashlib.md5()
        m.update(url)
        asset_local_name =  m.hexdigest() + file_ext        
        self._assets_list.append({"url" : url, "local_file": asset_local_name})

        return "url(" + asset_local_name + ")"

    def _update_css_node(self, node):
        css_new = re.sub(self._CSS_RE, self._repl , node.string);
        node.string.replaceWith(css_new)
                
    def _enqueue_external_css_resource(self, css_node):
        # get the new name of the file
        # add the css file to be fetched
        css_url = css_node["href"]
        m = hashlib.md5()
        m.update(css_url)
        css_local_name =  m.hexdigest() + ".css"
        
        self._assets_list.append({"url" : css_url, "local_file": css_local_name})
        print "The content of this CSS file should be digested and cenverted."
        
        
    def _fetch_and_rewrite_css(self, cssnodes, base_url, logger=None):
        for node in cssnodes:
                if node.string:
                    if not '://' in node.string:
                        self._update_css_node(node)
                        # node.string.replaceWith(self._CSS_RE.sub(r'url(' + base_url + r'\1)', node.string))
                        # print "CSS: %s" % node.string
                    # print "do some other css node polishing"
                    node.string = re.sub( r'\/\*[\s\S]*?\*\/', "", node.string)
                    node.string = re.sub(r'&amp;', r'&', node.string)
                    #node.string = re.sub( r'\<\!\-\-[\s\S]*?\-\-\>', "", node.string)
                else:
                    if logger is not None:
                        logger.append({'text': "The CSS is not in proper format. Please check it.", 'code': node.contents})
                    print "err:" + str(node.contents).encode('ascii')

    def _rewrite_html_with_local_files(self, index_path, ad_hash, base_url, logger=None):
        # print os.getcwd()
        os.system('mv "%s" "%s.original"' % (index_path, index_path))
        folder = index_path[:index_path.rindex('/') + 1]

        fp = codecs.open(index_path + '.original', mode='r')
        soup = fp.read()

        soup = re.sub(r'&(?!nbsp;)', r'&amp;', soup)

        soup = BeautifulSoup(soup, "html.parser")
        # add ad hash as watermark comment
        # new_comment = Comment("ad-hash: " + ad_hash)
        # soup.head.append(new_comment)

        # merge the CSS in the html file
        stylesheets = soup.findAll("link", {"rel": "stylesheet"})
        for s in stylesheets:
            if s["href"] and not s["href"].startswith("http"):
                if logger is not None:
                    tag = "Embed CSS file."
                    logger.append({'text': tag, 'code': " %s " % s["href"]})
                # handle all local css files
                c = open(folder + s["href"]).read()
                tag = Tag(soup, "style", [("type", "text/css")])
                tag.insert(0, c)
                s.replaceWith(tag)
            else:
                # internal method, which should fetch an external css file
                self._enqueue_external_css_resource(base_url, s)
                if logger is not None:
                    tag = "External CSS file, which should be fetched first. Unable to embed it."
                    logger.append({'text': tag, 'code': " %s " % s["href"]})

        self._fetch_and_rewrite_all(soup.findAll('a'), 'href', base_url, image=False, logger=logger)
        self._fetch_and_rewrite_all(soup.findAll('table'), 'background', base_url, image=True, logger=logger)
        self._fetch_and_rewrite_all(soup.findAll('td'), 'background', base_url, image=True, logger=logger)
        self._fetch_and_rewrite_all(soup.findAll('link'), 'href', base_url, image=False, logger=logger)
        self._fetch_and_rewrite_all(soup.findAll('img'), 'src', base_url, image=True, logger=logger)
    
        self._fetch_and_rewrite_css(soup.findAll('style'), base_url, logger=logger)
        
        self._process_assets_queue()
        
        # find all comments and remove those
        # comments = soup.findAll(text=lambda text:isinstance(text, Comment))
        # [comment.extract() for comment in comments]
        soup = re.sub(r'&amp;', r'&', unicode(soup))
        fp.close()
        out = codecs.open(index_path, mode='w', encoding='utf-8')
        out.write(unicode(soup))

        out.close()

