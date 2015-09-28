## Copyright (c) 2015 Emil Atanasov.  All rights reserved.
from webfetcher import WebFetcher

def test():
    url = "http://www.yield-media.com/anzeigen/payon/cl/20152987.html"
    # url = "http://challengecard.eu"

    index_path = "./dl"
    web_fetcher = WebFetcher(url, index_path)
    web_fetcher.fetch()
    print web_fetcher.logger

test()
