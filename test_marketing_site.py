"""Static marketing page is honest and does not collect customer data."""
from html.parser import HTMLParser
from pathlib import Path
import unittest

class TagCollector(HTMLParser):
    def __init__(self):
        super().__init__();self.tags=[];self.attrs=[]
    def handle_starttag(self,tag,attrs):
        self.tags.append(tag)
        self.attrs.extend((tag,name,value) for name,value in attrs)

class MarketingPageTests(unittest.TestCase):
    def test_prelaunch_page_does_not_collect_data(self):
        page=Path(__file__).parent/"site"/"index.html"
        contents=page.read_text(encoding="utf-8")
        parser=TagCollector();parser.feed(contents)
        self.assertNotIn("script",parser.tags)
        self.assertNotIn("form",parser.tags)
        self.assertNotIn("iframe",parser.tags)
        self.assertTrue("not currently accepting subscriptions" in contents.lower())
        for tag,name,value in parser.attrs:
            if name in ("src","action"):
                self.assertFalse((value or "").startswith(("http:","https:")))
    def test_page_has_accessible_structure(self):
        contents=(Path(__file__).parent/"site"/"index.html").read_text()
        parser=TagCollector();parser.feed(contents)
        self.assertIn("main",parser.tags)
        self.assertIn("h1",parser.tags)
        self.assertIn("title",parser.tags)
if __name__=="__main__":unittest.main()
