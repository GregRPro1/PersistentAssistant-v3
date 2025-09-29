# server/jobs_api.py
import os, json, threading, queue, time, subprocess, uuid
from pathlib import Path
from flask import Blueprint, request, jsonify, Response

bp = Blueprint('jobs_api', __name__)
mount_path = '/api/jobs'

_q = queue.Queue()
_jobs = {}
_lock = threading.Lock()

def _repo_root()->Path:
    p = Path(__file__).resolve()
    for _ in range(12):
        if (p/'.git').exists(): return p
        if p.parent==p: break
        p = p.parent
    return Path.cwd()

def _jobs_dir()->Path:
    d = _repo_root()/'reports'/'ops'/'jobs'
    d.mkdir(parents=True, exist_ok=True)
    return d

class Job:
    def __init__(self, kind:str, args:dict):
        self.id = time.strftime("%Y%m%d_%H%M%S") + '_' + uuid.uuid4().hex[:6]
        self.kind = kind
        self.args = args
        self.status = 'queued'
        self.returncode = None
        self.started = None
        self.ended = None
        self.log_path = _jobs_dir()/f'{self.id}.log'
        self.meta_path = _jobs_dir()/f'{self.id}.json'
    def meta(self):
        return {
            'id': self.id, 'kind': self.kind, 'args': self.args,
            'status': self.status, 'returncode': self.returncode,
            'started': self.started, 'ended': self.ended,
            'log': str(self.log_path).replace('\\','/'),
        }
    def save(self):
        self.meta_path.write_text(json.dumps(self.meta(), indent=2), encoding='utf-8')

def _runner():
    while True:
        job = _q.get()
        if job is None: break
        job.status = 'running'; job.started = int(time.time()); job.save()
        env = os.environ.copy()
        tok = (job.args.get('gh_token') or '').strip()
        if tok: env['GITHUB_TOKEN'] = tok
        dummy = os.environ.get('PA_JOB_DUMMY','').strip()
        if dummy:
            cmd = ['python','-c','print("dummy ok");import time;time.sleep(0.2)']
        else:
            root = _repo_root()
            py_fetcher = root/'tools'/'py'/'pack'/'pack_fetcher.py'
            ps1 = root/'tools'/'ps1'/'run_pack_fetcher.ps1'
            direct = (job.args.get('direct_url') or '').strip()
            if direct and py_fetcher.exists():
                cmd = ['python', str(py_fetcher), '--once', '--direct', direct]
            elif py_fetcher.exists():
                repo = job.args.get('repo','').strip()
                rel = job.args.get('release','').strip()
                asset = job.args.get('asset_glob','PA_OUTPUT_*.zip').strip()
                cmd = ['python', str(py_fetcher), '--once', '--repo', repo, '--release', rel, '--asset', asset]
            else:
                cmd = ['pwsh', str(ps1), '-Once']
        try:
            with job.log_path.open('w', encoding='utf-8', errors='ignore') as log:
                log.write('CMD: ' + ' '.join(cmd) + '\n'); log.flush()
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, cwd=str(_repo_root()))
                for line in p.stdout: log.write(line)
                p.wait()
                job.returncode = p.returncode
                job.status = 'success' if p.returncode==0 else 'failed'
        except Exception as e:
            with job.log_path.open('a', encoding='utf-8', errors='ignore') as log:
                log.write(f'EXCEPTION: {e}\n')
            job.status = 'error'; job.returncode = -1
        finally:
            job.ended = int(time.time()); job.save()
        _q.task_done()

import threading as _t; _thr = _t.Thread(target=_runner, daemon=True); _thr.start()

def _submit(kind:str, args:dict):
    j = Job(kind, args)
    with _lock: _jobs[j.id] = j
    j.save(); _q.put(j); return j

@bp.post('/apply')
def jobs_apply():
    data = request.get_json(silent=True) or request.form or {}
    j = _submit('apply', {
        'repo': data.get('repo',''),
        'release': data.get('release',''),
        'asset_glob': data.get('asset_glob','PA_OUTPUT_*.zip'),
        'direct_url': data.get('direct_url',''),
        'gh_token': data.get('gh_token',''),
    })
    return jsonify({'id': j.id, 'status': j.status})

@bp.get('/<jid>')
def jobs_status(jid):
    p = _jobs.get(jid)
    if not p:
        meta = _jobs_dir()/f'{jid}.json'
        if meta.exists():
            return Response(meta.read_text(encoding='utf-8'), mimetype='application/json')
        return jsonify({'error':'not_found'}), 404
    return jsonify(p.meta())

@bp.get('/<jid>/tail')
def jobs_tail(jid):
    try: n = int(request.args.get('n', 400))
    except Exception: n = 400
    lp = _jobs_dir()/f'{jid}.log'
    if not lp.exists(): return Response('log not found', status=404, mimetype='text/plain')
    lines = lp.read_text(encoding='utf-8', errors='ignore').splitlines()
    return Response('\n'.join(lines[-n:]), mimetype='text/plain')
