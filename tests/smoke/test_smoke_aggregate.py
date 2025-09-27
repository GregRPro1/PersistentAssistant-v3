from tools.py.smoke_aggregate import write_outputs
def test_write_outputs_creates_md_and_json(tmp_path):
    rows=[{'step':'PA-XXX','junit':'dev_steps/PA-XXX/results/junit_1.xml','total':1,'failures':0,'errors':0,'skips':0}]
    out = tmp_path/'reports'; write_outputs(rows, out)
    assert (out/'summary.json').exists() and (out/'summary.md').exists()
