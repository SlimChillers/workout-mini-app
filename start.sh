#!/bin/bash
# Start workout mini app server + Cloudflare tunnel on boot
# URL is logged to /tmp/tunnel-workout.log

nohup python3 -m http.server 8921 -d /opt/data/workout-mini-app > /tmp/workout-server.log 2>&1 &
sleep 2
nohup /opt/data/profiles/coding-premium/home/bin/cloudflared tunnel --url http://localhost:8921 --no-autoupdate > /tmp/tunnel-workout.log 2>&1 &
