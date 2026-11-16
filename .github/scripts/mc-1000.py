import re, json, collections, time, urllib.request, urllib.error, sys
from wordfreq import top_n_list
import pymorphy3

ALPHABET="абвеикмнорстух"
MAPPING=dict(zip(ALPHABET, ["a","b","B","e","u","K","M","H","o","P","C","T","y","X"]))
VALID=re.compile("^["+ALPHABET+"]{3,16}$")
TARGET=1000
morph=pymorphy3.MorphAnalyzer()
groups=collections.defaultdict(list)
for rank,word in enumerate(top_n_list("ru",320000)):
    if not VALID.fullmatch(word): continue
    parsed=morph.parse(word)
    primary=parsed[0]
    if not(primary.tag.POS=="NOUN" and primary.normal_form==word and primary.is_known): continue
    tags=str(primary.tag)
    if any(x in tags for x in ("Name","Surn","Patr","Geox","Abbr")): continue
    nick="".join(MAPPING[c] for c in word)
    if not(3<=len(nick)<=16): continue
    groups[word[0]].append((word,nick,rank))
print("GENERATED|"+str(sum(map(len,groups.values()))),flush=True)
print("INITIALS|"+json.dumps({k:len(v) for k,v in sorted(groups.items())},ensure_ascii=False),flush=True)

# Preserve higher-frequency words, while not limiting variety to a few starting letters.
ordered=[]
# Round robin at query stage minimizes risk of failure causing a missing initial.
queue={x:list(v) for x,v in groups.items()}
used=set()
while True:
    moved=False
    for letter in ALPHABET:
        if not queue[letter]: continue
        word,nick,rank=queue[letter].pop(0)
        key=nick.casefold()   # Minecraft treats uppercase/lowercase as the same username.
        if key in used: continue
        used.add(key)
        ordered.append((letter,word,nick,rank))
        moved=True
    if not moved:break
print("UNIQUE_CANDIDATES|"+str(len(ordered)),flush=True)

# Official public profile lookup checks current profile existence, NOT exact name availability.
lookup_url="https://api.minecraftservices.com/minecraft/profile/lookup/bulk/byname"
controls=["Notch","jeb_"]
full=controls + [x[2] for x in ordered]
found=set()
failed=set()
for idx in range(0,len(full),10):
    batch=full[idx:idx+10]
    for attempt in range(6):
        try:
            req=urllib.request.Request(lookup_url,json.dumps(batch).encode(),{"User-Agent":"minecraft-nickname-audit/1.0","Content-Type":"application/json","Accept":"application/json"},method="POST")
            with urllib.request.urlopen(req,timeout=20) as response:
                result=json.load(response)
            if not isinstance(result,list):raise ValueError("Unexpected API response")
            found.update(x["name"].casefold() for x in result)
            break
        except urllib.error.HTTPError as e:
            if e.code==429:
                retry=e.headers.get("Retry-After") if e.headers else None
                try:delay=max(2,min(18,int(retry)))
                except (TypeError,ValueError):delay=min(3+attempt*2,15)
                print(f"RATE_LIMIT|{idx//10}|{attempt}|{delay}",flush=True)
                time.sleep(delay)
            else:
                print(f"HTTP_ERROR|{idx//10}|{attempt}|{e.code}",flush=True)
                time.sleep(2+attempt)
        except Exception as e:
            print(f"ERROR|{idx//10}|{attempt}|{type(e).__name__}|{str(e)[:80]}",flush=True)
            time.sleep(2+attempt)
    else:
        failed.update(batch)
    if idx%300==0:
        print(f"PROGRESS|{idx}|{len(found)}|{len(failed)}",flush=True)

print("CHECKED|"+str(len(ordered))+"|FOUND|"+str(len(found))+"|FAILED|"+str(len(failed)),flush=True)
assert {"notch","jeb_"}<=found,"Positive controls failed"
# Failed batches are omitted; never misreport a failed API call as available.
available=collections.defaultdict(list)
for letter,word,nick,rank in ordered:
    if nick not in failed and nick.casefold() not in found:
        available[letter].append((word,nick,rank))
print("UNREGISTERED|"+str(sum(map(len,available.values()))),flush=True)
print("BY_INITIAL|"+json.dumps({k:len(available[k]) for k in ALPHABET},ensure_ascii=False),flush=True)
selected=[]
while len(selected)<TARGET:
    moved=False
    for letter in ALPHABET:
        if available[letter]:
            word,nick,rank=available[letter].pop(0)
            selected.append((letter,word,nick))
            moved=True
            if len(selected)==TARGET:break
    if not moved:break
print("SELECTED_COUNT|"+str(len(selected)),flush=True)
print("SELECTED_BY_INITIAL|"+json.dumps(dict(sorted(collections.Counter(x[0] for x in selected).items())),ensure_ascii=False),flush=True)
for letter,word,nick in selected:
    print("SELECTED|"+letter+"|"+word+"|"+nick,flush=True)
assert len(selected)==TARGET,"Not enough verified-unregistered names"
