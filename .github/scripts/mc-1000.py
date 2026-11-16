import re, json, csv, time, collections, urllib.request, urllib.error, pathlib, sys, random
from wordfreq import top_n_list
import pymorphy3

# Only requested visual equivalents: no Cyrillic Б/б; Russian З/з -> ASCII digit 3.
CYR = "авезикмнорстух"
LAT = ["a","B","e","3","u","K","M","H","o","P","C","T","y","X"]
MAP = dict(zip(CYR,LAT))
PAT = re.compile("["+CYR+"]{3,16}\\Z")
TARGET = 5000
EXTRA = 120
MAX_BATCHES = 2200
OUT = pathlib.Path("out")
OUT.mkdir(exist_ok=True)
morph = pymorphy3.MorphAnalyzer()
pool = collections.defaultdict(list)
seen = set()
POS = {"NOUN","ADJF","ADJS","VERB","INFN","ADVB","PRTF","PRTS","GRND","COMP","PRED"}
BAD_TAGS = ("Name","Surn","Patr","Geox","Abbr")
priorities = {"NOUN":1,"ADJF":3,"INFN":4,"ADVB":5,"VERB":6,"ADJS":7,"PRTF":8,"PRTS":9,"GRND":10,"COMP":11,"PRED":12}

def add(word, rank, parsed=None, source="freq"):
    if word in seen or not PAT.fullmatch(word): return
    parses = parsed if parsed is not None else morph.parse(word)
    good = next((p for p in parses if p.is_known and p.tag.POS in POS and not any(t in str(p.tag) for t in BAD_TAGS)),None)
    if not good: return
    name = "".join(MAP[c] for c in word)
    if not 3 <= len(name) <= 16:return
    seen.add(word)
    pos = good.tag.POS
    lemma = good.normal_form == word
    prio = priorities[pos] + (0 if lemma else 2)
    if lemma and pos == "NOUN": prio = 0
    pool[word[0]].append((word,name,rank,prio,int(lemma),pos,source))

lexeme_sources = []
for rank, word in enumerate(top_n_list("ru",420000)):
    if not PAT.fullmatch(word): continue
    parses=morph.parse(word)
    add(word, rank, parses)
    if rank < 320000:
        lemma = next((p for p in parses if p.is_known and p.tag.POS in {"NOUN","ADJF","INFN"}
                      and p.normal_form==word and not any(t in str(p.tag) for t in BAD_TAGS)),None)
        if lemma:
            lexeme_sources.append((word,rank,lemma))
print("FREQUENCY_CANDIDATES|"+str(sum(map(len,pool.values()))),flush=True)

# Dictionary-backed grammatical forms of verified Russian lemmas.
for word,rank,parsed in lexeme_sources:
    for form in parsed.lexeme:
        candidate=form.word
        if PAT.fullmatch(candidate):
            add(candidate,rank+1500000,[form],source="lexeme")
print("ALL_CANDIDATES|"+str(sum(map(len,pool.values()))),flush=True)
print("INITIAL_POOLS|"+json.dumps({k:len(pool[k]) for k in CYR},ensure_ascii=False),flush=True)
for k in CYR:
    pool[k].sort(key=lambda x:(x[3],x[2],len(x[0]),x[0]))
# Fair round-robin candidate order by original Russian initial.
queues={k:collections.deque(v) for k,v in pool.items()}
order=[]
while True:
    moved=False
    for letter in CYR:
        if queues[letter]:
            order.append((letter,*queues[letter].popleft()))
            moved=True
    if not moved:break
print("QUERY_CANDIDATES|"+str(len(order)),flush=True)

api="https://api.minecraftservices.com/minecraft/profile/lookup/bulk/byname"
active=set()
checks=0
failure=[]
good=collections.defaultdict(list)
control=["Notch","jeb_"]
def lookup(chunk):
    for attempt in range(8):
        try:
            req=urllib.request.Request(api,json.dumps(chunk).encode("utf-8"),headers={
                "Content-Type":"application/json","Accept":"application/json",
                "User-Agent":"Minecraft-Russian-Nick-Audit/2.0"},method="POST")
            with urllib.request.urlopen(req,timeout=25) as res:
                profiles=json.load(res)
            if not isinstance(profiles,list):raise RuntimeError("unexpected Mojang response")
            return {p["name"].casefold() for p in profiles}
        except urllib.error.HTTPError as e:
            if e.code==429:
                try: ra = float(e.headers.get("Retry-After","2"))
                except: ra=2.0
                delay=min(max(ra,3+attempt*2.5),32)
                print("RATE_LIMIT|"+str(attempt)+"|"+str(delay),flush=True)
            else:
                delay=2+attempt*2
                print("HTTP_ERR|"+str(e.code)+"|"+str(attempt),flush=True)
            time.sleep(delay)
        except Exception as e:
            print("NETWORK_ERR|"+type(e).__name__+"|"+str(e)[:60],flush=True)
            time.sleep(2+attempt*2)
    return None

