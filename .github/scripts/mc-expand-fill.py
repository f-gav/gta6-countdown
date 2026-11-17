import collections, csv, json, pathlib, re, time, urllib.request, urllib.error, sys
from wordfreq import top_n_list, zipf_frequency
import pymorphy3

OUT=pathlib.Path("out"); OUT.mkdir(exist_ok=True)
TARGET=5000
CYR="авезикмнорстух"
LAT=["A","B","E","3","u","K","M","H","O","P","C","T","y","X"]
M=dict(zip(CYR,LAT))
VALID=re.compile(r"^[авезикмнорстух]{3,16}$")
DISALLOW_ABBR={"вуз","загс","совхоз","колхоз","нарком","военком","партком","профком","сельхоз","главк","горком","райком","обком","нархоз","совмин","совнарком","спецназ","профорг","комсорг","комсомол","завхоз","завуч","рунет","интерпол","роно","санэпид"}
BAD_PREFIX=("совхоз","колхоз","райком","партком","профком","нарком","военком","горком","обком","главк","комсомол","сельхоз","спецназ","завхоз","завуч","совмин")
POS_ADJF={"ADJF","ADJS"}
MORPH=pymorphy3.MorphAnalyzer()

baseline=(OUT/"cross_media_all_2952.txt").read_text(encoding="utf8").splitlines()
assert len(baseline)==2952, len(baseline)
oldkeys={s.casefold() for s in baseline}
oldlemmas=set()
oldwords=set()
with (OUT/"nominative_verified_words.tsv").open(encoding="utf8") as f:
    for row in csv.DictReader(f,delimiter="\t"):
        oldlemmas.add(row["Первоначальная форма"].lower())
        oldwords.add(row["Русское слово"].lower())
print("OLD|"+str(len(oldkeys))+"|LEMMA|"+str(len(oldlemmas)),flush=True)

# Frequency list ranks common Russian words ahead of archaic morphology-dictionary entries.
common=top_n_list("ru",600000)
ranks={w:n for n,w in enumerate(common)}
print("FREQ|"+str(len(common)),flush=True)
source=MORPH.dictionary.words
print("DAWG|"+type(source).__name__+"|"+str(type(source).__name__),flush=True)

# Morphology parses only words with glyphs that visually match the requested Latin characters.
selected={}
processed=0
valid=0
for word in source.keys():
    if not VALID.fullmatch(word):
        continue
    valid+=1
    if word in DISALLOW_ABBR or word.startswith(BAD_PREFIX):
        continue
    parsed=MORPH.parse(word)
    for p in parsed:
        if not p.is_known or p.tag.case!="nomn":continue
        pos=p.tag.POS
        if pos not in {"NOUN","ADJF"}:continue
        grams=p.tag.grammemes
        if "Abbr" in grams or "Patr" in grams:
            continue
        kind=("Места" if "Geox" in grams else
              "Имена" if "Name" in grams or "Surn" in grams else
              "Существительные" if pos=="NOUN" else
              "Прилагательные")
        lemma=p.normal_form.lower()
        nick="".join(M[c] for c in word)
        if nick.casefold() in oldkeys or word in oldwords:
            continue
        # Shorter names, singular nouns, and standalone dictionary lemmas rank above inflected forms.
        gram_number=p.tag.number
        score=(0 if kind=="Существительные" else
               1 if kind=="Места" else
               2 if kind=="Имена" else 4)
        score+=0 if gram_number=="sing" else 1
        if lemma not in oldlemmas:
            score-=2
        if pos=="ADJF": # prefer nominative forms that look like natural independent words
            score+=1
        rank=ranks.get(word,1000000)
        token=(score,rank,len(word),word)
        entry={"word":word,"nick":nick,"kind":kind,"lemma":lemma,"rank":rank,
               "number":gram_number or "","pos":pos,"score":score}
        key=(word,kind)
        prev=selected.get(key)
        if prev is None or token < prev[0]:
            selected[key]=(token,entry)
    processed+=1
    if processed%25000==0:print("MORPH_PROGRESS|"+str(processed)+"|"+str(len(selected)),flush=True)

candidates=[x[1] for x in selected.values()]
# Unique lexical lemma preference: avoid simply producing different cases/numbers of the same word.
# First pass pick one representative per lemma and kind (prefer words with high frequency).
candidates.sort(key=lambda x:(x["rank"]>=600000, x["score"],x["rank"],abs(len(x["nick"])-7),x["word"]))
distinct=[]
duplicates=[]
used_lemmas=set(oldlemmas)
for e in candidates:
    if e["lemma"] in used_lemmas:duplicates.append(e)
    else:
        distinct.append(e)
        used_lemmas.add(e["lemma"])
# Rebalance across initial letters by score/frequency so we do not fill only one alphabet segment.
groups=collections.defaultdict(collections.deque)
for e in distinct:
    groups[e["word"][0]].append(e)
roundrobin=[]
while any(groups.values()):
    for letter in CYR:
        if groups[letter]:roundrobin.append(groups[letter].popleft())
