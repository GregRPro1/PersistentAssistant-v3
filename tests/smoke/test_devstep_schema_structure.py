import os, yaml
REQUIRED = {'id','title','status','touches'}
def test_dev_step_min_fields():
    p=os.path.join('dev_steps','PA-201','dev_step.yaml')
    assert os.path.exists(p)
    y=yaml.safe_load(open(p,encoding='utf-8'))
    assert not (REQUIRED - set(y.keys()))
    assert isinstance(y['touches'], list) and y['touches']
def test_manifest_min_shape():
    p=os.path.join('dev_steps','PA-201','manifest.yaml')
    y=yaml.safe_load(open(p,encoding='utf-8'))
    for k in ('id','step_branch','latest'): assert k in y
