#!/bin/bash

DOMAIN="mybankapp"

echo "═══════════════════════════════════════"
echo "🌟 جاري التشغيل..."
echo "═══════════════════════════════════════"

python app.py &
sleep 3

echo ""
echo "🌍 الرابط العام الثابت:"
ssh -R ${DOMAIN}:80:localhost:5000 nokey@localhost.run

kill %1 2>/dev/null
