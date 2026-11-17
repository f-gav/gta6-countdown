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
            req=urllib.request.Request(URL,json.dumps(names).encode(),headers={
                "Content-Type":"application/json","Accept":"application/json",
                "User-Agent":"MinecraftPublicNicknameProfileAudit/3.0"},method="POST")
            with urllib.request.urlopen(req,timeout=27) as r:data=json.load(r)
            if not isinstance(data,list):raise ValueError("Unexpected profile response")
            return {x["name"].casefold() for x in data}
        except urllib.error.HTTPError as exc:
            try: retry=float(exc.headers.get("Retry-After","0"))
            except:retry=0
            delay=min(max(3+i*3,retry),38)
            print("RETRY_HTTP|"+str(exc.code)+"|"+str(i)+"|"+str(delay),flush=True)
        except Exception as exc:
            delay=min(3+i*3,32)
            print("RETRY_OTHER|"+type(exc).__name__+"|"+str(exc)[:60],flush=True)
        time.sleep(delay)
    return None

assert {"notch","jeb_"}<=lookup(["Notch","jeb_"]),"controls failed"
verified=[]
taken=0
failed=[]
checked=0
target_new=TARGET-len(oldkeys)
for k in range(0,len(unique_queue),10):
    batch=unique_queue[k:k+10]
    res=lookup([e["nick"] for e in batch])
    if res is None:
        failed.extend(e["nick"] for e in batch)
    else:
        checked+=len(batch)
        for e in batch:
            if e["nick"].casefold() in res:taken+=1
            elif len(verified)<target_new: verified.append(e)
    if (k//10)%40==0:
        print("API_PROGRESS|"+str(k+len(batch))+"|new="+str(len(verified))+"|taken="+str(taken)+"|failed="+str(len(failed)),flush=True)
    if len(verified)>=target_new:
        break
    time.sleep(.13)

# No-profiles are checked, but can still be held/reserved/not registrable.
print("FINISH|checked="+str(checked)+"|taken="+str(taken)+"|errors="+str(len(failed))+"|new="+str(len(verified))+"|total="+str(len(baseline)+len(verified)),flush=True)
print("NEW_GROUPS|"+json.dumps(dict(collections.Counter(x["kind"] for x in verified)),ensure_ascii=False),flush=True)
print("NEW_INITIALS|"+json.dumps(dict(collections.Counter(x["word"][0] for x in verified)),ensure_ascii=False),flush=True)
if len(verified)<target_new:print("WARNING|not enough checked names to reach target",flush=True)

with (OUT/"expanded_to_5000_additions.tsv").open("w",encoding="utf8",newline="") as f:
    w=csv.writer(f,delimiter="\t")
    w.writerow(["Ник","Русское слово","Категория","Лемма","Часть речи","Число","Словарный ранг","Проверка"])
    for x in verified:
        w.writerow([x["nick"],x["word"],x["kind"],x["lemma"],x["pos"],x["number"],x["rank"],"NO_PROFILE"])
(OUT/"expanded_to_5000_additions.txt").write_text("\n".join(x["nick"] for x in verified)+"\n",encoding="utf8")
(OUT/"expanded_to_5000_all.txt").write_text("\n".join(baseline+[x["nick"] for x in verified])+"\n",encoding="utf8")
(OUT/"expanded_to_5000_report.json").write_text(json.dumps({
    "previous_total":len(baseline),
    "new_checked_no_profiles":len(verified),
    "total":len(baseline)+len(verified),
    "checked_attempted_successfully":checked,
    "registered_profiles_found":taken,
    "failed_api_batches":len(failed)//10,
    "available_claim_not_guaranteed":True,
    "new_groups":dict(collections.Counter(x["kind"] for x in verified)),
    "dictionary_forms":len(candidates),
    "unique_lemmas":len(distinct)
},ensure_ascii=False,indent=2)+"\n",encoding="utf8")
print("SUCCESS",flush=True)
