import re, json, collections, pathlib
import pymorphy3
from wordfreq import top_n_list
CYR = "авезикмнорстух"
TRANSLIT = dict(zip(CYR,["a","B","e","3","u","K","M","H","o","P","C","T","y","X"]))
pat = re.compile("["+CYR+"]{3,16}\\Z")
morph=pymorphy3.MorphAnalyzer()
bad_exact={"совхоз","колхоз","совнарком","нарком","военком","комхоз","сельхоз","завком","завуч","комсомол","генсек","медсан","спецназ","торгпред","главк","горком","райком","исполком","обком","горисполком","райисполком","облисполком","комвуз","совмин","партком","парторг","профком","нархоз","нарсуд","предсов","предком"}
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
