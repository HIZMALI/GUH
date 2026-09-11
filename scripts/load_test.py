"""Measure real HTTP and MQTT ingestion against the running local PostgreSQL stack.

Run while the background simulator is stopped. Uses generated frames; persists them
under a unique run prefix and confirms DB commits, not just MQTT PUBACK.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import platform
import statistics
import time
import uuid
import httpx
import paho.mqtt.client as mqtt
from sqlalchemy import create_engine, text

ROOT=Path(__file__).resolve().parents[1]


def stats(values):
    if not values: return {'count':0}
    values=[float(value) for value in values]
    ordered=sorted(values)
    return {'count':len(values),'mean':round(statistics.mean(values),3),'p50':round(ordered[math.ceil(len(values)*.5)-1],3),'p95':round(ordered[math.ceil(len(values)*.95)-1],3),'max':round(max(values),3)}


def frame(number, message_id, round_index):
    device=f'EDGE-{number:03d}'
    measurements={'current_l1':300+round_index*.2,'current_l2':296+round_index*.1,'current_l3':302+round_index*.15,'current_neutral':8,'voltage_l1':231,'voltage_l2':230,'voltage_l3':232,'active_power_kw':199,'reactive_power_kvar':49,'apparent_power_kva':205,'power_factor':.97,'frequency_hz':50,'thd_current':4.2,'thd_voltage':1.4,'temperature_c':36+round_index*.3,'ambient_temperature_c':25,'humidity_pct':46,'pd_pulse_count':12+round_index,'pd_peak':.8,'pd_rms':.12,'pd_activity_rate':1,'pd_baseline_ratio':1,'battery_pct':97}
    # Every tenth panel has an unmistakably synthetic arc event in the last round.
    arc_event=round_index==3 and number%10==0
    stamp=datetime.now(timezone.utc).isoformat()
    return {'message_id':message_id,'device_id':device,'panel_id':f'PNL-{number:03d}','timestamp':stamp,'source':'generated_synthetic','scenario':'arc_event' if arc_event else 'normal_operation','measurements':measurements,'quality':{k:'good' for k in measurements},'provenance':{k:'generated_synthetic' for k in measurements},'device_key':hmac.new(os.environ['DEVICE_TOKEN'].encode(),device.encode(),hashlib.sha256).hexdigest(),'arc':{'event':arc_event,'detectors':['X1:1'] if arc_event else [],'trip_relays':['K4'] if arc_event else [],'timestamp':stamp if arc_event else None,'system_state':int(arc_event),'active_errors':[],'communication_ok':True},'communication_ok':True,'simulation_step':round_index}


def run_case(client, db, devices, rounds, transport):
    prefix=f'load-{uuid.uuid4().hex}'
    mqtt_client=None
    if transport=='mqtt':
        mqtt_client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id=prefix)
        mqtt_client.username_pw_set(os.environ['MQTT_USERNAME'],os.environ['MQTT_PASSWORD'])
        mqtt_client.connect(os.getenv('MQTT_HOST','mqtt'),int(os.getenv('MQTT_PORT','1883')),60)
        mqtt_client.loop_start()
    errors=[]
    request_ms=[]
    before=client.get('/api/metrics').json()
    start=time.perf_counter()
    def send(number, r):
        payload=frame(number,f'{prefix}-{number}-{r}',r)
        t=time.perf_counter()
        try:
            if mqtt_client:
                info=mqtt_client.publish(f'gridsentinel/telemetry/{payload["device_id"]}',json.dumps(payload),qos=1)
                info.wait_for_publish(timeout=15)
                if not info.is_published(): raise RuntimeError('MQTT PUBACK timeout')
            else:
                response=client.post('/api/telemetry',json=payload)
                response.raise_for_status()
                body=response.json()
                if body.get('status') in ('duplicate','out_of_order','rejected'): raise RuntimeError(str(body))
            return (time.perf_counter()-t)*1000,None
        except Exception as exc:
            return (time.perf_counter()-t)*1000,str(exc)[:250]
    with ThreadPoolExecutor(max_workers=12) as executor:
        for r in range(rounds):
            for elapsed,error in executor.map(lambda n:send(n,r),range(1,devices+1)):
                request_ms.append(elapsed)
                if error: errors.append(error)
            # Ensure a periodic round is committed before next round for same panels.
            deadline=time.monotonic()+120
            expected=devices*(r+1)-len(errors)
            while True:
                with db.connect() as conn:
                    committed=conn.execute(text('SELECT count(*) FROM telemetry WHERE message_id LIKE :prefix'),{'prefix':prefix+'%'}).scalar_one()
                if committed>=expected or time.monotonic()>deadline: break
                time.sleep(.1)
            if committed<expected:
                errors.append(f'Commit timeout: {committed}/{expected}')
                break
            if r<rounds-1: time.sleep(.25)
    duration=time.perf_counter()-start
    if mqtt_client:
        mqtt_client.disconnect(); mqtt_client.loop_stop()
    with db.connect() as conn:
        latencies=conn.execute(text('SELECT EXTRACT(EPOCH FROM (received_at - timestamp))*1000 FROM telemetry WHERE message_id LIKE :prefix'),{'prefix':prefix+'%'}).scalars().all()
        db_start=time.perf_counter()
        count=conn.execute(text('SELECT count(*) FROM telemetry WHERE message_id LIKE :prefix'),{'prefix':prefix+'%'}).scalar_one()
        query_ms=(time.perf_counter()-db_start)*1000
    api=[]
    for _ in range(10):
        t=time.perf_counter(); response=client.get('/api/fleet'); response.raise_for_status(); api.append((time.perf_counter()-t)*1000)
    after=client.get('/api/metrics').json()
    return {'transport':transport,'devices':devices,'rounds':rounds,'expected':devices*rounds,'committed':count,'duration_seconds':round(duration,3),'committed_frames_per_second':round(count/duration,2),'producer_request_or_puback_ms':stats(request_ms),'source_to_ingestion_received_ms':stats(latencies),'fleet_api_ms':stats(api),'db_count_query_ms':round(query_ms,3),'metrics_before':before,'metrics_after':after,'errors':errors[:10],'passed':count==devices*rounds and not errors,'run_prefix':prefix}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--devices',default='100,250,500')
    parser.add_argument('--rounds',type=int,default=4)
    parser.add_argument('--transport',choices=['http','mqtt','both'],default='both')
    parser.add_argument('--output',default='/tmp/gridsentinel-load.json')
    args=parser.parse_args()
    client=httpx.Client(base_url=os.getenv('API_URL','http://api:8000'),headers={'Authorization':'Bearer '+os.environ['SERVICE_TOKEN']},timeout=120)
    db=create_engine(os.environ['DATABASE_URL'],pool_pre_ping=True)
    counts=[int(n) for n in args.devices.split(',')]
    login=client.post('/api/auth/login',json={'username':os.environ.get('ADMIN_USERNAME','admin'),'password':os.environ['ADMIN_PASSWORD']}); login.raise_for_status()
    admin={'Authorization':'Bearer '+login.json()['access_token']}
    provision=client.post('/api/demo/fleet',json={'count':max(counts)},headers=admin); provision.raise_for_status()
    result={'timestamp':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'python':platform.python_version(),'note':'Local Docker PostgreSQL. Simulator must be paused. Each case confirms committed telemetry by unique message IDs. Producer PUBACK does not imply durable application ingestion. Small 4-round bursts are not a sustained production capacity claim.','cases':[]}
    transports=['http','mqtt'] if args.transport=='both' else [args.transport]
    for n in counts:
        for transport in transports:
            case=run_case(client,db,n,args.rounds,transport)
            result['cases'].append(case)
            print(json.dumps({k:case[k] for k in ['transport','devices','expected','committed','committed_frames_per_second','passed','errors']}),flush=True)
            Path(args.output).write_text(json.dumps(result,indent=2),encoding='utf-8')
    client.close(); db.dispose()
    if not all(c['passed'] for c in result['cases']): raise SystemExit(1)


if __name__=='__main__': main()
