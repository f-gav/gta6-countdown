import re, json, csv, pathlib, time, collections, urllib.request, urllib.parse, urllib.error

OUT=pathlib.Path("out")
CYR="авезикмнорстух"
MAP=dict(zip(CYR,"aBe3uKMHoPCTyX"))
PAT=re.compile(r"^[авезикмнорстух]{3,16}$")
BAD={"история","персонаж","персонажи","список","мультфильм","мультсериал","сериал","комикс","эпизод","фильм","герои","герой","войны","категория","книга","серии","сезон","сезоны","актера","артиста","актер","основа","звезда","сага","марвел","персонажам","все","роман"}
GROUPS={
"Фильмы — Звёздные войны":"Анакин Таркин Кассиан Сатин Траун Мотма Рева Сноук Хакс Меррин Меррин Хан Кино Нут Асока Реван",
"Фильмы — Гарри Поттер":"Рон Римус Сириус Северус Крам Симус Рита Аврора Ханна",
"Фильмы — Властелин колец":"Саурон Саруман Арвен Аман Нуменор Мерри Морвен",
"Фильмы Marvel":"Старк Стив Оса Земо Космо Ракета Танос Веном Мантис Карнак",
"Фильмы DC":"Аквамен Харви Затанна Старро Виксен Кара",
"Фильмы — Звёздный путь":"Кирк Сиско Кира Сарек Тувок Ухура Скотти Кес Ким Сато",
"Сериалы — Игра престолов":"Санса Тирион Теон Варис Станнис Томмен Мира Рамси Торос Мормонт Крастер Визерион",
"Сериалы — Во все тяжкие":"Мари Туко Виктор Тирус Ким Кенни",
"Сериалы — Очень странные дела":"Стив Макс Векна Карен Крисси",
"Сериалы — Доктор Кто":"Роза Марта Рори Мисси Ривер Рани",
"Сериалы — Сверхъестественное":"Ровена Амара Кевин",
"Сериалы — Ходячие мертвецы":"Рик Аарон Розита Тара Иисус",
"Сериалы — Пацаны":"Нуар Тек",
"Мультсериалы — Рик и Морти":"Морти Саммер Мисикс",
"Мультсериалы — Симпсоны":"Красти Скиннер Смитерс Кирк Мартин Отто",
"Мультсериалы — Губка Боб":"Карен Мермен",
"Мультсериалы — Футурама":"Мом",
"Мультфильмы — Шрек":"Арти Кот",
"Мультфильмы — Холодное сердце":"Анна Свен Ханс",
"Мультфильмы — Тачки":"Маккуин Круз Рамирес",
"Мультфильмы — История игрушек":"Рекс",
"Мультфильмы — Король Лев":"Скар Тимон Зазу Кову Киара Витани Зира Нука",
"Мультфильмы — Зверополис":"Ник Отертон",
"Мультфильмы — Энканто":"Антонио",
"Мультфильмы — Душа":"Терри Керри",
"Мультфильмы — Трансформеры":"Старскрим",
"Мультсериалы — Соник":"Соник Крим Зина Зик Завок Зазз Зомом Зор Космо",
"Игры — Pokémon":"Ротом Иви Арсеус Зоруа Зороарк Вапореон Оникс Суикун Раттата Зекром Некрозма Краморант Сном Омастар Марактус",
"Игры — World of Warcraft":"Артас Вариан Утер Рексар Таурен",
"Игры — Ведьмак":"Весемир Трисс Карантир Вернон Орианна Ума Хаттори",
"Игры — Skyrim":"Серана Мирак Мора Назир Рикке Ситис Азура Вермина Хирсин Мерунес Намира Зенитар Мара Кинарет",
"Игры — Fallout":"Вероника Рекс Виктор Кристин Ник Амата Сара",
"Игры — Baldur's Gate 3":"Астарион Минтара Минск Торм Кетерик Саревок Мизора",
"Игры — Dragon Age":"Зевран Винн Варрик Карвер Сера Рук Нив",
"Игры — Mass Effect":"Моринт Самара Касуми Сарен Хакет Рекс",
"Игры — Cyberpunk 2077":"Ривер Керри Такемура Мисти Виктор Ханако Хансен",
"Игры — Final Fantasy":"Винсент Зак Риноа Виви Аурон Рикку Вакка",
"Игры — Kingdom Hearts":"Сора Роксас Аква Вентус Терра Ксеханорт Ксенмас",
"Игры — Hollow Knight":"Хорнет Зот Носк Унн Исма Мономон Маркот Оро Мато Тисо Нимм",
"Игры — Undertale Deltarune":"Санс Меттатон Крис Квин Тенна Роар",
"Игры — Genshin Impact":"Сахароза Итто Венти Мона Кокоми Тома Сара Кавех Мавуика Иансан Оророн Скирк Варка Мико",
"Игры — Honkai Star Rail":"Химеко Ахерон Искорка Хохо Анакса Кирена",
"Игры — League of Legends":"Ахри Векс Катарина Сивир Сорака Карма Варус Сетт Самира Рената Кеннен Тимо Зери Орианна Киана Ксерат Нами Насус Нико Орнн Раммус Ривен Сенна Скарнер Тарик Тристана Виктор Зои Зира",
"Игры — Dota 2":"Акс Веномансер Вивер Марс Мирана Никс Рики Свен Тинкер Тини Туск Урса Хускар Кез",
"Игры — Mortal Kombat":"Зиро Китана Кано Ермак Нитара Сектор Смоук Мотаро Хавик Кроника",
"Игры — Tekken":"Нина Анна Аска Стив Кума Ноктис Азусена",
"Игры — Resident Evil":"Крис Вескер Итан Миа Роуз Ханк Рамон Сера Мороу Немезис",
"Игры — Assassin's Creed":"Коннор Арно Марио Катерина",
"Игры — Zelda":"Равио Касс Руто Нави Зант",
"Игры — Overwatch":"Уинстон Мерси Ана Симметра Кирико Раматтра",
"Игры — Valorant":"Сова Омен Астра Неон Исо Техо Вето",
"Аниме — One Piece":"Крокус Сенор Кинемон Кику Рокс Корасон Росинант Катакури Овен Крекер",
"Аниме — Атака титанов":"Кенни",
"Аниме — Клинок рассекающий демонов":"Томиока Аказа Музан Руи Узуи",
"Аниме — Магическая битва":"Рика Такума Мехамару Урауме Ханами Инумаки",
"Аниме — Тетрадь смерти":"Наоми Мисора",
"Аниме — Человек бензопила":"Куанси Космо Санта",
"Аниме — Блич":"Орихиме Урахара Старрк Иккаку Киске",
"Аниме — Евангелион":"Аска Каору Мари Кенске Наоко",
}
ROOT_CATEGORIES=[
"Категория:Персонажи «Звёздных войн»",
"Категория:Персонажи Саги Скайуокеров",
"Категория:Персонажи историй о Гарри Поттере",
"Категория:Персонажи романа «Властелин колец»",
"Категория:Персонажи телесериала «Мандалорец»",
"Категория:Персонажи мультсериала «Звёздные войны: Войны клонов»",
"Категория:Персонажи мультсериала «Звёздные войны: Повстанцы»",
"Категория:Персонажи компьютерных игр по франшизе",
"Категория:Персонажи мультфильмов",
"Категория:Персонажи комиксов Marvel Comics",
"Категория:Персонажи DC Comics",
"Категория:Персонажи телесериалов",
"Категория:Персонажи фильмов",
]
def wiki(opts):
    url="https://ru.wikipedia.org/w/api.php?"+urllib.parse.urlencode({"format":"json",**opts})
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (MCUsernameSourceAudit/1.0)"})
    with urllib.request.urlopen(req,timeout=27) as resp:return json.load(resp)
