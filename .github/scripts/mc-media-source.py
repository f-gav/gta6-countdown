import urllib.request, urllib.parse, json, re, time
sources={}
head={"User-Agent":"MinecraftNameFinder/1.0 (wikidata public label lookup; contact example@example.com)","Accept":"application/sparql-results+json"}
queries={
 "characters_direct":'SELECT ?item ?label WHERE { ?item wdt:P31 wd:Q95074; rdfs:label ?label. FILTER(LANG(?label)="ru") } LIMIT 10000',
 "characters_related":'SELECT ?item ?label WHERE { ?item wdt:P31/wdt:P279* wd:Q95074; rdfs:label ?label. FILTER(LANG(?label)="ru") } LIMIT 10000',
}
for key,q in queries.items():
    try:
        url="https://query.wikidata.org/sparql?"+urllib.parse.urlencode({"query":q,"format":"json"})
        req=urllib.request.Request(url,headers=head)
        with urllib.request.urlopen(req,timeout=110) as r:
            data=json.load(r)
        labels=[p["label"]["value"] for p in data["results"]["bindings"]]
        sources[key]=labels
        print(f"SOURCE_OK|{key}|{len(labels)}|{labels[:30]}",flush=True)
    except Exception as e:
        print(f"SOURCE_ERR|{key}|{type(e).__name__}|{str(e)[:200]}",flush=True)
for key,title in [
 ("ruwiki_anime","Категория:Персонажи аниме и манги"),
 ("ruwiki_naruto","Категория:Персонажи «Наруто»"),
 ("ruwiki_games","Категория:Персонажи компьютерных игр"),
]:
    try:
        q=urllib.parse.urlencode({"action":"query","list":"categorymembers","cmtitle":title,"cmlimit":"500","format":"json"})
        req=urllib.request.Request("https://ru.wikipedia.org/w/api.php?"+q,headers={"User-Agent":"Mozilla/5.0 (MCNickAnalyzer)"})
        with urllib.request.urlopen(req,timeout=40) as r: data=json.load(r)
        labels=[p["title"] for p in data["query"].get("categorymembers",[])]
        sources[key]=labels
        print(f"WIKI_OK|{key}|{len(labels)}|{labels[:30]}",flush=True)
    except Exception as e:
        print(f"WIKI_ERR|{key}|{type(e).__name__}|{str(e)[:200]}",flush=True)
print("DONE|"+str(sum(len(x) for x in sources.values())),flush=True)
