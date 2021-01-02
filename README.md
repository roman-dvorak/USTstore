# UST - OpenIntranet

Systém umožňující správu v organizaci zabývající se řešením open-source projektů. 

## Motivace

U organizace, která se skládá z týmů lidí pracujících na jednom, nebo více open-source projektech, vznikají různé agendy, které je potřeba zvládat co nejefektivněji, přehledně a v dnešní době i z jakéhokoliv zařízení on-line. Seskupení těchto nástrojů je často v rámci podniku nazýváno intranetem. 

Obsahem intranetu je standardně správa skladových zásob, docházková agenda, fakturace, smlouvy, atd. Velké společnosti vynakládají velké finanční prostředky na pořízení robustních systémů jim na míru. Malým a středním firmám většinou nezbývá nic jiného, než zvolit běžné komerční řešení. Na trhu se jich pohybuje celá řada. Některé jsou i velmi zdařilé, ale mají vždy jeden společný problém. Skoro vždy se najde něco, co v dané aplikaci chybí a ochota vývojových firem provést nějakou změnu je poměrně malá. Dost často se jedná o nepochopitelné maličkosti, které by hodně zefektivnili práci.

Běžným stavem tak je, že systém umí párovat příchozí platby na firemní účet, ale již není schopný generovat příkazy k platbě, které by stačilo následně jen autorizovat v internetovém bankovnictví. Přitom v zásadě systém zná všechny potřebné informace od opakovaných dodavatelů. 

Mnoho jiných skladových systémů umí naskladňovat, vyskladňovat, prodat položku, ale je již problém s položek dělat další položky a z nich následně složit výsledné zařízení. Chybí i možnost provádět objednání pro výrobu s generováním výstupních dat, které akceptují e-shopy dodavatelů, s tím spojené automatizované naskladnění po dodávce. (Tato funkce je kritická zejména při nákupu elekronických součástek podle BOM)

Tyto a další nedostatky nás vedly k vytvoření open-source intranetu, kde bude možné využít stávající implementaci a v případě potřeby si je upravit pro svoje vlastní potřeby, bez nutnosti dělat vše od začátku.

Z tohoto důvodu budeme určitě rádi, pokud najdeme partnera pro spolupráci na tomto typu projektu. 

## Současná implementace


 [Návody a popis](https://github.com/UniversalScientificTechnologies/OpenIntranet/wiki)

## Seznam plánovaných modulů

Následující moduly jsou v různé fázi rozpracovanosti, některé jsou již implementovány do současné struktury intranetu, jiné čekají na konkretizace svojí definice a následnou implementaci. 

### Správce skladu

Základní modul sloužící k orientaci a vyhledávání ve skladu a k běžným operacím se skladovými položkami.

### Inventura

Modul usnadňující pravidelnou a systematickou inventarizaci položek, zejména za účelem odhalení chybějících položek.

### Adresář

Adresář uživatelů, zákazníků, dodavatelů o podobně, usnadňuje orientaci a minimalizuje chyby vznikající roztříštěním informací v různých poznámkách uvnitř organizace. 

### Nákupy

Modul usnadňující nákupy. (zejména opakované)

### Prodej

Umožňuje prodej položek a zařízení třetím osobám. 

### Zařízení

V podstatě typ pohledu na sklad z hlediska sestavených celků vytvořených z menších skladových položek. 

### Projekty

Projekty, na které jsou dedikovány některé prostředky které intranet pokrývá.

### Docházka a platby

Modul řešící rozdělování příjmových prostředků, pomocí předem definovaných dohod. 

### Fakturace

Usnadňuje možnost fakturace za služby provedené organizací. 

### Platby

Zjednodušuje správu plateb za pohledávky třetích stran. 
