import inspect
import json

from bson import ObjectId
from contextlib import contextmanager
from pymongo.operations import InsertOne, UpdateOne, DeleteOne

from plugins import DbWithBulkOps
from plugins.helpers.db_experiments.db_fields import BaseField, StringField

"""
Tento modul obsahuje abstraktní třídy reprezentující dokumenty v MongoDB kolekcích. Jelikož se v rámci systému používá
slovo dokument v jiném smyslu, pro dokumenty v MongoDB databázi zavádíme název mdokument nebo mdoc. 

Za stávající implementace je zanoření mdokumentů limitováno na jednu úroveň zanoření, tzn. jednotlivé top-level 
mdokumenty v kolekci mohou mít pole embedded mdokumentů, ale mdokumenty v tomto poli již další pole embedded mdokumentů 
mít nemohou.

Cílem těchto wrapperů je abstrahovat operace nad mdokumenty v kolekcích tak, aby se v běžném kódu nemuselo pracovat s 
PyMongo dictionaries (protože tam neprobíhá žádná kontrola správnosti fieldů nebo typů hodnot). Každý mdokument je 
tedy obalen příslušným objektem, který poskytuje jeho fieldy jako properties (přesněji descriptors). Předpokládá se, 
že pro každý typ mdokumentu se vytvoří třída dědící jednu z těchto abstraktních tříd, ve které se následně definuje 
funkcionalita spojená s danou kolekcí/polem embedded mdokumentů.

Aby fungovalo ukládání do databáze, je nutné wrapper objektům předat referenci na speciální databázový objekt 
(momentálně je to DbWithBulkOps v database_wrapper) poskytující možnost přidávat MongoDB bulk operace a ty následně 
všechny najednou zapsat (v handlerech je v self.mdb). Tento objekt dědí z pymongo.database.Database a v těchto třídách
je uložen jako _database. 

Dědící třídy musí definovat konstantu COLLECTION s názvem kolekce, ve které jsou uložena reprezentovaná data a v případě
tříd obalujících embedded dokumenty také konstantu FIELD s názvem fieldu, ve kterém jsou uloženy.

Tyto třídy poskytují metody pro čtení a zápis do databáze. Snaha je být při manipulaci s db co nejlínější. 
Korespondující mdokument se z databáze načte až při prvním skutečném přístupu k datům, tzn. je-li objekt vytvořen jen 
za účelem zápisu, mdokument se vůbec nenačte. 

V kódu by se neměly používat konstruktory wrapper objektů, tzn. dědí-li třída MDocument např. od TopLevelMdocWrapper, 
nemělo by se volat MDocument(...). Místo toho by v každé dědící třídě měla být definována @classmethod metoda new() 
nebo new_*(), která bude ve vnějším kódu sloužit pro vytvoření nového mdokumentu v databázi. Abstraktní třídy určené 
pro mdokumenty s _id definují @classmethod metodu _new_empty(...), určenou pro interní použití v této new() nebo 
new_*() metodě. _new_empty() provede interní inicializaci a vrátí vytvořený objekt připravený k další inicializaci 
záležící na typu. 

Tyto třídy dále definují @classmethod metodu from_id(), které vytvoří wrapper objekt reprezentující mdokument s daným 
_id (ale jak bylo zmíněno výše, nenačítá data dokud nejsou potřeba). 

Pro definici dostupných fieldů se používají speciální descriptory (momentálně v db_fields.py). Implementace těchto 
descriptorů je značně couplovaná s implementací abstraktních wrapper tříd, při změně implementace je tedy třeba na toto
brát ohled.

Data jsou v wrapper objektu interně uložena v _mdoc. Ten po vytvoření objektu (ať už pomocí new() nebo from_id()) 
obsahuje jen field _id. Pro získání dat z databáze slouží interní metoda _get_from_mdoc(<field>), která při prvním 
použití volá metodu reload_from_database(), čímž populuje self._mdoc skutečnými daty. Poté, co je _mdoc aktuální, vrací
hodnotu požadovaného fieldu.

Hodnoty, které byly změněny, ale ještě nejsou zapsány v databázi, jsou uloženy se slovníku _updates, který má stejnou 
strukturu jako _mdoc. Pro zápis dat slouží interní metoda _process_updates(), která uloží změny do _updates a vytvoří 
novou bulk operaci v databázovém objektu. Pro samotné zapsání je nutné volat <databázový objekt>.write_operations().

Funkce _get_from_mdoc() a _process_updates() pracují správně s _updates. K _mdoc není radno přistupovat přímo, 
mohlo by se něco rozbít! Implementace jednotlivých descriptorů fieldů interně také používají tyto dvě funkce.

Některé fieldy mohou být nastaveny jako nezapisovatelné. Aby bylo možné je interně měnit (místo přímého používání 
_process_updates() - protože zápis přes descriptor umí validaci typů, což _process_updates() neumí), 
poskytují abstraktní třídy context manager _i_know_what_im_doing(), který pro daný blok přenastaví vnitřní proměnnou 
a umožní zápis do takovýchto fieldů.

TopLevelMdocWrapper je jediná třída, objekty jejíž potomků mohou obsahovat fieldy s embedded mdokumenty. Protože tyto 
embedded mdokumenty jsou samotné obalené do odpovídajících objektů a vrací se pole (list) těchto objektů, 
není žádoucí, aby se tento proces obalování opakoval při každém přístupu k takovému fieldu. Proto descriptor určný 
pro takovýto field implementuje chachování. Poté, co se poprvé přistoupí k takovému fieldu, proběhne obalení embedded 
mdokumentů a výsledné pole je uloženo do dictionary _cache. Poté se vždy vrací toto uložené pole. Cache lze v případě 
potřeby smazat pomocí clear_cache().

Jedna možná neefektivita, kterou se nepodařilo odstranit je úprava polí (jiných objektů než embedded mdokumentů). 
MongoDB sice umí pomocí $push a $pull ukládat jen změny v daném poli, nikoliv posílat celé pole, nepřišel jsem na 
způsob, jak toto implementovat, aniž by se rozbilo následné přistupování k tomuto poli před tím, než bylo uloženo do 
databáze (přesněji, nepřišel jsem na způsob, který by byl dostatečně jednoduchý a nemagický, aby se vyplatil). 
 Momentální přístup je takový, že kopírovat malá pole (s max 1000 prvky) je přijatelné, v případě větších polí by se pak 
 takové diferenciální updatování muselo řešit mimo systém descriptorů přímo pomocí _database.add_operation(...).
 
 Příklad:
 
 class ConcreteMdocType(TopLevelMdocWrapper):
    COLLECTION = "collection_name"    
 
    field1 = StringField("field1")
    field2 = IntegerField("field2", settable=False, deletable=False)
 
    @classmethod
    def new(cls, database, init_field1, init_field2):
        new_obj = cls._new_empty(database)
        new_obj.field1 = init_field1
        
        with new_obj.i_know_what_im_doing():
            new_obj.field2 = init_field2
            
 """


