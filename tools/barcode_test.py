import barcode
import bson
print(barcode.__file__)

a = bson.ObjectId()
b = str(a).lower()
c = str(a).upper()
d = str(int(str(a), 16))

print(">>>>>>>>>>>>> lower")
bc = barcode.Code128(b)
bc.save('/home/roman/barcode_128_lower.png')

print(">>>>>>>>>>>>> UPPER")
bc = barcode.Code128(c)
bc.save('/home/roman/barcode_128_upper.png')

print(">>>>>>>>>>>>> NUM")
bc = barcode.Code128(d)
bc.save('/home/roman/barcode_128_num.png')


print(">>>>>>>>>>>>>")
print(len(b), b)
print(len(c), c)
print(len(d), d)
