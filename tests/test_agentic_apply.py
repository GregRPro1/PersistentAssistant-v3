import pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "USER_GUIDE.md"

def test_user_guide_has_agentic_marker():
  assert GUIDE.exists()
  text = GUIDE.read_text(encoding="utf-8")
  assert re.search(r"\[plan\] placeholder for step 10\.3", text)
