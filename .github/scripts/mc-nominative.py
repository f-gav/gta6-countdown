import re, json, collections, pathlib
import pymorphy3
from wordfreq import top_n_list
CYR = "авезикмнорстух"
TRANSLIT = dict(zip(CYR,["a","B","e","3","u","K","M","H","o","P","C","T","y","X"]))
pat = re.compile("["+CYR+"]{3,16}\\Z")
morph=pymorphy3.MorphAnalyzer()
bad_exact={"вуз","загс","сми","ооо","оон","нко","мкс","мкк","рнк","тнт","вто","нарсуд","совнарком","военком","совхоз","колхоз","совнарком","нарком","военком","комхоз","сельхоз","завком","завуч","комсомол","генсек","медсан","спецназ","торгпред","главк","горком","райком","исполком","обком","горисполком","райисполком","облисполком","комвуз","совмин","партком","парторг","профком","нархоз","нарсуд","предсов","предком"}
bad_prefix=("совхоз","нарком","военком","комхоз","исполком","главком","партком","профком")
bad_grammemes={"Name","Surn","Patr","Geox","Abbr"}
source=set(top_n_list("ru",420000))
candidate={}
def add(word, tag, lemma, rank, source_type):
    if not pat.fullmatch(word) or word in bad_exact or word.startswith(bad_prefix): return
    if any(c in tag.grammemes for c in bad_grammemes):return
    if tag.POS!="NOUN" or tag.case!="nomn":return
    prev=candidate.get(word)
    meta=(rank,int(tag.number!="sing"),lemma,source_type)
    if prev is None or meta[:2]<prev[:2]:
        candidate[word]=meta
for i,word in enumerate(top_n_list("ru",420000)):
    if not pat.fullmatch(word):continue
    parses=morph.parse(word)
    for p in parses:
        if not p.is_known or p.tag.POS!="NOUN" or any(t in p.tag.grammemes for t in bad_grammemes): continue
        if p.tag.case=="nomn":
            add(word,p.tag,p.normal_form,i,"direct")
        # For each known lexeme, include ONLY true nominative forms.
        if p.normal_form==word or (p.tag.case=="nomn" and p.tag.number=="plur"):
            for form in p.lexeme:
                if form.tag.case=="nomn":
                    add(form.word,form.tag,p.normal_form,i,"lexeme")
print("CANDIDATES|"+str(len(candidate)),flush=True)
print("INITIALS|"+json.dumps(dict(sorted(collections.Counter(w[0] for w in candidate).items())),ensure_ascii=False),flush=True)
print("SINGULAR|"+str(sum(v[1]==0 for v in candidate.values())),flush=True)
print("PLURAL|"+str(sum(v[1]==1 for v in candidate.values())),flush=True)
for letter in CYR:
    sorted_words=sorted(((w,m) for w,m in candidate.items() if w.startswith(letter)),key=lambda x:x[1][:2])
    print("SAMPLE|"+letter+"|"+json.dumps([w for w,m in sorted_words[:20]],ensure_ascii=False),flush=True)
out=pathlib.Path("out");out.mkdir(exist_ok=True)
rows=sorted([(w,"".join(TRANSLIT[c] for c in w),*meta) for w,meta in candidate.items()],key=lambda x:(x[2],x[3],x[0]))
with (out/"nominative_candidates.tsv").open("w",encoding="utf8") as f:
    f.write("russian\tnick\trank\tis_plural\tlemma\tsource\n")
    for row in rows:f.write("\t".join(map(str,row))+"\n")


# Independently check all nominated Russian noun forms using official public profile lookup.
import urllib.request, urllib.error, time, csv, os
api="https://api.minecraftservices.com/minecraft/profile/lookup/bulk/byname"
controls=["Notch","jeb_"]
def batch_lookup(names):
    payload=json.dumps(names).encode("utf-8")
    for attempt in range(8):
        try:
            req=urllib.request.Request(api,payload,method="POST",headers={
                "Content-Type":"application/json","Accept":"application/json",
                "User-Agent":"Russian-Nominative-Nickname-Audit/1.0"})
            with urllib.request.urlopen(req,timeout=28) as resp:
                data=json.load(resp)
            if not isinstance(data,list):raise RuntimeError("Non-list API output")
            return {str(x["name"]).casefold() for x in data}
        except urllib.error.HTTPError as e:
            if e.code==429:
                try: delay=max(3,min(45,int(e.headers.get("Retry-After","5"))))
                except Exception: delay=5
                delay=max(delay,min(3+attempt*3,20))
            else:delay=min(4+attempt*3,25)
            print("HTTP_RETRY|"+str(e.code)+"|attempt="+str(attempt)+"|delay="+str(delay),flush=True)
            time.sleep(delay)
        except Exception as e:
            delay=min(3+attempt*3,25)
            print("OTHER_RETRY|"+str(type(e).__name__)+"|"+str(e)[:80],flush=True)
            time.sleep(delay)
    return None