ctrl=lookup(control)
assert ctrl is not None and {"notch","jeb_"}<=ctrl,"positive controls failed"
print("CONTROLS_OK|"+str(len(ctrl)),flush=True)

for i in range(0,len(order),10):
    if i//10>=MAX_BATCHES: break
    chunk=order[i:i+10]
    found=lookup([x[2] for x in chunk])
    checks += len(chunk)
    if found is None:
        failure.extend([x[2] for x in chunk])
    else:
        for x in chunk:
            letter,word,name,rank,prio,lemma,pos,source=x
            if name.casefold() in found:active.add(name.casefold())
            else: good[letter].append((word,name,rank,prio,lemma,pos,source))
    if (i//10)%45==0:
        print("PROGRESS|checked="+str(checks)+"|no_profile="+str(sum(map(len,good.values())))+"|used="+str(len(active))+"|failed="+str(len(failure)),flush=True)
    if sum(map(len,good.values()))>=TARGET+EXTRA:break
    time.sleep(0.16)
print("RESULT|checked="+str(checks)+"|no_profile="+str(sum(map(len,good.values())))+"|taken="+str(len(active))+"|failed="+str(len(failure)),flush=True)
print("NO_PROFILE_BY_INITIAL|"+json.dumps({k:len(good[k]) for k in CYR},ensure_ascii=False),flush=True)
assert sum(map(len,good.values()))>=TARGET,"Fewer than 5000 confirmed no-profile names"

# Balance names by Cyrillic starting letter, while rare initials may have fewer words.
selected=[]
while len(selected)<TARGET:
    moved=False
    for letter in CYR:
        if good[letter]:
            info=good[letter].pop(0)
            selected.append((letter,*info))
            moved=True
            if len(selected)>=TARGET:break
    if not moved:break
assert len(selected)==TARGET
assert len({x[2].casefold() for x in selected})==TARGET
assert all("b" not in x[2] for x in selected)
assert all(all(c in "aBe3uKMHoPCTyX" for c in x[2]) for x in selected)
summary = {
    "checked":checks,"no_profile":sum(map(len,good.values()))+len(selected),
    "registered_profiles_found":len(active),"failed_checks":len(failure),
    "selected":len(selected),"selected_initials":dict(collections.Counter(x[0] for x in selected)),
    "candidate_counts":{k:len(pool[k]) for k in CYR},
    "claim":"NO_PROFILE (not guaranteed AVAILABLE)","source":"official public Minecraft Services profile lookup",
}
(OUT/"nicknames_5000.txt").write_text("\n".join(x[2] for x in selected)+"\n",encoding="utf-8")
with (OUT/"nicknames_5000.csv").open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.writer(f); w.writerow(["Никнейм","Русское слово/словоформа","Первая буква","Часть речи","Начальная форма","Статус API"])
    for x in selected:
        letter,word,name,rank,prio,lemma,pos,source=x
        w.writerow([name,word,letter,pos,"да" if lemma else "нет","NO_PROFILE"])
(OUT/"report_5000.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

# A machine-filtered starting point for manually selecting neutral, short, readable nicknames.
avoid=("террор","нарк","нац","полит","дебил","смерт","расизм","секс","болезн",
       "боль","убий","суиц","фаш","военн","кримин","гитлер")
fav=[x for x in selected if x[5]==1 and x[6]=="NOUN" and 4<=len(x[2])<=11
      and not any(a in x[1] for a in avoid)]
fav.sort(key=lambda x:(abs(len(x[2])-7),x[3]//25000,x[1]))
with (OUT/"neutral_candidates.csv").open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.writer(f);w.writerow(["Никнейм","Русское слово","Первая буква","Частотный ранг"])
    for x in fav[:300]:w.writerow([x[2],x[1],x[0],x[3]])
print("FINAL_SELECTED|"+str(len(selected)),flush=True)
print("FINAL_INITIALS|"+json.dumps(summary["selected_initials"],ensure_ascii=False),flush=True)
print("FAVORITES_POOL|"+str(len(fav)),flush=True)
print("END_OK",flush=True)
