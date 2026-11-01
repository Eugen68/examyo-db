# examyo-db

Întrebările pentru examenul de radioamator YO, cu răspunsuri și explicații, în format **JSON** și **CSV**, gata de folosit în aplicații sau de citit offline.

Datele provin din [Sim_exam_yo](https://github.com/6oskarwN/Sim_exam_yo), simulatorul de examen creat de **Francisc Toth, YO6OWN**, care rulează pe [examyo.scienceontheweb.net](http://examyo.scienceontheweb.net). Tot meritul pentru întrebări și rezolvări le aparține lui YO6OWN și contributorilor menționați la fiecare întrebare. Acest repo doar le convertește într-un format mai ușor de folosit.

## Nu e o copie înghețată

Repo-ul original e inclus ca submodul (`upstream/`), iar un GitHub Action verifică în fiecare luni dacă au apărut modificări. Dacă da, regenerează automat datele. Versiunea exactă din care s-au generat fișierele e în `data/index.json` (`upstream_commit`).

**Greșelile și sugestiile se raportează la sursă**, prin [Colectare erori și sugestii](http://examyo.scienceontheweb.net/cgi-bin/troubleticket.cgi?type=0) de pe site, nu aici. Corecturile ajung apoi și în acest repo la următoarea sincronizare.

## Conținut

| Fișier | Clase | Întrebări | Cu explicație |
|---|---|---:|---:|
| `radiotehnica-clasa-1` | I | 278 | 220 |
| `radiotehnica-clasa-2` | II | 660 | 597 |
| `radiotehnica-clasa-3` | III | 460 | 443 |
| `legislatie-clasa-1-2` | I, II | 122 | 52 |
| `legislatie-clasa-3` | III | 121 | 51 |
| `legislatie-clasa-4` | IV | 62 | 25 |
| `sanctiuni` | toate | 33 | 17 |
| `operare-clasa-1-2` | I, II | 67 | 66 |
| `operare-clasa-3` | III | 67 | 66 |
| `operare-clasa-4` | IV | 63 | 60 |
| `ntsm-clasa-1-3` | I, II, III | 65 | 50 |
| `ntsm-clasa-4` | IV | 60 | 48 |

Cifrele sunt de la generarea inițială (upstream `c6b0d25`, octombrie 2026); cele curente sunt în `data/index.json`. Maparea pe clase e cea folosită de simulatorul original: examenul de clasa I folosește radiotehnica-clasa-1, legislatie-clasa-1-2, operare-clasa-1-2, ntsm-clasa-1-3 și sanctiuni, și așa mai departe. Clasa a IV-a nu are probă de radiotehnică.

```
data/
  <slug>.json        o bază de date, cu metadate și întrebări
  all.json           toate bazele într-un singur fișier (compact)
  index.json         lista bazelor, versiuni, commit-ul upstream
  csv/<slug>.csv     aceleași date, tabelar (UTF-8 cu BOM, se deschide corect în Excel)
images/              figurile din întrebări și din rezolvări
```

## Formatul unei întrebări

```json
{
 "id": "radiotehnica-clasa-1/0",
 "number": 0,
 "code": "01B245",
 "question": "Care este raportul de transformare al transformatorului de impedanta din figura, ...?",
 "image": {"file": "images/I2b_177.jpg", "width": 177},
 "answers": ["16:1", "4:1", "64:4", "1:1"],
 "correct": "b",
 "correct_index": 1,
 "contributor": "YO6OWN, Brasov, 2010, ...",
 "explanation": "ANALIZA PROBLEMEI :\nTransformatorul din figura este ...",
 "explanation_image": null,
 "explanation_author": "YO6OWN, Brasov, 2010",
 "html": {"question": "...", "answers": ["..."], "explanation": "..."}
}
```

- `question`, `answers` și `explanation` sunt **text simplu**: `<br>` devine linie nouă, indicii și exponenții devin Unicode (`Pₚ`, `x²`) sau `_x` / `^(xy)` când nu există caracterul, linkurile devin `text (url)`.
- `html` păstrează textul original, cu formatarea completă. E util dacă afișezi într-un WebView sau pe o pagină.
- `explanation` e `null` pentru întrebările fără rezolvare.
- `code` e codul intern al întrebării din simulator. Aceeași întrebare poate apărea în mai multe baze (de exemplu legislație I-II și III), cu același cod.
- `width` e lățimea în pixeli la care simulatorul afișează figura.

## Regenerare locală

```sh
git clone --recurse-submodules https://github.com/Eugen68/examyo-db
cd examyo-db
git submodule update --remote upstream   # opțional: ultima versiune upstream
python3 tools/convert.py
```

Nu are nevoie de alte pachete în afară de Python 3.

## Licență

Bazele de date și programul original sunt distribuite de YO6OWN sub **GNU GPL v2 sau ulterioară**. Acest repo, inclusiv scriptul de conversie și datele derivate, e sub aceeași licență (vezi `LICENSE`). Orice redistribuire trebuie să păstreze licența și atribuirea către YO6OWN.
