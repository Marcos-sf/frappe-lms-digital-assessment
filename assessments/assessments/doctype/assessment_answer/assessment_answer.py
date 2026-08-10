# Copyright (c) 2026, nitin and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class AssessmentAnswer(Document):
	def validate(self):
		attempt_status = frappe.db.get_value("Assessment Attempt", self.attempt, "status")
		if attempt_status == "Submitted":
			frappe.throw(_("This assessment has already been submitted and cannot be modified."))
