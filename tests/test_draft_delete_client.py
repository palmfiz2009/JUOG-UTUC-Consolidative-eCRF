"""Offline contract checks: deletion passes reporter e-mail from Streamlit.

No running server, real study credentials, or patient data.
"""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return ast.parse((ROOT/path).read_text(encoding="utf-8"), filename=path)


class DraftDeleteClientTests(unittest.TestCase):
    def test_wrapper_sends_reporter_email(self):
        tree=module("juog_common.py")
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="delete_crf_draft")
        calls=[]
        def mock_registry(action,payload,timeout=30):
            calls.append((action,payload,timeout))
            return {"ok":True}
        ns={"registry_call":mock_registry,"str":str}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),filename="juog_common.py",mode="exec"),ns)
        result=ns["delete_crf_draft"](
            " juog-999 ","perioperative_30d","30d"," OWNER@EXAMPLE.INVALID ",timeout=17
        )
        self.assertTrue(result["ok"])
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][0],"delete_draft")
        self.assertEqual(calls[0][1]["registration_id"],"JUOG-999")
        self.assertEqual(calls[0][1]["reporter_email"],"OWNER@EXAMPLE.INVALID")
        self.assertEqual(calls[0][2],17)

    def test_30d_90d_followup_each_pass_reporter_email(self):
        for path in ("02_perioperative_30d_crf.py","03_day90_crf.py","04_followup_crf.py"):
            with self.subTest(path=path):
                tree=module(path)
                calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)
                       and isinstance(n.func,ast.Name) and n.func.id=="delete_crf_draft"]
                self.assertEqual(len(calls),1)
                self.assertGreaterEqual(len(calls[0].args),4)
                self.assertIsInstance(calls[0].args[3],ast.Name)
                self.assertEqual(calls[0].args[3].id,"reporter_email")

    def test_wrapper_email_required_no_silent_legacy_call(self):
        tree=module("juog_common.py")
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="delete_crf_draft")
        args=fn.args
        self.assertEqual([a.arg for a in args.args][:4],
            ["registration_id","crf_type","visit","reporter_email"])
        self.assertEqual(len(args.defaults),1)  # timeout alone defaults, e-mail required


    def test_pre_mdt_wrapper_sends_owner_email(self):
        tree=module("juog_common.py")
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
                and n.name=="delete_screening_draft")
        calls=[]
        def mock_registry(action,payload,timeout=30):
            calls.append((action,payload,timeout))
            return {"ok":True}
        ns={"registry_call":mock_registry,"str":str}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),"juog_common.py","exec"),ns)
        result=ns["delete_screening_draft"](" F11 "," LOCAL-999 ","owner@example.invalid",timeout=9)
        self.assertTrue(result["ok"])
        self.assertEqual(calls[0][0],"delete_screening_draft")
        self.assertEqual(calls[0][1]["facility_code"],"F11")
        self.assertEqual(calls[0][1]["local_subject_code"],"LOCAL-999")
        self.assertEqual(calls[0][1]["reporter_email"],"owner@example.invalid")
        self.assertEqual(calls[0][2],9)

    def test_pre_mdt_form_passes_owner_email_to_delete(self):
        calls=[n for n in ast.walk(module("01_registration_crf.py"))
               if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
               and n.func.id=="delete_screening_draft"]
        self.assertEqual(len(calls),1)
        self.assertEqual(len(calls[0].args),3)
        self.assertIsInstance(calls[0].args[2],ast.Name)
        self.assertEqual(calls[0].args[2].id,"reporter_email")


if __name__=="__main__":
    unittest.main()
