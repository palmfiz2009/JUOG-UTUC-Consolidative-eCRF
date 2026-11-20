"""Static guards: the three CRF pages must share one interaction pattern."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ("02_perioperative_30d_crf.py", "_render_peri_crf", "peri"),
    ("03_day90_crf.py", "_render_day90_crf", "d90"),
    ("04_followup_crf.py", "_render_followup_crf", "fu"),
]


class AllCrfPagesTests(unittest.TestCase):
    def test_all_three_use_local_fragments_and_same_submission_helper(self):
        for name, fn_name, page in FILES:
            with self.subTest(file=name):
                source = (ROOT / name).read_text(encoding="utf-8")
                tree = ast.parse(source)
                fragment = next(n for n in tree.body
                    if isinstance(n, ast.FunctionDef) and n.name == fn_name)
                self.assertTrue(any(isinstance(d, ast.Attribute) and d.attr == "fragment"
                                    for d in fragment.decorator_list))
                fragment_src = ast.get_source_segment(source,fragment)
                self.assertNotIn("st.rerun()", fragment_src)
                self.assertIn(f'pending_attempt("{page}", st.session_state)',fragment_src)
                self.assertIn(f'page="{page}"', fragment_src)
                self.assertIn("submit_crf_with_feedback(",fragment_src)
                self.assertIn(f'resume_panel("{page}")', fragment_src)
                self.assertIn(f'section_feedback("{page}",', fragment_src)
                self.assertNotIn("save_crf_draft(", fragment_src)

    def test_no_direct_crf_write_or_replay_generated_in_pages(self):
        for name, _, _ in FILES:
            with self.subTest(file=name):
                src=(ROOT/name).read_text(encoding="utf-8")
                self.assertNotIn("save_result = save_crf_payload(",src)
                self.assertNotIn("st.rerun()",src)
                self.assertNotIn('st.form("',src)


if __name__ == "__main__":
    unittest.main()

