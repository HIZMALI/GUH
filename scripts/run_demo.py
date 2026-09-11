"""One-command on-premise demo. Python standard library only."""
from pathlib import Path
import argparse
import json
import subprocess
import time
import urllib.request
from bootstrap import bootstrap

ROOT = Path(__file__).resolve().parents[1]


def read_env():
    return dict(line.split('=',1) for line in (ROOT/'.env').read_text().splitlines() if line and not line.startswith('#'))


def request(path, payload=None, token=None):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']=f'Bearer {token}'
    req=urllib.request.Request('http://127.0.0.1:8000'+path,headers=headers,data=json.dumps(payload).encode() if payload is not None else None)
    with urllib.request.urlopen(req,timeout=15) as response:
        return json.load(response)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario',default='combined_thermal_pd')
    parser.add_argument('--panel',default='PNL-001')
    parser.add_argument('--no-build',action='store_true')
    parser.add_argument('--connect-only',action='store_true')
    args=parser.parse_args()
    bootstrap()
    if not args.connect_only:
        command=['docker','compose','up','-d']
        if not args.no_build: command+=['--build']
        subprocess.run(command,cwd=ROOT,check=True)
    deadline=time.monotonic()+180
    while True:
        try:
            request('/health')
            break
        except Exception:
            if time.monotonic()>deadline: raise RuntimeError('Backend health timeout. Inspect docker compose logs api.')
            time.sleep(2)
    config=read_env()
    token=request('/api/auth/login',{'username':config['ADMIN_USERNAME'],'password':config['ADMIN_PASSWORD']})['access_token']
    result=request('/api/demo/scenario',{'scenario':args.scenario,'panel_id':args.panel},token)
    print(json.dumps(result,ensure_ascii=False))
    print('Demo: http://localhost:3000 | login: ADMIN_USERNAME / ADMIN_PASSWORD in .env')
    print('All observations are synthetic; no real SCADA/field connection or external notification.')


if __name__=='__main__':
    main()
