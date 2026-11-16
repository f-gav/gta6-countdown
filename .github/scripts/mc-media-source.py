import re, json, collections, pathlib, urllib.request, urllib.parse, urllib.error, time, csv

# Exact visual forms approved by the user. No Cyrillic б, no latin b.
CYR="авезикмнорстух"
LAT="aBe3uKMHoPCTyX"
MAP=dict(zip(CYR,LAT))
re_valid=re.compile(r"^[авезикмнорстух]{3,16}$")
bad_names={"список","персонаж","персонажи","аниме","манга","видеоигра","комикс","комиксы","история","мистер","мисс","мистер","капитан","принц","принцесса","король","королева","серия","глава","фильм","сезон","сериал","профессор","доктор","место","мир","вселенная","человек"}
OUT=pathlib.Path("out");OUT.mkdir(exist_ok=True)
sources=collections.defaultdict(list)
def read_json(url,timeout=100,headers=None):
    h={"User-Agent":"MinecraftRussianNameAudit/2.0 (public structured character labels)","Accept":"application/json"}
    if headers:h.update(headers)
    with urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=timeout) as f:return json.load(f)
def candidates_from(label,ref):
    raw=re.sub(r"\([^)]*\)"," ",label)
    raw=re.sub(r"«[^»]*»"," ",raw)
    raw=raw.replace("ё","е").replace("Ё","Е")
    raw=re.sub(r"\bIII?\b"," ",raw)
    tokens=re.findall(r"[А-Яа-яЁё]+",raw)
    if len(tokens)>5:return
    for token in tokens:
        w=token.lower()
        if len(w)<3 or w in bad_names:continue
        if re_valid.fullmatch(w):
            yield w,"".join(MAP[c] for c in w),ref
# Fixed media-name examples from the user's stated direction. Only well-known established spellings.
named={
"Наруто":"Наруто",
"Саске":"Наруто",
"Сакура":"Наруто",
"Хината":"Наруто",
"Курама":"Наруто",
"Коноха":"Наруто",
"Ино":"Наруто",
"Темари":"Наруто",
"Конан":"Наруто",
"Кисаме":"Наруто",
"Хаку":"Наруто",
"Карин":"Наруто",
"Сасори":"Наруто",
"Какузу":"Наруто",
"Конохамару":"Наруто",
"Сумире":"Наруто",
"Каваки":"Наруто",
"Химавари":"Наруто",
"Нами":"One Piece",
"Зоро":"One Piece",
"Кума":"One Piece",
"Михок":"One Piece",
"Виви":"One Piece",
"Смокер":"One Piece",
"Тони":"One Piece",
"Микаса":"Атака титанов",
"Армин":"Атака титанов",
"Конни":"Атака титанов",
"Марко":"Атака титанов",
"Зик":"Атака титанов",
"Имир":"Атака титанов",
"Незуко":"Клинок, рассекающий демонов",
"Канао":"Клинок, рассекающий демонов",
"Иноске":"Клинок, рассекающий демонов",
"Санеми":"Клинок, рассекающий демонов",
"Сатору":"Магическая битва",
"Маки":"Магическая битва",
"Нанами":"Магическая битва",
"Сукуна":"Магическая битва",
"Махито":"Магическая битва",
"Мива":"Магическая битва",
"Момо":"Магическая битва",
"Норитоси":"Магическая битва",
"Хакари":"Магическая битва",
"Касимо":"Магическая битва",
"Кирара":"Магическая битва",
"Макима":"Человек-бензопила",
"Резе":"Человек-бензопила",
"Аки":"Человек-бензопила",
"Химено":"Человек-бензопила",
"Аса":"Человек-бензопила",
"Миса":"Тетрадь смерти",
"Миками":"Тетрадь смерти",
"Ниа":"Тетрадь смерти",
"Теру":"Тетрадь смерти",
"Кира":"Тетрадь смерти",
"Мона":"Genshin Impact",
"Венти":"Genshin Impact",
"Кокоми":"Genshin Impact",
"Тома":"Genshin Impact",
"Мика":"Genshin Impact",
"Мико":"Genshin Impact",
"Сара":"Genshin Impact",
"Итто":"Genshin Impact",
"Кавех":"Genshin Impact",
"Мавуика":"Genshin Impact",
"Ахерон":"Honkai: Star Rail",
"Химеко":"Honkai: Star Rail",
"Искорка":"Honkai: Star Rail",
"Иви":"Покемон",
"Оникс":"Покемон",
"Арсеус":"Покемон",
"Суикун":"Покемон",
"Ротом":"Покемон",
"Какауна":"Покемон",
"Зороарк":"Покемон",
"Зоруа":"Покемон",
"Вапореон":"Покемон",
"Марио":"Mario",
"Варио":"Mario",
"Тор":"Marvel",
"Танос":"Marvel",
"Веном":"Marvel",
"Скаар":"Marvel",
"Соник":"Sonic",
"Вектор":"Sonic",
"Стив":"Minecraft",
"Мистик":"Marvel",
"Мантис":"Marvel",
"Суртур":"Marvel",
"Нова":"Marvel",
"Орочимару":"Наруто",
}
for name,series in named.items():sources["curated:"+series].append((name,name))
print("CURATED_SEEDS|"+str(sum(map(len,sources.values()))),flush=True)

