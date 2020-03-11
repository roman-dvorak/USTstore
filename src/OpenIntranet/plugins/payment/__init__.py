
from .. import BaseHandler

#TODO parental classes from 'BaseHelper'
class PaymentHelper():

	def new_payment(self, accountTo = None, bankCode = None, amount = 0, currency = 'CZK', ks = None, vs=None, ss=None, messageForRecipient=None, comment=None):
		"""
			Metoda vytvoří nový požadavek na platbu. Přidá ji do seznamu k uploadu do banky. Má mnoho vstupních parametrů, které zatím nejsou povinné
		"""

		payment = {}

		payment['accountTo'] = accountTo
		payment['bankCode'] = bankCode
		payment['amount'] = amount
		payment['currency'] = currency
		payment['ks'] = ks
		payment['vs'] = vs
		payment['ss'] = ss
		payment['messageForRecipient'] = messageForRecipient
		payment['comment'] = comment
		payment['ready_to_upload'] = False
		payment['done'] = False

		out = self.mdb.payment.insertOne(payment)
		print(out)

	def update_payment(self, id, edits):
		pass

	def get_payment_details(self, id):
		pass

	def get_payment_overview(self, page=0, limit=50):
		out = self.mdb.payment.find({})
		return list(out)

	def markt_to_upload(self, id, value=True):
		pass

	def upload_payment(self):
		pass