class MdocWrapper:
    COLLECTION = ""

    def __init__(self, database: DbWithBulkOps, mdoc=None):
        self._database = database
        self._updates = {}
        self._mdoc = mdoc
        self._is_mdoc_up_to_date = True
        self._i_know_what_im_doing = False

        if not self.COLLECTION:
            raise ValueError("The COLLECTION constant must be defined in this class.")

        self._collection = self._database[self.COLLECTION]

    @contextmanager
    def i_know_what_im_doing(self):
        try:
            self._i_know_what_im_doing = True
            yield
        finally:
            self._i_know_what_im_doing = False

    def _get_from_mdoc(self, field):
        if not self._is_mdoc_up_to_date:
            self.reload_from_database()

        return self._mdoc.get(field, None)

    def _add_operation(self, operation):
        self._database.add_operation(self.COLLECTION, operation)

    def _process_updates(self, updates):
        self._updates.update(updates)

    def reload_from_database(self):
        raise NotImplementedError()

    def clear_updates(self):
        self._updates = {}

    def get_json_serializable(self, *, included=None, excluded=None):
        field_descriptors = [descr for descr in self.__class__.__dict__.values()
                             if isinstance(descr, BaseField) and descr.serialize]

        if included:
            field_descriptors = [descr for descr in field_descriptors if descr.field in set(included)]

        if excluded:
            field_descriptors = [descr for descr in field_descriptors if descr.field not in set(excluded)]

        serializable = {descr.field: descr.__get__(self, None) for descr in field_descriptors}

        if hasattr(self, "id"):
            serializable["_id"] = self.id

        return serializable


