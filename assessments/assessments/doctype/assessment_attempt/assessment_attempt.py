# Copyright (c) 2026, nitin and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class AssessmentAttempt(Document):
	def validate(self):
		if self.is_new():
			return
		before_save = self.get_doc_before_save()
		if before_save and before_save.status == "Submitted":
			frappe.throw(_("This assessment has already been submitted and cannot be modified."))
