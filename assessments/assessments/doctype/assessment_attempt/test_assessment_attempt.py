# Copyright (c) 2026, nitin and Contributors
# See license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from assessments.assessments import api

STUDENT_EMAIL = "assessment_flow_student@example.com"
OTHER_STUDENT_EMAIL = "assessment_flow_other@example.com"
COURSE_TITLE = "Assessment Flow Test Course"


class TestAssessmentAttempt(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.student = cls._get_or_create_student(STUDENT_EMAIL, "Flow")
		cls.other_student = cls._get_or_create_student(OTHER_STUDENT_EMAIL, "Other")
		cls.course = cls._get_or_create_course()
		cls._enroll(cls.student, cls.course)

		cls.questions = cls._get_or_create_questions()
		cls.quiz = cls._get_or_create_quiz(cls.questions)
		cls.negative_marking_quiz = cls._get_or_create_negative_marking_quiz(cls.questions)

	def setUp(self):
		self.assessment = self._create_assessment(self.quiz)

	def _create_assessment(self, quiz):
		assessment = frappe.get_doc(
			{
				"doctype": "Assessment",
				"title": f"Assessment Flow Test {frappe.generate_hash()[:8]}",
				"course": self.course,
				"assessment_type": "Evaluation",
				"is_published": 1,
				"stages": [
					{"stage_type": "Declaration", "title": "Digital Declaration"},
					{
						"stage_type": "Quiz",
						"title": "MCQ Assessment",
						"quiz": quiz,
						"duration_minutes": 10,
					},
					{"stage_type": "Review", "title": "Final Review"},
				],
			}
		)
		assessment.insert(ignore_permissions=True)
		return assessment

	def tearDown(self):
		frappe.set_user("Administrator")

	@staticmethod
	def _get_or_create_student(email, first_name):
		if frappe.db.exists("User", email):
			return email
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name,
				"last_name": "Student",
				"send_welcome_email": 0,
				"roles": [{"role": "LMS Student"}],
			}
		)
		user.insert(ignore_permissions=True)
		return user.name

	@staticmethod
	def _get_or_create_course():
		existing = frappe.db.get_value("LMS Course", {"title": COURSE_TITLE}, "name")
		if existing:
			return existing
		course = frappe.get_doc(
			{
				"doctype": "LMS Course",
				"title": COURSE_TITLE,
				"short_introduction": "A course used by the assessment flow tests.",
				"description": "A course used by the assessment flow tests.",
				"instructors": [{"instructor": "Administrator"}],
				"published": 1,
			}
		)
		course.insert(ignore_permissions=True)
		return course.name

	@staticmethod
	def _enroll(student, course):
		if frappe.db.exists("LMS Enrollment", {"member": student, "course": course}):
			return
		frappe.get_doc({"doctype": "LMS Enrollment", "member": student, "course": course}).insert(
			ignore_permissions=True
		)

	@staticmethod
	def _get_or_create_questions():
		title = "Assessment Flow Test Question"
		existing = frappe.db.get_value("LMS Question", {"question": title}, "name")
		if existing:
			return [existing]
		question = frappe.get_doc(
			{
				"doctype": "LMS Question",
				"question": title,
				"type": "Choices",
				"option_1": "Correct Option",
				"is_correct_1": 1,
				"option_2": "Wrong Option",
			}
		)
		question.insert(ignore_permissions=True)
		return [question.name]

	@staticmethod
	def _get_or_create_quiz(question_names):
		title = "Assessment Flow Test Quiz"
		existing = frappe.db.get_value("LMS Quiz", {"title": title}, "name")
		if existing:
			return existing
		quiz = frappe.get_doc(
			{
				"doctype": "LMS Quiz",
				"title": title,
				"duration": "10",
				"passing_percentage": 60,
				"questions": [{"question": q, "marks": 1} for q in question_names],
			}
		)
		quiz.insert(ignore_permissions=True)
		return quiz.name

	@staticmethod
	def _get_or_create_negative_marking_quiz(question_names):
		title = "Assessment Flow Negative Marking Quiz"
		existing = frappe.db.get_value("LMS Quiz", {"title": title}, "name")
		if existing:
			return existing
		quiz = frappe.get_doc(
			{
				"doctype": "LMS Quiz",
				"title": title,
				"duration": "10",
				"passing_percentage": 60,
				"enable_negative_marking": 1,
				"marks_to_cut": 1,
				"questions": [{"question": q, "marks": 1} for q in question_names],
			}
		)
		quiz.insert(ignore_permissions=True)
		return quiz.name

	def _answer_all_correctly(self, attempt_name, stage_idx, questions):
		for q in questions:
			api.save_answer(attempt_name, stage_idx, q["quiz_question"], json.dumps(["Correct Option"]))

	def test_full_flow_progresses_and_scores_correctly(self):
		frappe.set_user(self.student)

		attempt = api.start_assessment(self.assessment.name)
		self.assertEqual(attempt.status, "In Progress")
		self.assertEqual(attempt.current_stage_idx, 0)
		self.assertEqual(attempt.stage_progress[0].stage_type, "Declaration")
		self.assertEqual(attempt.stage_progress[1].status, "Locked")

		# Starting again just returns the same in-progress attempt.
		same_attempt = api.start_assessment(self.assessment.name)
		self.assertEqual(same_attempt.name, attempt.name)

		with self.assertRaises(frappe.ValidationError):
			api.submit_declaration(attempt.name, "Test Student", "data:sig", declaration_accepted=0)

		# Both the signature and the candidate name are mandatory, not just
		# UI-disabled - the server must reject a blank one even if accepted=1.
		with self.assertRaises(frappe.ValidationError):
			api.submit_declaration(attempt.name, "Test Student", "", declaration_accepted=1)
		with self.assertRaises(frappe.ValidationError):
			api.submit_declaration(attempt.name, "   ", "data:image/png;base64,fake", declaration_accepted=1)

		attempt = api.submit_declaration(
			attempt.name, "Test Student", "data:image/png;base64,fake", declaration_accepted=1
		)
		self.assertEqual(attempt.current_stage_idx, 1)
		self.assertEqual(attempt.stage_progress[0].status, "Completed")
		self.assertEqual(attempt.stage_progress[1].status, "In Progress")

		state = api.get_attempt_state(attempt.name)
		self.assertEqual(len(state["current_stage_questions"]), len(self.questions))

		# Answering out of turn (wrong stage_idx) is rejected.
		with self.assertRaises(frappe.ValidationError):
			api.save_answer(
				attempt.name, 0, state["current_stage_questions"][0]["quiz_question"], json.dumps(["Correct Option"])
			)

		self._answer_all_correctly(attempt.name, attempt.current_stage_idx, state["current_stage_questions"])

		# Submitting the wrong stage is rejected.
		with self.assertRaises(frappe.ValidationError):
			api.submit_stage(attempt.name, 0)

		attempt = api.submit_stage(attempt.name, attempt.current_stage_idx)
		self.assertEqual(attempt.current_stage_idx, 2)
		self.assertEqual(attempt.stage_progress[2].stage_type, "Review")

		quiz_submission = frappe.get_doc(
			"LMS Quiz Submission", attempt.stage_progress[1].quiz_submission
		)
		self.assertEqual(quiz_submission.score, quiz_submission.score_out_of)
		self.assertEqual(quiz_submission.percentage, 100)

		attempt = api.submit_stage(attempt.name, attempt.current_stage_idx)
		self.assertEqual(attempt.status, "Submitted")
		self.assertIsNotNone(attempt.submitted_at)

		completion_status = api._get_completion_status(attempt)
		self.assertTrue(completion_status["passed"])
		self.assertEqual(completion_status["score"], quiz_submission.score)

	def test_quiz_score_of_zero_or_negative_does_not_break_submission(self):
		# A fully-wrong quiz (no negative marking) nets a score of exactly 0.
		frappe.set_user(self.student)
		attempt = api.start_assessment(self.assessment.name)
		attempt = api.submit_declaration(
			attempt.name, "Test Student", "data:image/png;base64,fake", declaration_accepted=1
		)
		state = api.get_attempt_state(attempt.name)
		for q in state["current_stage_questions"]:
			api.save_answer(attempt.name, attempt.current_stage_idx, q["quiz_question"], json.dumps(["Wrong Option"]))
		attempt = api.submit_stage(attempt.name, attempt.current_stage_idx)
		self.assertEqual(attempt.current_stage_idx, 2)
		quiz_submission = frappe.get_doc(
			"LMS Quiz Submission", attempt.stage_progress[1].quiz_submission
		)
		self.assertEqual(quiz_submission.score, 0)
		self.assertEqual(quiz_submission.percentage, 0)

		# Under negative marking, a fully-wrong quiz would net a negative raw
		# score; the persisted total must floor at 0 instead of crashing.
		neg_assessment = self._create_assessment(self.negative_marking_quiz)
		attempt2 = api.start_assessment(neg_assessment.name)
		attempt2 = api.submit_declaration(
			attempt2.name, "Test Student", "data:image/png;base64,fake", declaration_accepted=1
		)
		state2 = api.get_attempt_state(attempt2.name)
		for q in state2["current_stage_questions"]:
			api.save_answer(
				attempt2.name, attempt2.current_stage_idx, q["quiz_question"], json.dumps(["Wrong Option"])
			)
		attempt2 = api.submit_stage(attempt2.name, attempt2.current_stage_idx)
		self.assertEqual(attempt2.current_stage_idx, 2)
		neg_submission = frappe.get_doc(
			"LMS Quiz Submission", attempt2.stage_progress[1].quiz_submission
		)
		self.assertEqual(neg_submission.score, 0)
		self.assertEqual(neg_submission.percentage, 0)

	def test_other_users_are_denied_access(self):
		frappe.set_user(self.student)
		attempt = api.start_assessment(self.assessment.name)

		frappe.set_user(self.other_student)
		with self.assertRaises(frappe.ValidationError):
			api.get_attempt_state(attempt.name)
		with self.assertRaises(frappe.ValidationError):
			api.submit_declaration(attempt.name, "Someone Else", "data:sig", declaration_accepted=1)

	def test_locked_after_submission(self):
		frappe.set_user(self.student)
		attempt = api.start_assessment(self.assessment.name)
		attempt = api.submit_declaration(
			attempt.name, "Test Student", "data:image/png;base64,fake", declaration_accepted=1
		)
		state = api.get_attempt_state(attempt.name)
		self._answer_all_correctly(attempt.name, attempt.current_stage_idx, state["current_stage_questions"])
		attempt = api.submit_stage(attempt.name, attempt.current_stage_idx)
		attempt = api.submit_stage(attempt.name, attempt.current_stage_idx)
		self.assertEqual(attempt.status, "Submitted")

		with self.assertRaises(frappe.ValidationError):
			attempt.candidate_name = "Changed After Submission"
			attempt.save()

		answer = frappe.get_all("Assessment Answer", filters={"attempt": attempt.name}, limit=1)[0]
		answer_doc = frappe.get_doc("Assessment Answer", answer.name)
		answer_doc.answer_value = json.dumps(["Wrong Option"])
		with self.assertRaises(frappe.ValidationError):
			answer_doc.save()