check=batch_lookup(controls)
assert check is not None and {"notch","jeb_"} <= check,"positive controls failed"
# Round robin by Cyrillic initial to ensure fair coverage even if some later batches fail.
queues={k:collections.deque(sorted((w,v) for w,v in candidate.items() if w[0]==k)) for k in CYR}
ordered=[]
while any(queues.values()):
    for letter in CYR:
        if queues[letter]:
            word,meta=queues[letter].popleft()
            ordered.append((word,"".join(TRANSLIT[c] for c in word),*meta))
found=set()
unknown=set()
successful=0
for i in range(0,len(ordered),10):
    group=ordered[i:i+10]
    hits=batch_lookup([x[1] for x in group])
    if hits is None:
        unknown.update(x[1] for x in group)
    else:
        successful+=len(group)
        found.update(hits)
    if (i//10)%40==0:
        print("API_PROGRESS|"+str(i+len(group))+"|taken="+str(len(found))+"|failed="+str(len(unknown)),flush=True)
    time.sleep(.13)

verified=[x for x in ordered if x[1].casefold() not in found and x[1] not in unknown]
verified.sort(key=lambda x:(x[0][0],x[2],x[3],x[0]))
print("API_DONE|total="+str(len(ordered))+"|successful="+str(successful)+"|taken="+str(len(found))+"|unknown="+str(len(unknown))+"|no_profile="+str(len(verified)),flush=True)
print("VERIFIED_INITIALS|"+json.dumps(dict(sorted(collections.Counter(x[0][0] for x in verified).items())),ensure_ascii=False),flush=True)
assert len(verified)>0 and successful>0,"no verified names"

output=pathlib.Path("out");output.mkdir(exist_ok=True)
(output/"nominative_verified_nicks.txt").write_text("\n".join(x[1] for x in verified)+"\n",encoding="utf8")
with (output/"nominative_verified_words.tsv").open("w",encoding="utf8",newline="") as file:
    w=csv.writer(file,delimiter="\t")
    w.writerow(["Ник","Русское слово","Первоначальная форма","Число","Статус","Частотный ранг"])
    for word,nick,rank,plural,lemma,src in verified:
        w.writerow([nick,word,lemma,"мн." if plural else "ед.","NO_PROFILE",rank])
report={
    "date_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
    "candidate_count":len(ordered),
    "checked_count":successful,
    "taken_names":len(found),
    "unchecked_due_to_errors":len(unknown),
    "no_current_profile":len(verified),
    "initial_distribution":dict(sorted(collections.Counter(x[0][0] for x in verified).items())),
    "nominative_only":True,
    "parts_of_speech":["NOUN"],
    "includes_plural_nominative":True,
    "abbreviation_exclusions":"Tag and manual excludes, not exhaustive.",
    "profile_search_is_not_registration_availability":True
}
(output/"nominative_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")

# Curated neutral base forms; include only names positively checked as no profile in this run.
favwords="""сквер сонет синева мозаика зенит рассказ зарево заря озеро океан оазис архив
метрика метронoм камертон терем сумерки свиток крона канат караван космос
сирена кора корона контраст кассета картина витрина нота тематика текстура
восток ветер вера весна мир море остров окно неон енот искра иней мрамор
кремень камень камни стакан стекло камертон тенор тенорок теннис какао
карман костюм туман ракета машина мотор арена момент мера мера квест
контур мантра роман риск парк полоса каток катер кромка коса театр
унисон гармония саксофон аккорд морс маска маски мираж вектор
ворон веранда маска соната инок нота кросс стена тест тайна коса
камера ромашка казна зонт знак звук засов ракурс орнамент
трос территория ковёр терраса камин нектар моховик куст караоке
кино кубок кисет кисея романтика кварц кварта квартет
мозаики вереск козырёк скат стих стихия сказка сукно
завеса заслон спектр немота серенада ветка вена""".split()
best={x[0]:x for x in verified if x[3]==0}
curated=[]
for word in favwords:
    if word in best and word not in [x[0] for x in curated]:
        curated.append(best[word])
if len(curated)<45:
    rest=[x for x in verified if x[3]==0 and 4<=len(x[1])<=10 and x[0] not in favwords]
    rest.sort(key=lambda x:(abs(len(x[1])-7),x[2]))
    curated+=rest[:min(45-len(curated),len(rest))]
with (output/"nominative_favorites.tsv").open("w",encoding="utf8",newline="") as file:
    w=csv.writer(file,delimiter="\t")
    w.writerow(["Ник","Слово"])
    for word,nick,*_ in curated:w.writerow([nick,word])
print("FAVORITES|"+str(len(curated)),flush=True)
print("END_SUCCESS",flush=True)
