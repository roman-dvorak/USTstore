# Návrh databáze

## Jaké máme objekty

uživatel, jméno, adresa, smlouva, kus práce (jeden den od-do), dovolená, dokument, výplata

## Uživatel "user" - co víme?

tyto fieldy už v db jsou

- uživatelské jméno "user"?
- heslo "pass"
- email "email"
- mají ověřený email? "email_validate"
- pole rolí "role"
- kdy byl založen účet? "created"
- typ "type" - zatím "user" nebo "company", můžou být další

- jméno "name"

tyto je potřeba dořešit

- datum narození "birthdate"
- pole adres "addresses"
- telefon "phone_number"
- číslo účtu "account_number"
- pracovní náplň "assignment"
- pole smluv "contracts"
- dovednosti "skills"
- poznámky "notes"

- pole kusů práce "work_spans"?
- pole dovolených "vacations"
- pole dokumentů "documents"
- pole výplat "wages"

- má uživatel uzavřený měsíc? "month_closed"

## Smlouva "contract"

- typ smlouvy "type" - DPP, poměr...
- datum uzavření smlouvy "signing_date" - nazval bych to anglicky takto ikdyž ta smlouva nemusí být k tomuto dni fyzicky podepsaná
- začátek platnosti "valid_from"
- konec platnosti "valid_until"
- hodinová sazba "hour_rate"
- je podepsaná - platná? "is_valid"

odvod daně se bude řešit každý měsíc individuálně

## Kus práce "work_span" - opravdu potřebuje lepší název
= v jednom dni jeden časový úsek práce od-do

- od "from"
- počet hodin "hours"
- poznámka "note"

- na kterém projektu se dělalo "assignment" - možnosti projektů uložit do kolekce intranet?

## Jméno "name"
titulů, jmen i přijmení může mít člověk víc, ale nemá smysl to rozdělovat

- titul před jménem "pre_nominal_title"
- jméno "first_name"
- přijmení "surname"
- titul za jménem "post_nominal_title"

## Adresa "address"
- ulice "street"
- městská část? "city_district"
- město "city"
- stát "country"
- PSČ "postal_code"
- typ "type" - "trvalý pobyt", "kontaktní adresa"...

## Dokument "document"
- typ "type" - potvrzení o studiu, prohlášení k dani...
- platnost od "valid_from"
- platnost do "valid_until"
- cesta k souboru "path_to_file" - v db (id) / na disku

## Dovolená "vacation"
- od "from"
- do "until"
- nerušit "do_not_disturb" - pokud pravda, neposílat emaily o uzavření docházky atd.

## Výplata "wage"
- měsíc "month"
- kolik odpracovaných hodin za měsíc "hours_worked"
- hrubá mzda "gross_wage"
- platíme daň? "is_taxed"
- čistá mzda "net_wage"