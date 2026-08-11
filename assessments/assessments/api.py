import json

import frappe
from frappe.utils import add_to_date, cint, now_datetime
from lms.lms.doctype.lms_quiz.lms_quiz import check_input_answers, verify_answer


@frappe.whitelist()
def start_assessment(assessment):
	user = frappe.session.user
	assessment_doc = frappe.get_doc("Assessment", assessment)

	if not assessment_doc.is_published:
		frappe.throw("This assessment is not available.")

	is_enrolled = frappe.db.exists(
		"LMS Enrollment", {"member": user, "course": assessment_doc.course}
	)
	if not is_enrolled:
		frappe.throw("You are not enrolled in the course for this assessment.")

	existing = frappe.db.get_value(
		"Assessment Attempt", {"assessment": assessment, "member": user}, "name"
	)
	if existing:
		return frappe.get_doc("Assessment Attempt", existing)

	attempt = frappe.get_doc(
		{
			"doctype": "Assessment Attempt",
			"assessment": assessment,
			"member": user,
			"status": "In Progress",
			"current_stage_idx": 0,
			"started_at": now_datetime(),
		}
	)

	for idx, stage in enumerate(assessment_doc.stages):
		attempt.append(
			"stage_progress",
			{
				"stage_type": stage.stage_type,
				"title": stage.title,
				"status": "In Progress" if idx == 0 else "Locked",
				"started_at": now_datetime() if idx == 0 else None,
			},
		)

	attempt.insert()
	return attempt


@frappe.whitelist()
def save_answer(attempt, stage_idx, question, answer_value):
	user = frappe.session.user
	attempt_doc = frappe.get_doc("Assessment Attempt", attempt)

	if attempt_doc.member != user:
		frappe.throw("Not permitted.")

	if attempt_doc.status != "In Progress":
		frappe.throw("This assessment is not in progress.")

	if _auto_submit_if_expired(attempt_doc):
		frappe.throw("Time is up for this stage. It has moved on automatically.")

	if cint(stage_idx) != cint(attempt_doc.current_stage_idx):
		frappe.throw("You can only answer questions in the current stage.")

	existing = frappe.db.get_value(
		"Assessment Answer",
		{"attempt": attempt, "stage_idx": stage_idx, "question": question},
		"name",
	)

	if existing:
		answer_doc = frappe.get_doc("Assessment Answer", existing)
		answer_doc.answer_value = answer_value
		answer_doc.last_saved_at = now_datetime()
		answer_doc.save()
	else:
		answer_doc = frappe.get_doc(
			{
				"doctype": "Assessment Answer",
				"attempt": attempt,
				"stage_idx": stage_idx,
				"question": question,
				"answer_value": answer_value,
				"last_saved_at": now_datetime(),
			}
		)
		answer_doc.insert()

	return {"saved": True, "last_saved_at": answer_doc.last_saved_at}


@frappe.whitelist()
def submit_declaration(attempt, candidate_name, signature, declaration_accepted):
	user = frappe.session.user
	attempt_doc = frappe.get_doc("Assessment Attempt", attempt)

	if attempt_doc.member != user:
		frappe.throw("Not permitted.")
	if attempt_doc.status != "In Progress":
		frappe.throw("This assessment is not in progress.")

	if _auto_submit_if_expired(attempt_doc):
		frappe.throw("Time is up for this stage. It has moved on automatically.")

	current_stage = attempt_doc.stage_progress[attempt_doc.current_stage_idx]
	if current_stage.stage_type != "Declaration":
		frappe.throw("Current stage is not a declaration.")

	if not cint(declaration_accepted):
		frappe.throw("You must accept the declaration to continue.")

	if not (candidate_name or "").strip():
		frappe.throw("Candidate name is required.")

	if not (signature or "").strip():
		frappe.throw("Signature is required.")

	attempt_doc.candidate_name = candidate_name
	attempt_doc.signature = signature
	attempt_doc.declaration_accepted = 1
	attempt_doc.declaration_datetime = now_datetime()

	return _advance_to_next_stage(attempt_doc)


@frappe.whitelist()
def submit_stage(attempt, stage_idx):
	user = frappe.session.user
	attempt_doc = frappe.get_doc("Assessment Attempt", attempt)

	if attempt_doc.member != user:
		frappe.throw("Not permitted.")
	if attempt_doc.status != "In Progress":
		frappe.throw("This assessment is not in progress.")

	if _auto_submit_if_expired(attempt_doc):
		frappe.throw("Time is up for this stage. It has moved on automatically.")

	if cint(stage_idx) != cint(attempt_doc.current_stage_idx):
		frappe.throw("This is not your current stage.")

	current_stage = attempt_doc.stage_progress[attempt_doc.current_stage_idx]

	if current_stage.stage_type == "Quiz":
		_finalize_quiz_stage(attempt_doc, stage_idx, current_stage)

	return _advance_to_next_stage(attempt_doc)


