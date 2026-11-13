"""Yargıtay'ın halka açık karar arama arayüzünden günlük seçki oluşturur.
Resmî, dokümante bir API değildir; site değişikliklerinde entegrasyon güncellenmelidir.
Alıntı üzerinden hukuki yorum / sahte özet üretmez.
"""
import json, os, re, time, random
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

BASE = 'https://karararama.yargitay.gov.tr'
PATH = Path(__file__).parent / 'data' / 'decisions.json'
TODAY = datetime.now(ZoneInfo('Europe/Istanbul')).date().isoformat()
TERMS = [('İş Hukuku','fazla çalışma'),('Tüketici','ayıplı mal'),('Borçlar','temerrüt'),('Usul','ispat yükü'),('Ticaret','ticari defter'),('İş Hukuku','işe iade'),('Tüketici','tüketici hakem heyeti'),('Usul','bilirkişi raporu'),('Borçlar','sebepsiz zenginleşme')]
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; LexGunluk/1.0; legal-reading-project)','Accept':'application/json, text/plain, */*','Content-Type':'application/json; charset=UTF-8','X-Requested-With':'XMLHttpRequest','Origin':BASE,'Referer':BASE+'/'}
s=requests.Session();s.headers.update(HEADERS)

def req(method,path,**kwargs):
    for attempt in range(3):
        r=s.request(method,BASE+path,timeout=35,**kwargs)
        if r.status_code==429 or 'Erişim Sınırı' in r.text[:400]:
            if attempt<2: time.sleep(25*(attempt+1));continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError('Yargıtay hız sınırı')

def text_of(html):
    soup=BeautifulSoup(html,'html.parser')
    for x in soup(['script','style']): x.decompose()
    return re.sub(r'\n{3,}','\n\n',soup.get_text('\n',strip=True)).strip()

def excerpt(text,keyword):
    pattern=re.compile(re.escape(keyword),re.I)
    match=pattern.search(text)
    if not match: return text[:900]
    start=max(0,match.start()-280)
    return ('…' if start else '')+text[start:min(len(text),start+950)]+('…' if len(text)>start+950 else '')

def update():
    try: store=json.loads(PATH.read_text('utf-8'))
    except (FileNotFoundError,ValueError): store={'decisions':[]}
    decisions=store.get('decisions',[])
    seen={str(x.get('id')) for x in decisions}
    chosen=[]
    s.get(BASE+'/',timeout=30)
    rotation=int(TODAY.replace('-',''))%len(TERMS)
    topics=TERMS[rotation:]+TERMS[:rotation]
    for topic,keyword in topics:
        if len(chosen)>=3: break
        try:
            payload={'data':{'aranan':keyword,'arananKelime':keyword,'pageSize':15,'pageNumber':1}}
            result=req('POST','/aramadetaylist',json=payload)
            rows=(result.get('data') or {}).get('data') or []
            # En güncel ilk sayfa; eski içerik seçilmez.
            for row in rows:
                rid=str(row.get('id') or '')
                if not rid or rid in seen: continue
                time.sleep(3.2)
                doc=req('GET','/getDokuman',params={'id':rid})
                raw=text_of((doc or {}).get('data') or '')
                if len(raw)<200: continue
                number=str(row.get('kararNo') or '')
                case=str(row.get('esasNo') or '')
                chamber=str(row.get('daire') or '')
                if not all((number,case,chamber)):continue
                chosen.append({'id':rid,'selected_date':TODAY,'title':keyword[:1].upper()+keyword[1:]+' hakkında Yargıtay kararı','topic':topic,'daire':chamber,'esas_no':case,'karar_no':number,'karar_tarihi':str(row.get('kararTarihi') or 'Tarih belirtilmemiş'),'excerpt':excerpt(raw,keyword),'url':BASE+'/?id='+rid})
                seen.add(rid)
                break
        except Exception as exc:
            print(f'Konu {keyword}: {type(exc).__name__}: {exc}',flush=True)
        time.sleep(3.2)
    if not chosen:
        # Güncelleme başarısızsa tarih güncellenmez; eski kararlar arşivde kalır.
        raise RuntimeError('Bugün doğrulanmış karar indirilemedi. Eski içerik korunuyor.')
    # Sadece günün 3 yeni kararı; arşivde daha önceki içerikler tutulur.
    store={'updated_at':TODAY,'decisions':(chosen+decisions)[:500],'error':'' if len(chosen)==3 else f'Bugün yalnızca {len(chosen)} doğrulanabilir karar getirilebildi.'}
    PATH.write_text(json.dumps(store,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(f'{TODAY}: {len(chosen)} yeni karar eklendi.',flush=True)

if __name__=='__main__':update()
