import http.client
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
import operator_dashboard as ui
import operations

class HTTPConsoleTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.db=Path(temp.name)/"test.sqlite3"
        operations.setup(self.db)
        self.server=ThreadingHTTPServer(("127.0.0.1",0),
            ui.make_handler(self.db,"csrf-token","test-operator"))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
    def send(self,method,path,body=None,headers=None):
        conn=http.client.HTTPConnection("127.0.0.1",self.server.server_port,timeout=5)
        hdr={"Host":f"127.0.0.1:{self.server.server_port}"}
        hdr.update(headers or {})
        conn.request(method,path,body,headers=hdr)
        response=conn.getresponse()
        status=response.status
        payload=response.read().decode("utf-8",errors="replace")
        conn.close()
        return status,payload
    def test_local_overview(self):
        code,html=self.send("GET","/")
        self.assertEqual(code,200)
        self.assertIn("Operator attention",html)
    def test_reject_rebinding_host(self):
        code,_=self.send("GET","/",headers={"Host":"attacker.example"})
        self.assertEqual(code,403)
    def test_reject_foreign_origin(self):
        code,_=self.send("POST","/decide","csrf=csrf-token",
            {"Content-Type":"application/x-www-form-urlencoded",
             "Origin":"https://attacker.example"})
        self.assertEqual(code,403)
    def test_reject_missing_csrf(self):
        code,_=self.send("POST","/decide","job=1&change=2&decision=approved&reason=oops",
            {"Content-Type":"application/x-www-form-urlencoded"})
        self.assertEqual(code,403)
if __name__=="__main__":unittest.main()