q='SELECT ?item ?label WHERE { ?item wdt:P31/wdt:P279* wd:Q95074; rdfs:label ?label. FILTER(LANG(?label)="ru") } LIMIT 10000 OFFSET {}'
for offset in (0,10000,20000):
    url="https://query.wikidata.org/sparql?"+urllib.parse.urlencode({"query":q.format(offset),"format":"json"})
    try:
        data=read_json(url,timeout=115)
        rows=data["results"]["bindings"]
        for entry in rows:
            label=entry["label"]["value"]
            ref=entry["item"]["value"]
            sources["wikidata"].append((label,ref))
        print("WIKIDATA|"+str(offset)+"|"+str(len(rows)),flush=True)
        if len(rows)<10000:break
    except Exception as e:
        print("WIKIDATA_FAILED|"+str(offset)+"|"+type(e).__name__+"|"+str(e)[:120],flush=True)
        if offset==0:continue
        break
for key,title in [
    ("anime","Категория:Персонажи аниме и манги"),
    ("naruto","Категория:Персонажи «Наруто»"),
]:
    try:
        req_url="https://ru.wikipedia.org/w/api.php?"+urllib.parse.urlencode({
          "action":"query","list":"categorymembers","cmtitle":title,"cmlimit":"500","format":"json"})
        data=read_json(req_url,timeout=45)
        for row in data["query"]["categorymembers"]:
            if row["ns"]==0:sources["wikipedia:"+key].append((row["title"],"https://ru.wikipedia.org/wiki/"+urllib.parse.quote(row["title"].replace(" ","_"))))
        print("WIKIPEDIA|"+key+"|"+str(len(sources["wikipedia:"+key])),flush=True)
    except Exception as e:
        print("WIKIPEDIA_FAILED|"+key+"|"+str(e)[:120],flush=True)
        
entries={}
for source,rows in sources.items():
    for label,ref in rows:
        for word,nick,ref in candidates_from(label,ref):
            key=nick.casefold()
            if key not in entries:
                entries[key]={"name":nick,"word":word,"source":source,"label":label,"ref":ref}