print("DICT_VALID_FORMS|"+str(valid)+"|PARSED|"+str(processed)+"|CANDIDATE_FORMS|"+str(len(candidates))+"|UNIQUE_LEMMAS|"+str(len(distinct))+"|DUP_FORMS|"+str(len(duplicates)),flush=True)
print("CANDIDATE_GROUPS|"+json.dumps(dict(collections.Counter(x["kind"] for x in distinct)),ensure_ascii=False),flush=True)

# Continue with alternative forms only after exhausting independent lemmas.
queue=roundrobin+duplicates
seen=set()
unique_queue=[]
for x in queue:
    key=x["nick"].casefold()
    if key not in seen:
        unique_queue.append(x);seen.add(key)
print("QUERY_POOL|"+str(len(unique_queue)),flush=True)

URL="https://api.minecraftservices.com/minecraft/profile/lookup/bulk/byname"
def lookup(names):
    for i in range(8):
        try:
            req=urllib.request.Request(URL,json.dumps(names).encode(),headers={"Content-Type":"application/json","Accept":"application/json","User-Agent":"MinecraftNickotekaQualityAudit/4.0"},method="POST")
            with urllib.request.urlopen(req,timeout=25) as r: data=json.load(r)
            if not isinstance(data,list): raise ValueError("Unexpected response")
            return {x["name"].casefold() for x in data}
        except urllib.error.HTTPError as e:
            try:ra=float(e.headers.get("Retry-After","0"))
            except:ra=0
            t=min(max(3+i*2,ra),32)
            print("RETRY|"+str(e.code)+"|"+str(t),flush=True)
        except Exception as e:
            t=min(3+i*2,30)
            print("RETRY_OTHER|"+str(type(e).__name__),flush=True)
        time.sleep(t)
    return None
assert {"notch","jeb_"} <= lookup(["Notch","jeb_"])
banned=set("завсектором зверосовхоз откормсовхоз замнарком замзава завком хакасавтотранс ивановоавтотранс омскавтотранс химавтоматика".split())
file=OUT/"expanded_to_5000_additions.tsv"
with file.open(encoding="utf8") as f: prior=list(csv.DictReader(f,delimiter="\t"))
kept=[r for r in prior if r["Русское слово"] not in banned]
need=5000-len(baseline)-len(kept)
print("QUALITY_FILTER|excluded="+str(len(prior)-len(kept))+"|need="+str(need),flush=True)
assert 0<need<=50
prev_keys={x["Ник"].casefold() for x in prior}
batchpool=[e for e in unique_queue[3820:] if e["nick"].casefold() not in prev_keys]
added=[]
seen_lemmas={x["Лемма"] for x in prior}
taken=0
failed=0
for i in range(0,len(batchpool),10):
    grp=batchpool[i:i+10]
    result=lookup([x["nick"] for x in grp])
    if result is None:failed+=len(grp)
    else:
        for x in grp:
            if x["nick"].casefold() in result:taken+=1
            elif x["lemma"] not in seen_lemmas and x["word"] not in banned and len(added)<need:
                added.append(x);seen_lemmas.add(x["lemma"])
    if len(added)>=need:break
    if i%100==0:print("PROGRESS|"+str(i)+"|added="+str(len(added)),flush=True)
    time.sleep(.11)
assert len(added)==need,(len(added),need)
with file.open("w",encoding="utf8",newline="") as f:
    w=csv.DictWriter(f,fieldnames=["Ник","Русское слово","Категория","Лемма","Часть речи","Число","Словарный ранг","Проверка"],delimiter="\t")
    w.writeheader()
    for row in kept:w.writerow(row)
    for x in added:
        w.writerow({"Ник":x["nick"],"Русское слово":x["word"],"Категория":x["kind"],"Лемма":x["lemma"],"Часть речи":x["pos"],"Число":x["number"],"Словарный ранг":x["rank"],"Проверка":"NO_PROFILE"})
allnick=baseline+[x["Ник"] for x in kept]+[x["nick"] for x in added]
assert len(allnick)==5000
assert len(set(x.casefold() for x in allnick))==5000
(OUT/"expanded_to_5000_additions.txt").write_text("\n".join([x["Ник"] for x in kept]+[x["nick"] for x in added])+"\n",encoding="utf8")
(OUT/"expanded_to_5000_all.txt").write_text("\n".join(allnick)+"\n",encoding="utf8")
with (OUT/"expanded_to_5000_report.json").open("r",encoding="utf8") as f:report=json.load(f)
report["compounds_filtered"]=sorted(banned)
report["verified_replacements"]=len(added)
report["api_errors_replacements"]=failed
report["unique_additional_lemmas"]=True
(OUT/"expanded_to_5000_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
print("FILL_DONE|new="+str(len(added))+"|taken="+str(taken)+"|failed="+str(failed)+"|total="+str(len(allnick)),flush=True)
print("SUCCESS",flush=True)
