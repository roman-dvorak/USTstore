for file in *.bson;
    do mongorestore -d USTdev --drop $file;
done