def _advance_to_next_stage(attempt_doc):
	current_idx = attempt_doc.current_stage_idx
	current_row = attempt_doc.stage_progress[current_idx]
	current_row.status = "Completed"
	current_row.completed_at = now_datetime()

	next_idx = current_idx + 1
	if next_idx < len(attempt_doc.stage_progress):
		next_row = attempt_doc.stage_progress[next_idx]
		next_row.status = "In Progress"
		next_row.started_at = now_datetime()
		attempt_doc.current_stage_idx = next_idx
	else:
		attempt_doc.status = "Submitted"
		attempt_doc.submitted_at = now_datetime()

	attempt_doc.save()
	return attempt_doc


def _get_stage_duration_minutes(assessment_doc, stage_idx):
	stage_def = assessment_doc.stages[cint(stage_idx)]
	if stage_def.duration_minutes:
		return cint(stage_def.duration_minutes)
	if stage_def.stage_type == "Quiz" and stage_def.quiz:
		quiz_duration = frappe.db.get_value("LMS Quiz", stage_def.quiz, "duration")
		return cint(quiz_duration) if quiz_duration else None
	return None


def _get_completion_status(attempt_doc):
	"""Aggregate score/pass-fail across every graded Quiz stage of a Submitted attempt."""
	quiz_submission_names = [
		row.quiz_submission for row in attempt_doc.stage_progress if row.quiz_submission
	]
	if not quiz_submission_names:
		return None

	score = 0
	score_out_of = 0
	passed = True
	for name in quiz_submission_names:
		submission = frappe.db.get_value(
			"LMS Quiz Submission",
			name,
			["score", "score_out_of", "percentage", "passing_percentage"],
			as_dict=True,
		)
		if not submission:
			continue
		score += submission.score or 0
		score_out_of += submission.score_out_of or 0
		if (submission.percentage or 0) < (submission.passing_percentage or 0):
			passed = False

	return {"score": score, "score_out_of": score_out_of, "passed": passed}


def _auto_submit_if_expired(attempt_doc):
	if attempt_doc.status != "In Progress":
		return False

	current_idx = attempt_doc.current_stage_idx
	current_row = attempt_doc.stage_progress[current_idx]
	if not current_row.started_at:
		return False

	assessment_doc = frappe.get_doc("Assessment", attempt_doc.assessment)
	duration = _get_stage_duration_minutes(assessment_doc, current_idx)
	if not duration:
		return False

	deadline = add_to_date(current_row.started_at, minutes=duration, as_datetime=True)
	if now_datetime() < deadline:
		return False

	if current_row.stage_type == "Quiz":
		_finalize_quiz_stage(attempt_doc, current_idx, current_row)

	_advance_to_next_stage(attempt_doc)
	return True


@frappe.whitelist()
def get_attempt_state(attempt):
	user = frappe.session.user
	attempt_doc = frappe.get_doc("Assessment Attempt", attempt)

	if attempt_doc.member != user:
		frappe.throw("Not permitted.")

	_auto_submit_if_expired(attempt_doc)

	stage_deadline = None
	current_stage_questions = []

	if attempt_doc.status == "In Progress":
		current_idx = attempt_doc.current_stage_idx
		current_row = attempt_doc.stage_progress[current_idx]
		assessment_doc = frappe.get_doc("Assessment", attempt_doc.assessment)

		duration = _get_stage_duration_minutes(assessment_doc, current_idx)
		if duration and current_row.started_at:
			stage_deadline = add_to_date(
				current_row.started_at, minutes=duration, as_datetime=True
			)

		if current_row.stage_type == "Quiz":
			current_stage_questions = _get_stage_questions(assessment_doc, current_idx)

	answers = frappe.get_all(
		"Assessment Answer",
		filters={"attempt": attempt, "stage_idx": attempt_doc.current_stage_idx},
		fields=["question", "answer_value"],
	)

	return {
		"attempt": attempt_doc.as_dict(),
		"answers": {a.question: a.answer_value for a in answers},
		"stage_deadline": stage_deadline,
		"current_stage_questions": current_stage_questions,
	}


def _get_stage_questions(assessment_doc, stage_idx):
	stage_def = assessment_doc.stages[cint(stage_idx)]
	quiz = frappe.get_doc("LMS Quiz", stage_def.quiz)

	questions = []
	for quiz_question in quiz.questions:
		question_doc = frappe.get_doc("LMS Question", quiz_question.question)
		options = [
			{"idx": i, "text": question_doc.get(f"option_{i}")}
			for i in range(1, 11)
			if question_doc.get(f"option_{i}")
		]
		questions.append(
			{
				"quiz_question": quiz_question.name,
				"question": question_doc.question,
				"type": question_doc.type,
				"marks": quiz_question.marks,
				"multiple": question_doc.multiple,
				"options": options,
			}
		)
	return questions


