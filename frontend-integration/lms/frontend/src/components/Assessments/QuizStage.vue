<template>
	<div class="space-y-4">
		<div
			v-for="(question, qidx) in questions"
			:key="question.quiz_question"
			class="border rounded-lg p-5"
		>
			<div class="flex justify-between">
				<div class="text-sm text-ink-gray-5">
					{{ __('Question {0}').format(qidx + 1) }} -
					{{ instructionFor(question) }}
				</div>
				<div class="text-ink-gray-9 text-sm-semibold">
					{{ question.marks }} {{ question.marks == 1 ? __('Mark') : __('Marks') }}
				</div>
			</div>
			<div
				class="text-ink-gray-9 font-semibold mt-2 leading-5"
				v-html="question.question"
			/>

			<div v-if="question.type === 'Choices'" class="mt-4 space-y-2">
				<label
					v-for="option in question.options"
					:key="option.idx"
					class="flex items-center bg-surface-gray-3 rounded-md p-3 w-full cursor-pointer"
				>
					<input
						:type="question.multiple ? 'checkbox' : 'radio'"
						:name="question.quiz_question"
						:checked="isSelected(question, option.text)"
						@change="toggleOption(question, option.text)"
					/>
					<span class="ms-2 text-ink-gray-9">{{ option.text }}</span>
				</label>
			</div>

			<FormControl
				v-else-if="question.type === 'User Input'"
				type="text"
				class="mt-4"
				:model-value="localAnswers[question.quiz_question] || ''"
				@update:model-value="(val) => setTextAnswer(question, val)"
			/>

			<FormControl
				v-else
				type="textarea"
				class="mt-4"
				:model-value="localAnswers[question.quiz_question] || ''"
				@update:model-value="(val) => setTextAnswer(question, val)"
			/>

			<div v-if="savingState[question.quiz_question]" class="text-xs text-ink-gray-5 mt-2">
				{{ savingState[question.quiz_question] }}
			</div>
		</div>

		<Button variant="solid" :loading="submitting" @click="submitStage">
			{{ __('Submit and Continue') }}
		</Button>
	</div>
</template>
<script setup>
import { Button, FormControl, call, toast } from 'frappe-ui'
import { reactive, ref } from 'vue'

const props = defineProps({
	attempt: {
		type: Object,
		required: true,
	},
	questions: {
		type: Array,
		required: true,
	},
	answers: {
		type: Object,
		required: true,
	},
})

const emit = defineEmits(['advance'])

// Selected option TEXTS per question (Choices type), matching how LMS's own
// verify_answer() compares by option text rather than an index/id.
const selectedByQuestion = reactive({})
const localAnswers = reactive({})
const savingState = reactive({})
const submitting = ref(false)
let saveTimers = {}

props.questions.forEach((q) => {
	const saved = props.answers[q.quiz_question]
	if (q.type === 'Choices') {
		try {
			selectedByQuestion[q.quiz_question] = saved ? JSON.parse(saved) : []
		} catch {
			selectedByQuestion[q.quiz_question] = []
		}
	} else {
		localAnswers[q.quiz_question] = saved || ''
	}
})

const instructionFor = (question) => {
	if (question.type === 'Choices') {
		return question.multiple
			? __('Choose all answers that apply')
			: __('Choose one answer')
	}
	return __('Type your answer')
}

const isSelected = (question, optionText) => {
	return (selectedByQuestion[question.quiz_question] || []).includes(optionText)
}

const toggleOption = (question, optionText) => {
	const key = question.quiz_question
	if (!question.multiple) {
		selectedByQuestion[key] = [optionText]
	} else {
		const current = selectedByQuestion[key] || []
		selectedByQuestion[key] = current.includes(optionText)
			? current.filter((v) => v !== optionText)
			: [...current, optionText]
	}
	scheduleSave(question, JSON.stringify(selectedByQuestion[key]))
}

const setTextAnswer = (question, value) => {
	localAnswers[question.quiz_question] = value
	scheduleSave(question, value)
}

const scheduleSave = (question, value) => {
	const key = question.quiz_question
	clearTimeout(saveTimers[key])
	savingState[key] = __('Saving...')
	saveTimers[key] = setTimeout(async () => {
		try {
			await call('assessments.assessments.api.save_answer', {
				attempt: props.attempt.name,
				stage_idx: props.attempt.current_stage_idx,
				question: key,
				answer_value: value,
			})
			savingState[key] = __('Saved')
		} catch (err) {
			savingState[key] = __('Failed to save')
			toast.error(err.messages?.[0] || err.message)
		}
	}, 600)
}

const submitStage = async () => {
	submitting.value = true
	try {
		await call('assessments.assessments.api.submit_stage', {
			attempt: props.attempt.name,
			stage_idx: props.attempt.current_stage_idx,
		})
		emit('advance')
	} catch (err) {
		toast.error(err.messages?.[0] || err.message)
	} finally {
		submitting.value = false
	}
}
</script>
