import unittest
from repo_guard import validate_file

class PublicRepositorySafetyTests(unittest.TestCase):
    def test_reject_env_and_private_keys(self):
        self.assertTrue(validate_file(".env",b""))
        self.assertTrue(validate_file("credentials.json",b"{}"))
        self.assertTrue(validate_file("private.pem",b"anything"))
        self.assertTrue(validate_file("test.sqlite3",b""))
    def test_reject_token_shapes(self):
        token=b"sk-" + b"x"*40
        self.assertTrue(validate_file("settings.py",token))
        self.assertTrue(validate_file("notebook.txt",b"-----BEGIN "+b"PRIVATE KEY-----"))
        self.assertTrue(validate_file("file.json",b"github_pat_"+b"a"*40))
    def test_safe_public_test_files_pass(self):
        self.assertEqual(validate_file("README.md",b"Use OPENAI_API_KEY in environment"),[])
        self.assertEqual(validate_file("examples.csv",b"sku,title\nA,Sample\n"),[])
if __name__=="__main__":unittest.main()