def _finalize_quiz_stage(attempt_doc, stage_idx, progress_row):
	assessment_doc = frappe.get_doc("Assessment", attempt_doc.assessment)
	stage_def = assessment_doc.stages[cint(stage_idx)]
	quiz = frappe.get_doc("LMS Quiz", stage_def.quiz)

	answers = frappe.get_all(
		"Assessment Answer",
		filters={"attempt": attempt_doc.name, "stage_idx": stage_idx},
		fields=["question", "answer_value"],
	)
	answer_by_quiz_question = {a.question: a.answer_value for a in answers}

	quiz_submission = frappe.get_doc(
		{
			"doctype": "LMS Quiz Submission",
			"quiz": quiz.name,
			"member": attempt_doc.member,
			"score_out_of": quiz.total_marks,
			"passing_percentage": quiz.passing_percentage,
		}
	)

	graded = []

	for quiz_question in quiz.questions:
		question_doc = frappe.get_doc("LMS Question", quiz_question.question)
		submitted_value = answer_by_quiz_question.get(quiz_question.name, "")

		if question_doc.type == "Choices":
			selected = _parse_choice_answer(submitted_value)
			is_correct = bool(verify_answer(question_doc.name, selected))
		elif question_doc.type == "User Input":
			is_correct = bool(check_input_answers(question_doc.name, submitted_value or ""))
		else:
			# Open Ended questions have no stored correct answer in LMS -
			# they need a human evaluator. Left at 0 marks until graded.
			is_correct = False

		if is_correct:
			marks = quiz_question.marks
		elif quiz.enable_negative_marking and question_doc.type != "Open Ended":
			marks = -quiz.marks_to_cut
		else:
			marks = 0

		graded.append(
			{
				"question": question_doc.question,
				"question_name": question_doc.name,
				"answer": submitted_value,
				"marks": marks,
				"marks_out_of": quiz_question.marks,
				"is_correct": is_correct,
			}
		)

	# LMS Quiz Submission's `score` is always the sum of these result rows, and its
	# `percentage` is mandatory and non-negative. Negative marking can legitimately
	# drive the raw total below zero, so once every row is graded, soften just
	# enough of the negative rows (against the true final total, not interleaved
	# with it) to floor the quiz's total score at 0 without changing its sign or
	# any row's grading outcome.
	deficit = -sum(row["marks"] for row in graded)
	if deficit > 0:
		for row in graded:
			if deficit <= 0:
				break
			if row["marks"] < 0:
				offset = min(deficit, -row["marks"])
				row["marks"] += offset
				deficit -= offset

	total_marks = 0
	for row in graded:
		total_marks += row["marks"]
		quiz_submission.append("result", row)

	# LMS's own percentage calculation only runs when the score is truthy, so a
	# 0 score (an all-Open-Ended quiz awaiting grading, or a fully floored
	# negative-marking result) would otherwise leave the mandatory `percentage`
	# field unset and fail this insert.
	quiz_submission.percentage = (total_marks / quiz.total_marks) * 100 if quiz.total_marks else 0

	quiz_submission.insert(ignore_permissions=True)
	progress_row.quiz_submission = quiz_submission.name


def _parse_choice_answer(answer_value):
	if not answer_value:
		return []
	try:
		parsed = json.loads(answer_value)
	except (TypeError, ValueError):
		return [answer_value]
	return parsed if isinstance(parsed, list) else [parsed]


@frappe.whitelist()
def get_dashboard_assessments():
	user = frappe.session.user

	enrolled_courses = frappe.get_all(
		"LMS Enrollment", filters={"member": user}, pluck="course"
	)
	if not enrolled_courses:
		return []

	assessments = frappe.get_all(
		"Assessment",
		filters={"course": ["in", enrolled_courses], "is_published": 1},
		fields=["name", "title", "assessment_type", "course"],
	)

	result = []
	for assessment in assessments:
		attempt_name = frappe.db.get_value(
			"Assessment Attempt", {"assessment": assessment.name, "member": user}, "name"
		)
		stage_deadline = None
		completion_status = None
		attempt = None

		if attempt_name:
			attempt_doc = frappe.get_doc("Assessment Attempt", attempt_name)
			_auto_submit_if_expired(attempt_doc)
			attempt = attempt_doc

			if attempt_doc.status == "In Progress":
				current_idx = attempt_doc.current_stage_idx
				current_row = attempt_doc.stage_progress[current_idx]
				assessment_doc = frappe.get_cached_doc("Assessment", attempt_doc.assessment)
				duration = _get_stage_duration_minutes(assessment_doc, current_idx)
				if duration and current_row.started_at:
					stage_deadline = add_to_date(
						current_row.started_at, minutes=duration, as_datetime=True
					)
			elif attempt_doc.status == "Submitted":
				completion_status = _get_completion_status(attempt_doc)

		result.append(
			{
				"assessment": assessment.name,
				"title": assessment.title,
				"assessment_type": assessment.assessment_type,
				"course": assessment.course,
				"status": attempt.status if attempt else "Not Started",
				"attempt": attempt.name if attempt else None,
				"started_at": attempt.started_at if attempt else None,
				"submitted_at": attempt.submitted_at if attempt else None,
				"stage_deadline": stage_deadline,
				"completion_status": completion_status,
			}
		)

	return result
