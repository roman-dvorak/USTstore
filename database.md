

# MondoDB


## Views DB

View pro pozice obsahujici jejich cesty
```
db.createView("store_positions_complete", "store_positions", [
{
   "$graphLookup": {
      "from": 'store_positions',
      "startWith": '$parent',
      "connectFromField": "parent",
      "connectToField": "_id",
      "as": 'path'
   }
},
{
    "$addFields": {
        "path_string": "$path.name"
    }
},
{
   "$lookup": {
       "from": 'warehouse',
       "localField": 'warehouse',
       "foreignField": '_id',
       "as": 'warehouse',
   }
},
{
   "$set": { "warehouse": { "$first": "$warehouse" }}
},

])
```



View pro kategorie obsahujici jejich cesti
```
db.createView("category_complete", "category", 
[
{
   "$graphLookup": {
      "from": 'store_positions',
      "startWith": '$parent',
      "connectFromField": "parent",
      "connectToField": "_id",
      "as": 'path'
   }
},
{
    "$addFields": {
     "path_string": "$path.name"
    }
  }

])
```