def members(cat):
    token=None
    for n in range(3):
        d={"action":"query","list":"categorymembers","cmtitle":cat,"cmlimit":"500"}
        if token:d["cmcontinue"]=token
        try:res=wiki(d)
        except Exception as e:
            print("WIKI_ERROR|"+cat+"|"+str(e)[:80],flush=True)
            break
        for entry in res.get("query",{}).get("categorymembers",[]):yield entry
        token=res.get("continue",{}).get("cmcontinue")
        if token is None:break

previous=set(x.strip().casefold() for x in (OUT/"expanded_media_all_v2.txt").read_text(encoding="utf8").splitlines() if x.strip())
candidates={}
def add(word,category,source,orig):
    word=word.lower().replace("ё","е")
    if word in BAD or not PAT.fullmatch(word):return
    nick="".join(MAP[c] for c in word)
    if nick.casefold() in previous:return
    key=nick.casefold()
    if key not in candidates:
        candidates[key]={"nick":nick,"word":word,"media":category,"source":source,"origin":orig}
for category,tokens in GROUPS.items():
    for word in tokens.split():add(word,category,"curated",word)
print("CURATED_NEW|"+str(len(candidates)),flush=True)
for cat in ROOT_CATEGORIES:
    titles=[]
    for entry in members(cat):
        if entry["ns"]==0:titles.append(entry["title"])
    for title in titles:
        text=re.sub(r"\([^)]*\)"," ",title).replace("ё","е")
        for name in re.findall(r"[А-ЯЁ][а-яё]{2,15}",text):
            add(name,cat,"wikipedia",title)
