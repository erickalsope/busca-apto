#!/bin/sh
# Uso: scripts/conv_ingest.sh arquivo.json nome conversor(zap|iw) AAAA-MM-DD
set -e
python3 - "$1" "$2" <<'PY'
import json,sys
d=json.load(open(sys.argv[1],encoding='utf-8'))
open(f'raw/{sys.argv[2]}.txt','w',encoding='utf-8').write('\n'.join(d['lines'])+'\n')
PY
CONVERT_ONLY=1 python3 scripts/process_$3.py raw/$2.txt $4 100000 >/dev/null
python3 - "$1" "$2" <<'PY'
import json,sys
d=json.load(open(sys.argv[1],encoding='utf-8'))
d['lines']=[l for l in open(f'raw/{sys.argv[2]}.txt.conv',encoding='utf-8').read().split('\n') if l]
json.dump(d,open(f'/tmp/{sys.argv[2]}_conv.json','w',encoding='utf-8'),ensure_ascii=False)
PY
python3 scripts/ingest.py /tmp/$2_conv.json $2 $4 100000 | grep -v '^descartes'