class EmbeddedMdocWrapper(MdocWrapper):
    FIELD = ""

    def __init__(self, database, parent_id, mdoc=None):
        super().__init__(database=database, mdoc=mdoc)

        self._parent_id = parent_id

        if not self.FIELD:
            raise ValueError("The FIELD constant must be defined in this class.")

    def reload_from_database(self):
        raise NotImplementedError()


class TopLevelMdocWrapper(MdocWrapper):

    def __init__(self, database, mdoc):
        super().__init__(database, mdoc)
        self._cache = {}

    @classmethod
    def _new_empty(cls, database, _id=None):
        if not _id:
            _id = ObjectId()

        mdoc = {"_id": _id}

        obj = cls(database, mdoc)
        obj._add_operation(InsertOne(mdoc))

        return obj

    @classmethod
    def from_id(cls, database, _id):
        obj = cls(database=database, mdoc={"_id": _id})
        obj._is_mdoc_up_to_date = False

        return obj

    @classmethod
    def get_all(cls, database, **query_by):
        mdocs = database[cls.COLLECTION].find(query_by)

        return tuple(cls(database, mdoc) for mdoc in mdocs)

    def _process_updates(self, updates: dict):
        super()._process_updates(updates)

        if updates:
            self._add_operation(UpdateOne({"_id": self.id}, {"$set": updates}))

    @property
    def id(self):
        return self._mdoc["_id"]

    def reload_from_database(self):
        self._mdoc = self._collection.find_one({"_id": self.id})
        self.clear_cache()

    def delete(self):
        self._add_operation(DeleteOne({"_id": self.id}))

    def clear_cache(self):
        self._cache = {}


class EmbeddedMdocWithIdWrapper(EmbeddedMdocWrapper):

    @classmethod
    def _new_empty(cls, database, parent_id, embedded_id=None):
        """
        This class method is lazy, obj.write_operations() must be called afterwards!

        Adds new embedded document represented by the class to an array of specified parent mdoc in database.
        Every mdoc of this type must have an id, if none is provided, a new id is generated (text version of ObjectID).

        :param database: MongoDB database object
        :param parent_id: _id of parent mdoc
        :param embedded_id: _id of the new embedded document
        :return: object representing new embedded document
        """
        if not embedded_id:
            embedded_id = str(ObjectId())

        mdoc = {"_id": embedded_id}
        obj = cls(database, parent_id, mdoc)
        update = UpdateOne({"_id": parent_id}, {
            "$push": {
                cls.FIELD: mdoc
            }
        })

        obj._add_operation(update)

        return obj

    @classmethod
    def from_id(cls, database, parent_id, embedded_id):
        obj = cls(database=database, parent_id=parent_id, mdoc={"_id": embedded_id})
        obj._is_mdoc_up_to_date = False

        return obj

    def _process_updates(self, updates):
        super()._process_updates(updates)

        if updates:
            set_dict = {f"{self.FIELD}.$.{key}": value for key, value in updates.items()}

            self._add_operation(UpdateOne({"_id": self._parent_id, f"{self.FIELD}._id": self.id},
                                          {"$set": set_dict}))

    @property
    def id(self):
        return self._mdoc["_id"]

    def reload_from_database(self):
        mdoc = self._collection.find_one({"_id": self._parent_id, f"{self.FIELD}._id": self.id},
                                         {f"{self.FIELD}.$": 1})
        if not mdoc:
            return None

        field_content = mdoc.get(self.FIELD, None)

        self._mdoc = field_content[0] if field_content else None

    def delete(self):
        update = {"$pull": {
            self.FIELD: {
                "_id": self.id
            }
        }}
        self._add_operation(UpdateOne({"_id": self._parent_id}, update))


class SingleEmbeddedMdocWrapper(EmbeddedMdocWrapper):

    def _process_updates(self, updates):
        super()._process_updates(updates)

        if updates:
            set_dict = {f"{self.FIELD}.{key}": value for key, value in updates.items()}

            self._add_operation(UpdateOne({"_id": self._parent_id},
                                          {"$set": set_dict}))

    def reload_from_database(self):
        res = self._collection.find_one({"_id": self._parent_id}, {self.FIELD: 1})

        self._mdoc = res.get(self.FIELD, {}) if res else {}
