import re, json, collections, time
from wordfreq import top_n_list
import pymorphy3
ALPHABET="абвеикмнорстух"
MAP=dict(zip(ALPHABET,["a","b","B","e","u","K","M","H","o","P","C","T","y","X"]))
RE=re.compile("^["+ALPHABET+"]{3,16}$")
m=pymorphy3.MorphAnalyzer()
groups=collections.defaultdict(list)
roots=collections.defaultdict(set)
by_form=collections.defaultdict(list)
counters=collections.Counter()
for rank,word in enumerate(top_n_list("ru",320000)):
    if not RE.fullmatch(word): continue
    counters["matching_chars"]+=1
    parses=m.parse(word)
    known=[p for p in parses if p.tag.POS=="NOUN" and p.is_known and not any(t in str(p.tag) for t in ("Name","Surn","Patr","Geox"))]
    if not known: continue
    p=known[0]
    nick="".join(MAP[c] for c in word)
    if p.normal_form==word:
        groups[word[0]].append((word,nick,rank,p.normal_form))
        roots[word[0]].add(p.normal_form)
        counters["lemma"]+=1
    else:
        by_form[word[0]].append((word,nick,rank,p.normal_form))
        counters["form"]+=1
print("ALPHABET|"+json.dumps(MAP,ensure_ascii=False),flush=True)
print("COUNTERS|"+json.dumps(counters,ensure_ascii=False),flush=True)
print("LEMMAS|"+json.dumps({x:len(groups[x]) for x in ALPHABET},ensure_ascii=False),flush=True)
print("FORMS|"+json.dumps({x:len(by_form[x]) for x in ALPHABET},ensure_ascii=False),flush=True)
for k in ALPHABET:
    print("EXAMPLES|"+k+"|"+json.dumps(groups[k][:25],ensure_ascii=False),flush=True)
