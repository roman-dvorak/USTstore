mongodump --db USTintranet
echo "Dump done"
for file in dump/USTintranet/*.bson;
    do
    echo $file
    mongorestore --db USTdev --drop $file;
done
echo "Done restore"
rm dump -R
