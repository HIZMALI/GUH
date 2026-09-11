#!/bin/sh
set -eu
umask 077
if [ -f /mosquitto/data/passwords ]; then
  mosquitto_passwd -b /mosquitto/data/passwords "$MQTT_USERNAME" "$MQTT_PASSWORD"
else
  mosquitto_passwd -b -c /mosquitto/data/passwords "$MQTT_USERNAME" "$MQTT_PASSWORD"
fi
chown mosquitto:mosquitto /mosquitto/data/passwords
printf 'user %s\ntopic readwrite gridsentinel/#\n' "$MQTT_USERNAME" > /mosquitto/data/acl
chown mosquitto:mosquitto /mosquitto/data/acl
exec mosquitto -c /config/mosquitto.conf
