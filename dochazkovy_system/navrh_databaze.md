# Návrh databáze

## Jaké máme objekty

uživatel, jméno, adresa, smlouva, příloha (soubor), kus práce (jeden den od-do), dovolená

## Uživatel - co víme?

tyto fieldy už v db jsou

- uživatelské jméno "user"
- heslo "pass"
- email "email"
- mají ověřený email? "email_validate"
- pole rolí "role"
- kdy byl založen účet? "created"
- typ "type" - zatím "user" nebo "company", můžou být další

- jméno "name"

tyto je potřeba dořešit

- datum narození
- adresa trvalého pobytu
- kontaktní adresa
- telefon
- číslo účtu
- pracovní náplň
- pole smluv
- dovednosti
- poznámky

- pole kusů práce
- pole dovolených

- potvrzení o studiu - do kdy platí nebo null
- prohlášení o dani - do kdy platí nebo null

- kolik odpracovaných hodin v měsíci?
- kolik odpracovaných hodin v roce?

    tyhle dva fieldy se mi úplně nelíbí, protože opakují informace které v databázi už jsou ve fieldu kusů práce, ale bude potřeba tyto informace rychle získávat, protože budou kontrolované při každém zadání nového kusu práce - nevím jak to udělat líp

- má uživatel uzavřený měsíc?

## Smlouva

- typ smlouvy - DPP, poměr...
- datum uzavření smlouvy
- začátek platnosti
- konec platnosti
- hodinová sazba

- odvádíme daň?

    co ovlivňuje odvod daně?

- je podepsaná - platná?

## Kus práce - opravdu potřebuje lepší název
= v jednom dni jeden časový úsek práce od-do

- od - nepotřebujeme nutně znát, pak by to mohlo obsahovat datetime třeba půlnoci
- počet hodin
- poznámka

- na kterém projektu se dělalo (výběr z připravených možností)? - možnosti projektů uložit do kolekce intranet?

pokud uživatel zadá více kusů práce v jednom dni, budeme požadovat udání "od"? (abychom neměli záznamy tvrdící že uživatel pracoval dvakrát v jednom dni pokaždé od půlnoci, nebo na tom nezáleží?)

## Jméno
- titul před jménem - stačí jeden field, není důvod případných více titulů rozdělovat
- jméno - má smysl rozlišovat prostřední jména do samostatných fieldů?
  tj. {"jméno": "Jan Pavel", "přijmení": "Druhý"} vs. {"jméno": "Jan", "prostřední jméno": "Pavel", "přijmení": "Druhý"}
- přijmení - stačí jeden field
- titul za jménem - stačí jeden field

## Adresa
- ulice
- městská část?
- město
- stát
- PSČ

## Příloha
- typ - je to kopie pracovní smlouvy, potvrzení o studiu...
- popis
- datum nahrání
- kde je uložená - v db (id) / na disku (cesta)

## Dovolená 
- od
- do 
- nerušit - pokud pravda, neposílat emaily o uzavření docházky atd.