# Explicit examples from prior user requests first in UI
assert entries.get("hapyto") is not None
print("MEDIA_CANDIDATES|"+str(len(entries))+"|WIKIDATA_LABELS|"+str(len(sources["wikidata"])),flush=True)
print("MEDIA_SAMPLE|"+json.dumps(list(entries.values())[:40],ensure_ascii=False),flush=True)
# Check Minecraft name on public profile endpoint.
api="https://api.minecraftservices.com/minecraft/profile/lookup/bulk/byname"
def check_batch(batch):
    for attempt in range(8):
        try:
            req=urllib.request.Request(api,json.dumps(batch).encode(),headers={"Content-Type":"application/json","Accept":"application/json","User-Agent":"MinecraftNameFinder/2.0"},method="POST")
            with urllib.request.urlopen(req,timeout=25) as response:res=json.load(response)
            if not isinstance(res,list):raise ValueError("nonlist")
            return {x["name"].casefold() for x in res}
        except urllib.error.HTTPError as e:
            try:ra=float(e.headers.get("Retry-After",0))
            except:ra=0
            delay=min(max(2+attempt*2,ra),35)
            print("RETRY|"+str(e.code)+"|"+str(attempt)+"|"+str(delay),flush=True)
        except Exception as e:
            delay=min(3+attempt*2,35)
            print("RETRY_OTHER|"+str(e)[:100],flush=True)
        time.sleep(delay)
    return None
assert {"notch","jeb_"}<=check_batch(["Notch","jeb_"]),"controls unavailable"
oldpath=OUT/"nominative_verified_nicks.txt"
oldnames=[x.strip() for x in oldpath.read_text(encoding="utf8").splitlines() if x.strip()] if oldpath.exists() else []
print("PRIOR_NOUNS|"+str(len(oldnames)),flush=True)
allnames=list({n.casefold():n for n in [*oldnames,*[x["name"] for x in entries.values()]]}.values())
print("CHECK_INPUT|"+str(len(allnames)),flush=True)
found=set();failed=set();checked=0
for i in range(0,len(allnames),10):
    chunk=allnames[i:i+10]
    taken=check_batch(chunk)
    if taken is None:failed.update(x.casefold() for x in chunk)
    else:found.update(taken);checked+=len(chunk)
    if (i//10)%35==0:
        print("PROGRESS|"+str(i)+"|taken="+str(len(found))+"|failed="+str(len(failed)),flush=True)
    time.sleep(0.13)
available=lambda nick: nick.casefold() not in failed and nick.casefold() not in found
new=[v for v in entries.values() if available(v["name"]) and v["name"].casefold() not in {n.casefold() for n in oldnames}]
old=[n for n in oldnames if available(n)]
new.sort(key=lambda e:(0 if e["source"].startswith("curated:") else 1, len(e["name"]),e["word"]))
all_verified=old+[v["name"] for v in new]
assert len(all_verified)==len({n.casefold() for n in all_verified})
print("FINAL|checked="+str(checked)+"|failed="+str(len(failed))+"|old="+str(len(old))+"|new="+str(len(new))+"|total="+str(len(all_verified)),flush=True)
with (OUT/"expanded_media_new.tsv").open("w",encoding="utf8",newline="") as file:
    writer=csv.writer(file,delimiter="\t")
    writer.writerow(["Ник","Русское имя","Источник","Исходное имя","Ссылка"])
    for x in new:writer.writerow([x["name"],x["word"],x["source"],x["label"],x["ref"]])
(OUT/"expanded_media_new.txt").write_text("\n".join(x["name"] for x in new)+"\n",encoding="utf8")
(OUT/"expanded_media_all.txt").write_text("\n".join(all_verified)+"\n",encoding="utf8")
(OUT/"expanded_media_report.json").write_text(json.dumps({"prior_candidates":len(oldnames),"prior_still_no_profile":len(old),"new_media_no_profile":len(new),"total_unique_no_profile":len(all_verified),"checked":checked,"failed":len(failed),"source_labels":{k:len(v) for k,v in sources.items()},"availability":"NO_PROFILE only, not guaranteed AVAILABLE"},ensure_ascii=False,indent=2)+"\n",encoding="utf8")
print("NEW_SAMPLES|"+json.dumps(new[:160],ensure_ascii=False),flush=True)
print("SUCCESS",flush=True)
