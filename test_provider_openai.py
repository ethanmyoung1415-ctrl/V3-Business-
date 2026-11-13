import json
import unittest
from types import SimpleNamespace
from provider_openai import build_provider,enabled

class FakeResponses:
    def __init__(self):
        self.calls=[]
        self.reply=SimpleNamespace(status="completed",
            output_text=json.dumps({"explanation":"Check changed stock.",
                "verification_step":"Compare with supplier inventory evidence."}))
    def create(self,**kwargs):
        self.calls.append(kwargs)
        return self.reply

class ProviderBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.api=FakeResponses()
        self.created=[]
        def factory(**kwargs):
            self.created.append(kwargs)
            return SimpleNamespace(responses=self.api)
        self.factory=factory
        self.env={"V3_LOCAL_DEV":"1","V3_ENABLE_AI_ADVICE":"1",
                  "V3_SYNTHETIC_DATA_ONLY":"1","OPENAI_API_KEY":"synthetic-only-key",
                  "V3_AI_MODEL":"test-model"}
        self.request={"system_policy":"Read-only synthetic advice.",
                      "input":{"sku":"A","field":"stock","previous":"5","proposed":"0"},
                      "response_schema":{"explanation":"string","verification_step":"string"}}
    def test_gates_fail_without_explicit_flags(self):
        for missing in ("V3_LOCAL_DEV","V3_ENABLE_AI_ADVICE","V3_SYNTHETIC_DATA_ONLY"):
            env=dict(self.env);env.pop(missing)
            with self.subTest(missing=missing):
                with self.assertRaises(RuntimeError):
                    build_provider(environ=env,client_factory=self.factory)
        self.assertEqual(self.created,[])
    def test_inert_without_credentials(self):
        env=dict(self.env);env.pop("OPENAI_API_KEY")
        with self.assertRaises(RuntimeError):
            build_provider(environ=env,client_factory=self.factory)
    def test_structured_responses_api_call_has_no_tools_and_no_persistence(self):
        fn=build_provider(environ=self.env,client_factory=self.factory)
        advice=fn(self.request)
        self.assertEqual(advice["explanation"],"Check changed stock.")
        call=self.api.calls[0]
        self.assertFalse(call["store"])
        self.assertEqual(call["tools"],[])
        self.assertEqual(call["text"]["format"]["type"],"json_schema")
        self.assertNotIn("OPENAI_API_KEY",json.dumps(call))
        self.assertEqual(call["model"],"test-model")
        self.assertEqual(self.created[0]["timeout"],15.0)
    def test_incomplete_output_rejected(self):
        self.api.reply=SimpleNamespace(status="incomplete",output_text="")
        fn=build_provider(environ=self.env,client_factory=self.factory)
        with self.assertRaises(RuntimeError):
            fn(self.request)
    def test_unknown_extra_input_shape_rejected(self):
        fn=build_provider(environ=self.env,client_factory=self.factory)
        with self.assertRaises(ValueError):
            fn({"system_policy":"x","input":{},"response_schema":{},"tools":["shell"]})
if __name__=="__main__":unittest.main()
