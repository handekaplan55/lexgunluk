"""Free daily selection of open-access Turkish legal articles via DergiPark OAI-PMH.
Metadata-only discovery: never fabricates Yargitay decisions or legal conclusions.
"""
from __future__ import annotations
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'gunluk-kararlar.json'
URL = 'https://dergipark.org.tr/api/public/oai/'
NS = {'oai':'http://www.openarchives.org/OAI/2.0/', 'dc':'http://purl.org/dc/elements/1.1/'}
LEGAL = ['hukuk','yargıtay','içtihat','mahkeme','tüketici','işçi','işveren','kıdem','fesih','icra','tazminat','sözleşme','borçlar','ticaret','sigorta','kişisel veri','kvkk','hukuki','hakem heyeti','bilirkişi','anayasa mahkemesi','dava','temerrüt']
IMPORTANT = ['yargıtay','içtihat','tüketici','fesih','tanık','icra','bilirkişi','tazminat','temerrüt','ticari','sigorta']

def get_xml(params):
    url=URL+'?'+urllib.parse.urlencode(params)
    req=urllib.request.Request(url, headers={'User-Agent':'LexGunluk/1.0 (noncommercial open-access metadata reader; one daily run)'})
    with urllib.request.urlopen(req,timeout=25) as f:
        if f.status != 200: raise RuntimeError('DergiPark HTTP '+str(f.status))
        data=f.read(2500000)
    tree=ET.fromstring(data)
    error=tree.find('oai:error',NS)
    if error is not None: raise RuntimeError('DergiPark OAI: '+(error.text or 'hata'))
    return tree

def vals(record,tag):
    return [re.sub(r'\s+',' ',''.join(x.itertext())).strip() for x in record.findall('.//dc:'+tag,NS) if ''.join(x.itertext()).strip()]

def topic(text):
    t=text.casefold()
    if any(v in t for v in ['işçi','işveren','kıdem','fesih','iş hukuku','tanık']):return 'İş Hukuku'
    if 'tüketici' in t:return 'Tüketici Hukuku'
    if any(v in t for v in ['icra','iflas','haciz','temerrüt']):return 'İcra ve İflas Hukuku'
    if any(v in t for v in ['bilirkişi','mahkeme','yargılama','usul']):return 'Usul Hukuku'
    if any(v in t for v in ['ticaret','şirket','ticari']):return 'Ticaret Hukuku'
    if any(v in t for v in ['kişisel veri','kvkk','bilişim']):return 'Bilişim ve KVKK'
    if 'sigorta' in t:return 'Sigorta Hukuku'
    return 'Borçlar Hukuku'

def candidates(since):
    params={'verb':'ListRecords','metadataPrefix':'oai_dc','from':since.isoformat()}
    found=[]
    for _ in range(12):
        tree=get_xml(params)
        for rec in tree.findall('.//oai:record',NS):
            titles=vals(rec,'title');descs=vals(rec,'description');subjects=vals(rec,'subject');ids=vals(rec,'identifier')
            if not titles or not ids:continue
            title=titles[0];hay=(title+' '+' '.join(subjects)).casefold()
            if not any(w in hay for w in LEGAL):continue
            links=[x for x in ids if x.startswith('https://dergipark.org.tr/') or x.startswith('http://dergipark.org.tr/')]
            if not links:continue
            link=next((x for x in links if '/pub/' in x and '/article/' in x),links[0])
            u=urllib.parse.urlsplit(link)
            if u.hostname!='dergipark.org.tr' or u.scheme not in ('https','http'):continue
            identifier=rec.find('oai:header/oai:identifier',NS)
            oid=identifier.text.strip() if identifier is not None and identifier.text else link
            desc=re.sub(r'<[^>]+>',' ',html.unescape(descs[0] if descs else ''))
            desc=re.sub(r'\s+',' ',desc).strip()
            score=sum(3 for k in IMPORTANT if k in title.casefold())+sum(1 for k in LEGAL if k in hay)
            dates=vals(rec,'date');pub=next((x[:10] for x in dates if re.match(r'^\d{4}-\d{2}-\d{2}',x)),since.isoformat())
            found.append({'id':'dp-'+re.sub(r'[^a-zA-Z0-9]+','-',oid).strip('-')[-100:], 'kind':'Makale', 'category':topic(hay), 'title':title[:240], 'author':', '.join(vals(rec,'creator')[:3]) or 'Yazar bilgisi belirtilmemiş', 'published':pub,'publisher':'DergiPark (OAI-PMH açık erişim üstverisi)', 'url':link.replace('http://','https://',1), 'summary':(desc[:1200] if desc else 'Açık erişimli makalenin konusu başlık ve üstveri üzerinden belirlenmiştir. Özeti okumak için kaynak sayfasına bakın.'), 'why':'Bu çalışma, başlığındaki hukuki mesele bakımından araştırma başlangıcı olabilir. İçerik ve dayanaklar kaynak üzerinden kontrol edilmelidir.', 'usage':'Bu bir akademik makaledir, Yargıtay kararı değildir. Dilekçede atıf yapmadan önce makalenin tamamını, dayandığı kararları ve görüşleri inceleyin.','tags':subjects[:5], 'verified_source':False, 'metadata_source':True, '_score':score})
        token=tree.find('.//oai:resumptionToken',NS)
        if token is None or not token.text or not token.text.strip():break
        params={'verb':'ListRecords','resumptionToken':token.text.strip()}
    return sorted(found,key=lambda x:x['_score'],reverse=True)

def main():
    now=datetime.now(ZoneInfo('Europe/Istanbul'))
    day=now.date().isoformat()
    existing=json.loads(OUT.read_text('utf-8')) if OUT.exists() else []
    if any(x.get('daily_date')==day for x in existing):print('Bugün zaten yayımlandı');return
    try: pool=candidates(now.date()-timedelta(days=30))
    except Exception as e:
        print('Kaynak erişilemedi, yeni içerik oluşturulmadı: '+str(e),file=sys.stderr)
        return
    ids={r['id'] for r in existing}
    selected=next((x for x in pool if x['id'] not in ids),None)
    if selected is None:
        print('Yeni ve uygun makale bulunamadı, eski içerik tekrar eklenmedi')
        return
    selected.pop('_score',None)
    selected.update({'daily_date':day,'checked_at':now.isoformat()})
    existing.insert(0,selected)
    OUT.write_text(json.dumps(existing,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (ROOT/'gunluk-kararlar.js').write_text('window.LEX_AUTO_CONTENT='+json.dumps(existing,ensure_ascii=False)+';\n',encoding='utf-8')
    print('Yeni makale eklendi: '+selected['title'])

if __name__=='__main__':main()
