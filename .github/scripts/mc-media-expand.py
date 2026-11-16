import re, collections, urllib.request, urllib.parse, urllib.error, json, csv, pathlib, time

OUT=pathlib.Path("out");OUT.mkdir(exist_ok=True)
CYR="авезикмнорстух"
LAT="aBe3uKMHoPCTyX"
M=dict(zip(CYR,LAT))
VALID=re.compile(r"^[авезикмнорстух]{3,16}$")
STOP={"список","списки","персонаж","персонажи","аниме","манга","манги","сериал","серии","мультфильм","компьютер","игра","игры","комикс","комиксы","мисс","мистер","супер","серия","статья","оригинал","человек","тор","все","мистер","доктор","синопсис","списке"}
ROOTS=[
"Категория:Персонажи компьютерных игр по франшизе",
"Категория:Персонажи компьютерных игр",
"Категория:Персонажи аниме и манги",
"Категория:Персонажи мультфильмов",
"Категория:Персонажи комиксов Marvel Comics",
"Категория:Персонажи DC Comics",
"Категория:Персонажи комиксов",
"Категория:Персонажи телесериалов",
"Категория:Персонажи сериалов",
"Категория:Персонажи фильмов",
]
def load(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (MCNickGatherer/2.0)"})
    with urllib.request.urlopen(req,timeout=28) as r: return json.load(r)
def members(category):
    token=None
    for _ in range(4):
        opts={"action":"query","list":"categorymembers","cmtitle":category,"cmlimit":"500","format":"json"}
        if token:opts["cmcontinue"]=token
        url="https://ru.wikipedia.org/w/api.php?"+urllib.parse.urlencode(opts)
        try:data=load(url)
        except Exception as e:
            print("CAT_ERR|"+category+"|"+type(e).__name__+"|"+str(e)[:80],flush=True)
            return
        for x in data["query"].get("categorymembers",[]): yield x
        token=data.get("continue",{}).get("cmcontinue")
        if not token:return
queue=collections.deque((title,0) for title in ROOTS)
visited=set()
pages={}
while queue and len(visited)<180 and len(pages)<19000:
    cat,depth=queue.popleft()
    if cat in visited:continue
    visited.add(cat)
    count=0
    for row in members(cat):
        if row["ns"]==0:
            title=row["title"]
            if not any(x in title.lower() for x in ("список","персонажи","списки","категория:")):
                pages[title]=cat
                count+=1
        elif row["ns"]==14 and depth<3:
            sub=row["title"]
            if any(x in sub.lower() for x in ("списки","незавершён","годам","гендер","десятилетия","жанрам")):
                continue
            if sub not in visited:queue.append((sub,depth+1))
    if len(visited)%20==0:print("CATEGORY_PROGRESS|"+str(len(visited))+"|pages="+str(len(pages))+"|queue="+str(len(queue)),flush=True)
    time.sleep(.04)
print("CATEGORY_DONE|"+str(len(visited))+"|"+str(len(pages)),flush=True)
names={}
for title,cat in pages.items():
    raw=re.sub(r"\([^)]*\)"," ",title)
    raw=re.sub(r"«[^»]*»"," ",raw)
    for token in re.findall(r"[А-Яа-яЁё]+",raw):
        w=token.lower().replace("ё","е")
        if w in STOP or not VALID.fullmatch(w):continue
        nick="".join(M[c] for c in w)
        key=nick.casefold()
        names.setdefault(key,{"nick":nick,"word":w,"page":title,"category":cat})
# Media personalities/places and names of popular characters directly attested in their media.
seeds={
"Асока":"Звёздные войны","Реван":"Звёздные войны","Саурон":"Властелин колец",
"Саруман":"Властелин колец","Хорнет":"Hollow Knight","Ори":"Ori","Моно":"Little Nightmares",
"Сикс":"Little Nightmares","Санс":"Undertale","Темми":"Undertale","Меттатон":"Undertale",
"Крис":"Deltarune","Тео":"Celeste","Рики":"Dota 2","Свен":"Dota 2","Тинкер":"Dota 2",
"Тини":"Dota 2","Мирана":"Dota 2","Сова":"Valorant","Неон":"Valorant","Астра":"Valorant",
"Омен":"Valorant","Исо":"Valorant","Векс":"League of Legends","Ахри":"League of Legends",
"Сона":"League of Legends","Катарина":"League of Legends","Сивир":"League of Legends",
"Сорака":"League of Legends","Карма":"League of Legends","Варус":"League of Legends",
"Сетт":"League of Legends","Самира":"League of Legends","Рената":"League of Legends",
"Кеннен":"League of Legends","Тимо":"League of Legends","Зери":"League of Legends",
"Орианна":"League of Legends","Танатос":"Hades","Никс":"Hades","Арес":"Hades",
"Хаос":"Hades","Марио":"Mario","Тор":"Marvel","Танос":"Marvel","Веном":"Marvel",
"Соник":"Sonic","Вектор":"Sonic","Ротом":"Pokemon","Зоруа":"Pokemon",
"Зороарк":"Pokemon","Вапореон":"Pokemon","Мики":"Disney","Мини":"Disney",
}
for token,series in seeds.items():
    w=token.lower()
    if VALID.fullmatch(w):
        nick="".join(M[c] for c in w)
        names.setdefault(nick.casefold(),{"nick":nick,"word":w,"page":token,"category":"seed:"+series})
print("CANDIDATES|"+str(len(names)),flush=True)

oldnames=[x.strip() for x in (OUT/"expanded_media_all.txt").read_text(encoding="utf8").splitlines() if x.strip()]
oldkeys={n.casefold() for n in oldnames}
to_check=[x for k,x in names.items() if k not in oldkeys]
print("OLD|"+str(len(oldnames))+"|TO_CHECK|"+str(len(to_check)),flush=True)

API="https://api.minecraftservices.com/minecraft/profile/lookup/bulk/byname"
def query(chunk):
    for attempt in range(7):
        try:
            req=urllib.request.Request(API,json.dumps(chunk).encode(),method="POST",headers={"Content-Type":"application/json","Accept":"application/json","User-Agent":"MinecraftAudit/2.0"})
            with urllib.request.urlopen(req,timeout=25) as r:
                data=json.load(r)
            if not isinstance(data,list): raise ValueError("Unexpected API response")
            return {e["name"].casefold() for e in data}
        except urllib.error.HTTPError as e:
            try:wait=float(e.headers.get("Retry-After","0"))
            except:wait=0
            delay=min(max(wait,3+attempt*3),32)
            print("RETRY|"+str(e.code)+"|"+str(delay),flush=True)
        except Exception as e:
            delay=min(2+attempt*3,30)
            print("ERROR|"+str(type(e).__name__),flush=True)
        time.sleep(delay)
    return None
assert {"notch","jeb_"} <= query(["Notch","jeb_"]),"positive controls failed"
taken=set();failed=set()
for i in range(0,len(to_check),10):
    batch=[x["nick"] for x in to_check[i:i+10]]
    resp=query(batch)
    if resp is None: failed.update(x.casefold() for x in batch)
    else:taken.update(resp)
    if i%250==0:print("API_PROGRESS|"+str(i)+"|taken="+str(len(taken))+"|failed="+str(len(failed)),flush=True)
    time.sleep(.12)
new=[x for x in to_check if x["nick"].casefold() not in taken and x["nick"].casefold() not in failed]
new.sort(key=lambda x:(len(x["nick"]),x["word"]))
newnames=[x["nick"] for x in new]
assert len(newnames)==len(set(n.casefold() for n in newnames))
merged=oldnames+newnames
assert len(merged)==len(set(n.casefold() for n in merged))
print("DONE|new="+str(len(new))+"|taken="+str(len(taken))+"|failed="+str(len(failed))+"|combined="+str(len(merged)),flush=True)
(OUT/"expanded_media_added_round2.txt").write_text("\n".join(newnames)+"\n",encoding="utf8")
with (OUT/"expanded_media_added_round2.tsv").open("w",encoding="utf8",newline="") as f:
    writer=csv.writer(f,delimiter="\t")
    writer.writerow(["Ник","Русская форма","Страница","Категория"])
    for x in new:writer.writerow([x["nick"],x["word"],x["page"],x["category"]])
(OUT/"expanded_media_all_v2.txt").write_text("\n".join(merged)+"\n",encoding="utf8")
(OUT/"expanded_media_report_v2.json").write_text(json.dumps({
    "base_lookups_done":len(oldnames),"new_queries":len(to_check),
    "new_no_profile":len(new),"new_taken":len(taken),"failed":len(failed),
    "total_combined":len(merged),"wiki_pages":len(pages),"category_count":len(visited),
    "limitation":"Public profile absence is not guaranteed AVAILABLE"
},ensure_ascii=False,indent=2)+"\n",encoding="utf8")
print("NEW_SAMPLE|"+json.dumps(new[:100],ensure_ascii=False),flush=True)
print("SUCCESS",flush=True)
