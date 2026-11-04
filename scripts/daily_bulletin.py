"""Run two independent free research jobs and publish a unified daily JSON/JS feed."""
import json
from pathlib import Path
from daily_free import main as article_main
from daily_yargitay import main as case_main

ROOT=Path(__file__).resolve().parents[1]
for label,fn in [('Makale',article_main),('Yargıtay',case_main)]:
 try:fn()
 except Exception as error:
  # Do not replace existing items if an upstream feed fails.
  print(label+' kaynağı çalışmadı: '+str(error))
records=json.loads((ROOT/'gunluk-kararlar.json').read_text('utf-8'))
(ROOT/'gunluk-kararlar.js').write_text('window.LEX_AUTO_CONTENT='+json.dumps(records,ensure_ascii=False)+';\n',encoding='utf-8')
print('Günlük havuzdaki kayıt sayısı:',len(records))
