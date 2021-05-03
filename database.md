

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
{"$set": {"path": { "$reverseArray": "$path" }}},
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
{"$set": {"path": { "$reverseArray": "$path" }}},
{
    "$addFields": {
     "path_string": "$path.name"
    }
  }

])
```



View s počtem součástek v sáčcích. Každý dokument odpovídá jedné součástce a v poddokumentu jsou jednotlivé sáčky
```
db.createView("packets_count_complete", "stock", [
    {"$unwind": "$packets"},
    {"$lookup": { "from": 'store_positions', "localField":'packets.position', "foreignField": '_id', "as": 'packets.position'}},
    {"$lookup": { "from": 'stock_operation', "localField":'packets._id', "foreignField": 'pid', "as": 'packets.operations'}},
    {"$project": {"packets":1} },
    {"$addFields": {
            "packet_count":  {"$sum": "$packets.operations.count"},
            "packet_reserv":  {"$sum": "$packets.operations.reserv"},
            "packet_ordered":  {"$sum": "$packets.operations.ordered"},
            "packet_price": {
            "$function":
                {
                    "body": function(prices, counts) {
                     let total_counts = Array.sum(counts);
                     var tmp_count = total_counts;
                     var total_price = 0;

                     var c = counts.reverse();
                     var p = prices.reverse();

                     for(i in c){
                         if(c[i] > 0){
                             if(c[i] < tmp_count){
                                 total_price += (c[i]*p[i]);
                                 tmp_count -= c[i]
                              }
                              else{
                                 total_price += (tmp_count*p[i]);
                                 tmp_count = 0;
                              }
                          }

                      }
                      return total_price;
                    },
                    "args": ["$packets.operations.unit_price", "$packets.operations.count"], "lang": "js"
                }
            }
        }
    },
  {
    "$group": {
      _id: "$_id",
      packets: { $push: "$$ROOT" }
    }
  }, 
   {"$addFields": {
        "component_count":  {"$sum": "$packets.packet_count"},
        "component_reserv":  {"$sum": "$packets.packet_reserv"},
        "component_ordered":  {"$sum": "$packets.packet_ordered"},
        "component_price":  {"$sum": "$packets.packet_price"}
    }
}
])
```
