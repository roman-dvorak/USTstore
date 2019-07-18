# Návrh databáze

## Jaké máme objekty

uživatel, jméno, adresa, smlouva, kus práce (jeden den od-do), dovolená, dokument

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
- pole adres
- telefon
- číslo účtu
- pracovní náplň
- pole smluv
- dovednosti
- poznámky

- pole kusů práce
- pole dovolených
- pole dokumentů

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

- od
- počet hodin
- poznámka

- na kterém projektu se dělalo (výběr z připravených možností)? - možnosti projektů uložit do kolekce intranet?

## Jméno
titulů, jmen i přijmení může mít člověk víc, ale nemá smysl to rozdělovat

- titul před jménem
- jméno
- přijmení
- titul za jménem

## Adresa
- ulice
- městská část?
- město
- stát
- PSČ
- typ - "trvalý pobyt", "kontaktní adresa"...

## Dokument
- typ - potvrzení o studiu, prohlášení k dani...
- platnost od
- platnost do
- cesta k souboru - v db (id) / na disku

## Dovolená 
- od
- do 
- nerušit - pokud pravda, neposílat emaily o uzavření docházky atd.