print("TOTAL_NEW_CANDIDATES|"+str(len(candidates)),flush=True)
API="https://api.minecraftservices.com/minecraft/profile/lookup/bulk/byname"
def check(chunk):
    for attempt in range(6):
        try:
            req=urllib.request.Request(API,json.dumps(chunk).encode(),headers={"Content-Type":"application/json","Accept":"application/json","User-Agent":"MCNameAudit/3.0"},method="POST")
            with urllib.request.urlopen(req,timeout=23) as r:res=json.load(r)
            if not isinstance(res,list):raise ValueError("Unexpected response")
            return {e["name"].casefold() for e in res}
        except Exception as e:
            print("RETRY|"+str(type(e).__name__)+"|"+str(e)[:70],flush=True)
            time.sleep(min(3+attempt*3,20))
    return None
controls=check(["Notch","jeb_"])
assert controls and {"notch","jeb_"}<=controls,"Invalid positive controls"
items=list(candidates.values())
found=set()
failed=set()
for offset in range(0,len(items),10):
    batch=[x["nick"] for x in items[offset:offset+10]]
    result=check(batch)
    if result is None: failed.update(x.casefold() for x in batch)
    else: found.update(result)
    if offset%300==0:print("PROGRESS|"+str(offset)+"|used="+str(len(found))+"|failed="+str(len(failed)),flush=True)
    time.sleep(0.1)
new=[x for x in items if x["nick"].casefold() not in found and x["nick"].casefold() not in failed]
new.sort(key=lambda x:(0 if x["source"]=="curated" else 1,len(x["nick"]),x["nick"]))
print("COMPLETE|total_candidates="+str(len(items))+"|taken="+str(len(found))+"|failed="+str(len(failed))+"|new="+str(len(new)),flush=True)
counts=dict(collections.Counter(x["media"] for x in new))
print("BY_MEDIA|"+json.dumps(counts,ensure_ascii=False),flush=True)
with (OUT/"cross_media_new.tsv").open("w",encoding="utf8",newline="") as f:
    writer=csv.writer(f,delimiter="\t")
    writer.writerow(["Никнейм","Оригинальное имя","Произведение или категория","Источник","Полное имя/страница"])
    for x in new:writer.writerow([x["nick"],x["word"],x["media"],x["source"],x["origin"]])
(OUT/"cross_media_new.txt").write_text("\n".join(x["nick"] for x in new)+"\n",encoding="utf8")
(OUT/"cross_media_all.txt").write_text("\n".join(list(x.strip() for x in (OUT/"expanded_media_all_v2.txt").read_text(encoding="utf8").splitlines() if x.strip())+[x["nick"] for x in new])+"\n",encoding="utf8")
(OUT/"cross_media_report.json").write_text(json.dumps({"new":len(new),"candidate_count":len(items),"taken":len(found),"failed":len(failed),"sources":counts},ensure_ascii=False,indent=2)+"\n",encoding="utf8")
for x in new:print("RESULT|"+x["nick"]+"|"+x["word"]+"|"+x["media"],flush=True)
print("END_SUCCESS",flush=True)
