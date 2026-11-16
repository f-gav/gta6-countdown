import json, re, sys, time, urllib.request, collections
from wordfreq import top_n_list
import pymorphy3

MAX_WORDS=85000
PER_LETTER=120
TARGET=1000
# Visual Latin substitutions for the complete Russian alphabet.
MAPPING={
"а":"a","б":"b","в":"B","г":"r","д":"g","е":"e","ё":"e",
"ж":"X","з":"Z","и":"u","й":"u","к":"K","л":"JI","м":"M","н":"H","о":"o","п":"n",
"р":"P","с":"C","т":"T","у":"y","ф":"f","х":"X","ц":"u","ч":"h","ш":"W","щ":"W",
"ъ":"b","ы":"bI","ь":"b","э":"E","ю":"IO","я":"R"}
# These are less convincing as direct shape similarities and are penalized when selecting names.
APPROX=set("бгджзйлпфцчшщэюя")
morph=pymorphy3.MorphAnalyzer()
groups=collections.defaultdict(list)
seen=set()
input_words=top_n_list("ru",MAX_WORDS)
for idx,w in enumerate(input_words):
    if not re.fullmatch(r"[а-яё]{3,16}",w): continue
    if len(groups[w[0]]) >= PER_LETTER: continue
    pars=morph.parse(w)
    good=next((p for p in pars if p.tag.POS=="NOUN" and p.normal_form==w and not any(tag in str(p.tag) for tag in ("Name","Surn","Patr","Geox"))),None)
    if good is None: continue
    nick="".join(MAPPING[c] for c in w)
    if not 3<=len(nick)<=16 or nick.lower() in seen: continue
    seen.add(nick.lower())
    penalty=sum(c in APPROX for c in w)
    groups[w[0]].append((w,nick,penalty,idx))
print("CANDIDATES|"+str(sum(map(len,groups.values()))),flush=True)
print("INITIALS|"+json.dumps({k:len(v) for k,v in sorted(groups.items())},ensure_ascii=False),flush=True)
# Try visually closer, more common variants first per Russian initial.
for initial,opts in groups.items():
    opts.sort(key=lambda x: (x[2]//2, x[3]))
pairs=[]
for initial in sorted(groups):
    pairs += [(initial,*p) for p in groups[initial]]
known={"notch","jeb_"}
url="https://api.minecraftservices.com/minecraft/profile/lookup/bulk/byname"
found=set()
failed=[]
allnames=["Notch","jeb_"] + [p[2] for p in pairs]
print("API_INPUTS|"+str(len(allnames)),flush=True)
for idx in range(0,len(allnames),10):
    chunk=allnames[idx:idx+10]
    for attempt in range(4):
        try:
            req=urllib.request.Request(url,json.dumps(chunk).encode(),headers={"User-Agent":"MC-username-audit/1.0","Content-Type":"application/json","Accept":"application/json"},method="POST")
            with urllib.request.urlopen(req,timeout=25) as res:
                data=json.load(res)
            if not isinstance(data,list): raise ValueError("Expected list")
            batch={x["name"].casefold() for x in data}
            found.update(batch)
            break
        except Exception as e:
            print("ERROR|"+str(idx//10)+"|"+str(attempt)+"|"+str(e)[:100],flush=True)
            time.sleep(2.5*(attempt+1))
    else:
        failed+=chunk
    if idx%300==0: print("PROGRESS|"+str(idx)+"|"+str(len(found))+"|"+str(len(failed)),flush=True)
print("RESULT_COUNTS|"+str(len(found))+"|"+str(len(failed)),flush=True)
assert not failed,"At least one batch failed"
assert known <= found,"positive controls failed"
available=collections.defaultdict(list)
for letter,w,nick,penalty,rank in pairs:
    if nick.casefold() not in found:
        available[letter].append((w,nick,penalty,rank))
print("UNREGISTERED|"+str(sum(map(len,available.values()))),flush=True)
print("BY_INITIAL|"+json.dumps({k:len(v) for k,v in sorted(available.items())},ensure_ascii=False),flush=True)
assert sum(map(len,available.values())) >= TARGET,"Too few candidates"
# Fair round-robin per initial; scarcity is respected.
chosen=[]
while len(chosen)<TARGET:
    progress=False
    for letter in sorted(available):
        if available[letter]:
            word,nick,penalty,rank=available[letter].pop(0)
            chosen.append((letter,word,nick))
            progress=True
            if len(chosen)>=TARGET: break
    if not progress: break
print("SELECTION|"+str(len(chosen)),flush=True)
print("SELECTED_INITIALS|"+json.dumps(dict(sorted(collections.Counter(x[0] for x in chosen).items())),ensure_ascii=False),flush=True)
for letter,word,nick in chosen:
    print("SELECTED|"+letter+"|"+word+"|"+nick,flush=True)
assert len(chosen)==TARGET