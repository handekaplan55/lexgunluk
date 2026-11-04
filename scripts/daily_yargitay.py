"""Yargitay public site search + original decision document checks.

Unpaid/unofficial endpoint. Can stop working, block requests or change without notice.
Never creates imaginary decisions. Failures are reported; previously published items persist.
"""
from __future__ import annotations
import html, json, re, sys, time, urllib.error, urllib.parse, urllib.request
from html.parser import HTMLParser
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'gunluk-kararlar.json'
ORIGIN = 'https://karararama.yargitay.gov.tr'
QUERIES = [
 ('İş Hukuku', 'tanık beyanı'),
 ('Tüketici Hukuku', 'ayıplı hizmet'),
 ('İcra ve İflas Hukuku', 'itirazın iptali'),
 ('Usul Hukuku', 'bilirkişi raporu'),
 ('Borçlar Hukuku', 'temerrüt'),
 ('Ticaret Hukuku', 'ticari faiz'),
 ('İş Hukuku', 'işe iade'),
 ('Tüketici Hukuku', 'aracı hizmet sağlayıcı'),
]

class PlainText(HTMLParser):
 def __init__(self): super().__init__();self.chunks=[];self.ignored=0
 def handle_starttag(self, tag, attrs):
  if tag in ('script','style'): self.ignored+=1
  elif tag in ('p','br','div','li','tr'): self.chunks.append(' ')
 def handle_endtag(self,tag):
  if tag in ('script','style') and self.ignored: self.ignored-=1
  elif tag in ('p','div','li','tr'):self.chunks.append(' ')
 def handle_data(self,data):
  if not self.ignored:self.chunks.append(data)
 def result(self):return re.sub(r'\s+',' ',' '.join(self.chunks)).strip()

def request_json(path, body=None):
 headers={'User-Agent':'Mozilla/5.0 (compatible; LexGunlukResearch/1.0; personal daily research)',
 'Accept':'application/json, text/plain, */*','Referer':ORIGIN+'/',
 'Origin':ORIGIN,'X-Requested-With':'XMLHttpRequest'}
 if body is not None: headers['Content-Type']='application/json; charset=UTF-8'
 data=None if body is None else json.dumps(body,ensure_ascii=False).encode('utf-8')
 req=urllib.request.Request(ORIGIN+path,data=data,headers=headers,method='POST' if body else 'GET')
 with urllib.request.urlopen(req,timeout=28) as rsp:
  if rsp.status!=200:raise RuntimeError('Yargıtay HTTP '+str(rsp.status))
  obj=json.loads(rsp.read(3_000_000).decode('utf-8'))
  if not isinstance(obj,dict):raise RuntimeError('Beklenmeyen yanıt')
  return obj

def search(term):
 payload={'data':{'aranan':term,'arananKelime':term,'pageSize':10,'pageNumber':1}}
 response=request_json('/aramadetaylist',payload)
 data=response.get('data') or {}
 return data.get('data',[]) if isinstance(data,dict) and isinstance(data.get('data',[]),list) else []

def valid_number(v):return bool(re.fullmatch(r'(?:19|20)\d{2}\s*/\s*\d{1,8}',str(v or '').strip()))

def extract_snippet(text,term):
 # Only show a short literal excerpt, not a synthesized legal holding.
 for fragment in [term.split()[0], 'gerekçe', 'mahkemece']:
  i=text.casefold().find(fragment.casefold())
  if i>80:
   start=max(0,i-90);return ('…' if start else '')+text[start:start+410].strip()+'…'
 return text[:410].strip()+'…'

def find_decision(existing, today):
 # fixed daily rotation; only a few requests/day to respect rate limiting
 offset=(today.toordinal()%len(QUERIES))
 known={(r.get('id'), r.get('kind')) for r in existing}
 for category,term in [QUERIES[(offset+i)%len(QUERIES)] for i in range(3)]:
  try:
   rows=search(term)
  except (urllib.error.URLError,TimeoutError,ValueError,RuntimeError) as exc:
   print('Yargıtay arama erişimi: '+str(exc),file=sys.stderr)
   break
  for raw in rows[:5]:
   id_=str(raw.get('id') or '')
   esas=str(raw.get('esasNo') or '').strip()
   karar=str(raw.get('kararNo') or '').strip()
   daire=str(raw.get('daire') or '').strip()
   tarih=str(raw.get('kararTarihi') or '').strip()
   if not id_ or not valid_number(esas) or not valid_number(karar) or not daire or ('Hukuk' not in daire):continue
   if ('yg-'+id_,'Yargıtay Kararı') in known:continue
   time.sleep(3.2)  # official site rate limit
   try:
    doc=request_json('/getDokuman?id='+urllib.parse.quote(id_,safe=''))
    contents=doc.get('data')
    if not isinstance(contents,str): continue
    parser=PlainText();parser.feed(contents);text=parser.result()
    # Full text must exist and contain case number components.
    if len(text)<700:continue
    nos=[x.strip().split('/')[-1] for x in (esas,karar)]
    if not all(re.search(r'(?<!\d)'+re.escape(n)+r'(?!\d)',text) for n in nos):continue
   except (urllib.error.URLError,ValueError,RuntimeError,TimeoutError) as exc:
    print('Karar metni kontrol edilemedi: '+str(exc),file=sys.stderr);continue
   return {'id':'yg-'+id_, 'kind':'Yargıtay Kararı','category':category,
           'title':f'{daire} — E. {esas}, K. {karar}', 'daire':daire,
           'esas_no':esas,'karar_no':karar,'decision_date':tarih,
           'url':ORIGIN+'/', 'source_search':term,
           'summary':'Resmî Yargıtay kayıtlarında bulunan kararın otomatik seçilmiş metin bölümü aşağıdadır. Bu bölüm kararın özeti veya bağlayıcı hukuki sonucu değildir.',
           'excerpt':extract_snippet(text,term),
           'usage':f'“{term}” konusunda araştırma için seçildi. Dilekçede kullanmadan önce resmî sitede E. {esas} / K. {karar} ile tam metni açın; olay, gerekçe, bozma/onama sonucu ve güncel içtihatla uygunluğunu karşılaştırın.',
           'verified_source':True,'checked_document':True,'checked_at':datetime.now(ZoneInfo('Europe/Istanbul')).isoformat()}
  time.sleep(3.2)
 return None

def main():
 now=datetime.now(ZoneInfo('Europe/Istanbul'));day=now.date().isoformat()
 try: existing=json.loads(OUT.read_text('utf-8')) if OUT.exists() else []
 except (ValueError,OSError):existing=[]
 if any(x.get('daily_date')==day and x.get('kind')=='Yargıtay Kararı' for x in existing):
  print('Bugünkü Yargıtay kararı zaten seçildi');return
 selected=find_decision(existing,now.date())
 if not selected:
  print('Bugün doğrulanabilen yeni bir karar bulunamadı; uydurma karar eklenmedi')
  return
 selected['daily_date']=day;existing.insert(0,selected)
 OUT.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Karar eklendi: '+selected['title'])

if __name__=='__main__':main()
