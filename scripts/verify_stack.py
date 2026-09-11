"""Actual Docker/HTTP/Modbus restart checks, with local report and restored services."""
from pathlib import Path
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import socket
import struct
import subprocess
import time
import urllib.error
import urllib.request
import uuid

ROOT=Path(__file__).resolve().parents[1]


def read_env():
    return dict(line.split('=',1) for line in (ROOT/'.env').read_text().splitlines() if line and not line.startswith('#'))


def request(path, payload=None, token=None):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    req=urllib.request.Request('http://127.0.0.1:8000'+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=20) as response: return response.status,json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code,json.load(exc)


def wait_health():
    deadline=time.monotonic()+120
    while time.monotonic()<deadline:
        try:
            if request('/health')[0]==200: return
        except Exception: pass
        time.sleep(1)
    raise RuntimeError('API health did not recover')


def compose(*args):
    return subprocess.run(['docker','compose',*args],cwd=ROOT,check=True,capture_output=True,text=True).stdout


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restarts',action='store_true',help='Includes API/DB/MQTT restart faults; services restored afterward.')
    parser.add_argument('--output',default='docs/verification/stack-results.json',help='Report path; use a new filename to preserve earlier evidence.')
    args=parser.parse_args()
    env=read_env()
    results=[]
    def check(name,fn):
        t=time.perf_counter()
        try:
            detail=fn()
            results.append({'name':name,'passed':True,'seconds':round(time.perf_counter()-t,3),'detail':detail})
            print('PASS',name,flush=True)
        except Exception as exc:
            results.append({'name':name,'passed':False,'seconds':round(time.perf_counter()-t,3),'detail':str(exc)})
            print('FAIL',name,str(exc),flush=True)
    def require(condition,message):
        if not condition: raise AssertionError(message)
    wait_health()
    status,auth=request('/api/auth/login',{'username':env['ADMIN_USERNAME'],'password':env['ADMIN_PASSWORD']})
    require(status==200,'Admin login failed')
    token=auth['access_token']
    _,viewer=request('/api/auth/login',{'username':'viewer','password':env['VIEWER_PASSWORD']})
    check('anonymous fleet rejected',lambda:require(request('/api/fleet')[0]==401,'Unauthenticated read allowed'))
    check('viewer scenario mutation rejected',lambda:require(request('/api/demo/scenario',{'scenario':'arc_event','panel_id':'PNL-001'},viewer['access_token'])[0]==403,'Viewer mutation allowed'))
    def stack_health():
        # API readiness can precede the first scheduled SCADA/web health probe.
        deadline=time.monotonic()+45
        while True:
            output=compose('ps','--format','json')
            states=json.loads(output) if output.lstrip().startswith('[') else [json.loads(l) for l in output.splitlines() if l.strip()]
            ready=len(states)>=6 and all(s['State']=='running' and
                    (s['Service'] not in {'db','mqtt','api','web','scada'} or s.get('Health')=='healthy') for s in states)
            if ready or time.monotonic()>=deadline: break
            time.sleep(1)
        require(len(states)>=6,'Missing services')
        for state in states:
            require(state['State']=='running',state['Service']+' not running')
            if state['Service'] in {'db','mqtt','api','web','scada'}: require(state.get('Health')=='healthy',state['Service']+' unhealthy')
        return [{'service':s['Service'],'health':s.get('Health'),'state':s['State']} for s in states]
    check('Docker services healthy',stack_health)
    check('fleet populated with at least100 panels',lambda:require(request('/api/fleet',token=token)[1]['summary']['total']>=100,'Insufficient fleet'))
    def scada_read():
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            code,data=request('/api/scada/registers?panel_id=PNL-001',token=token)
            if code==200 and data.get('connected'):
                require(len(data['registers'])>=12,'Incomplete Modbus register read')
                return {'connected':True,'registers':len(data['registers']),'transport':data['transport']}
            time.sleep(1)
        raise AssertionError('TCP master did not connect: '+str(data))
    check('actual Modbus TCP master roundtrip',scada_read)
    def modbus_exception(function,address,value,expected):
        pdu=struct.pack('>BHH',function,address,value)
        with socket.create_connection(('127.0.0.1',1502),3) as connection:
            connection.sendall(struct.pack('>HHHB',77,0,len(pdu)+1,1)+pdu)
            packet=b''
            while len(packet)<9:
                chunk=connection.recv(1024)
                if not chunk: break
                packet+=chunk
        require(packet[-2:]==bytes([function|0x80,expected]),f'Wrong exception {packet.hex()}')
    check('Modbus invalid register rejected',lambda:modbus_exception(3,60000,1,2))
    check('Modbus writes rejected',lambda:modbus_exception(6,0,0,1))
    check('notification records explicitly simulated',lambda:require(all(n['status']=='simulated' for n in request('/api/notifications',token=token)[1]['items']),'Misleading notification status'))
    if args.restarts:
        compose('stop','simulator')
        try:
            panel=request('/api/panels/PNL-001',token=token)[1]
            before=panel.get('last_seen')
            def restart_api():
                compose('restart','api'); wait_health()
                data=request('/api/panels/PNL-001',token=token)[1]
                require(data.get('last_seen')==before,'Persisted panel timestamp changed/lost with simulator paused')
                return {'last_seen_preserved':True}
            check('backend restart preserves durable panel data',restart_api)
            def restart_database():
                compose('stop','db')
                time.sleep(2)
                code,_=request('/health')
                require(code==503,'DB outage health must be503')
                probe='db-recovery-'+uuid.uuid4().hex
                compose('exec','-T','api','python','scripts/publish_probe.py','--message-id',probe)
                compose('start','db'); wait_health()
                recovery_read_started=time.perf_counter()
                data=request('/api/panels/PNL-001',token=token)[1]
                recovery_read_seconds=time.perf_counter()-recovery_read_started
                require(data.get('last_seen')==before,'Database persistence lost')
                require(recovery_read_seconds<8,'Recovered panel read exceeded eight-second bounded check')
                deadline=time.monotonic()+45
                persisted=0
                while time.monotonic()<deadline:
                    persisted=int(compose('exec','-T','api','python','scripts/publish_probe.py','--check-db','--message-id',probe).strip())
                    if persisted==1: break
                    time.sleep(1)
                require(persisted==1,'QoS1 message published during DB outage was not committed exactly once after recovery')
                return {'outage_health':code,'last_seen_preserved':True,'outage_message_committed_exactly_once':True,
                        'recovery_panel_read_seconds':round(recovery_read_seconds,3)}
            check('database outage and reconnect',restart_database)
            def restart_mqtt():
                compose('stop','mqtt'); time.sleep(3)
                _,health=request('/health')
                _,metrics=request('/api/metrics',token=token)
                compose('start','mqtt')
                deadline=time.monotonic()+45
                while time.monotonic()<deadline:
                    _,after=request('/api/metrics',token=token)
                    if after.get('mqtt_connected') is True: break
                    time.sleep(1)
                require(after.get('mqtt_connected') is True,'MQTT failed to reconnect')
                require(metrics.get('mqtt_connected') is False,'MQTT disconnect not visible')
                return {'disconnected_visible':True,'reconnected':True}
            check('MQTT disconnect and reconnect',restart_mqtt)
        finally:
            compose('start','db','mqtt','api','scada','simulator','web')
            wait_health()
    output=Path(args.output)
    if not output.is_absolute(): output=ROOT/output
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'timestamp':datetime.now(timezone.utc).isoformat(),'checks':results},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Report:',output.relative_to(ROOT))
    if not all(r['passed'] for r in results): raise SystemExit(1)


if __name__=='__main__': main()
