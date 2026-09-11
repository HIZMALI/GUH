"""One QoS1 test message, or durable receipt check. No secret output."""
import argparse
import json
import os
import time
import paho.mqtt.client as mqtt
from sqlalchemy import create_engine, text
from load_test import frame

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--message-id',required=True)
parser.add_argument('--check-db',action='store_true')
args=parser.parse_args()
if args.check_db:
    engine=create_engine(os.environ['DATABASE_URL'],pool_pre_ping=True)
    with engine.connect() as db:
        print(db.execute(text('SELECT count(*) FROM telemetry WHERE message_id=:message'),{'message':args.message_id}).scalar_one())
    engine.dispose()
else:
    payload=frame(100,args.message_id,0)
    client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='probe-'+args.message_id)
    client.username_pw_set(os.environ['MQTT_USERNAME'],os.environ['MQTT_PASSWORD'])
    client.connect(os.environ.get('MQTT_HOST','mqtt'),int(os.environ.get('MQTT_PORT','1883')),30)
    client.loop_start()
    info=client.publish('gridsentinel/telemetry/EDGE-100',json.dumps(payload),qos=1)
    info.wait_for_publish(timeout=10)
    if not info.is_published(): raise SystemExit('MQTT broker did not acknowledge probe')
    client.disconnect(); client.loop_stop()
    print('Published synthetic probe:',args.message_id)
