import json, urllib.request, urllib.parse, re, collections, time
SEARCH=["Звёздные войны","Гарри Поттер","Властелин колец","Игра престолов","Дом Дракона","Ведьмак","Очень странные дела","Остаться в живых","Во все тяжкие","Лучше звоните Солу","Доктор Кто","Шерлок","Офис","Друзья","Сверхъестественное","Вампирские дневники","Стрела","Флэш","Пацаны","Ходячие мертвецы",
"Симпсоны","Футурама","Гриффины","Южный Парк","Гравити Фолз","Рик и Морти","Время приключений","Аватар легенда об Аанге","Аватар легенда о Корре","Леди Баг","Черепашки ниндзя","Скуби Ду","Шрек","История игрушек","Как приручить дракона","Холодное сердце","Король Лев","Зверополис","Тачки",
"Варкрафт","World of Warcraft","Дота","League of Legends","Genshin Impact","Honkai Star Rail","Mass Effect","Dragon Age","Baldur's Gate","Skyrim","Oblivion","Fallout","Cyberpunk 2077","The Last of Us","God of War","Red Dead Redemption","GTA","Grand Theft Auto","Resident Evil","Final Fantasy","Kingdom Hearts","Hollow Knight","Undertale","Deltarune","Overwatch","Valorant","Assassin's Creed","Sonic","Mario","Zelda","Minecraft","Mortal Kombat","Tekken","Street Fighter","Persona","Yakuza","StarCraft","Diablo","Dungeons and Dragons",
"Marvel","Мстители","Люди икс","DC Comics","Бэтмен","Супермен","Человек паук","Дэдпул"]
def fetch(params):
    base="https://ru.wikipedia.org/w/api.php?"+urllib.parse.urlencode({"format":"json",**params})
    req=urllib.request.Request(base,headers={"User-Agent":"Mozilla/5.0 (FictionalNamesResearch/1.0)"})
    with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
cats=set()
listpages=set()
for term in SEARCH:
    for ns in ("14","0"):
        try:
            prefix="персонажи "+term if ns=="14" else "список персонажей "+term
            d=fetch({"action":"query","list":"search","srsearch":prefix,"srnamespace":ns,"srlimit":"20"})
            results=d.get("query",{}).get("search",[])
            if ns=="14":
                for x in results:
                    title=x["title"]
                    if any(v in title.lower() for v in ("персонаж","герои","комикс","злодей","монстры")):cats.add(title)
            else:
                for x in results:
                    if "персонаж" in x["title"].lower() or "герои" in x["title"].lower():listpages.add(x["title"])
        except Exception as e:print("ERR|"+term+"|"+ns+"|"+str(e)[:90],flush=True)
    if len(cats)%25<2:print("SEARCH_PROGRESS|"+term+"|cats="+str(len(cats))+"|lists="+str(len(listpages)),flush=True)
print("CATEGORIES|"+str(len(cats)),flush=True)
print("LISTS|"+str(len(listpages)),flush=True)
for x in sorted(cats):print("CAT|"+x,flush=True)
for x in sorted(listpages)[:150]:print("LIST|"+x,flush=True)
