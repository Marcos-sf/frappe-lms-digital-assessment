<template>
	<header
		class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-base px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs :items="[{ label: __('Assessments') }]" />
	</header>
	<div class="mx-4 sm:mx-10 py-8">
		<h1 class="text-2xl font-semibold text-ink-gray-9 mb-6">
			{{ __('Assessments') }}
		</h1>

		<div v-if="assessments.loading" class="flex justify-center py-12">
			<LoadingIndicator class="size-5 text-ink-gray-5" />
		</div>

		<div
			v-else-if="!assessments.data?.length"
			class="border rounded-lg text-center p-16 text-ink-gray-6"
		>
			{{ __('No assessments are available for your enrolled courses yet.') }}
		</div>

		<div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
			<div
				v-for="item in assessments.data"
				:key="item.assessment"
				class="border rounded-lg p-5 flex flex-col gap-3"
			>
				<div class="flex items-center justify-between">
					<Badge :theme="typeTheme(item.assessment_type)">
						{{ item.assessment_type }}
					</Badge>
					<Badge :theme="statusTheme(item.status)">
						{{ item.status }}
					</Badge>
				</div>
				<div class="text-base font-semibold text-ink-gray-9">
					{{ item.title }}
				</div>
				<div
					v-if="item.status === 'In Progress' && item.stage_deadline"
					class="text-sm"
					:class="timeRemaining(item.stage_deadline) === __('Time up') ? 'text-ink-red-6' : 'text-ink-gray-6'"
				>
					{{ __('Time Remaining') }}: {{ timeRemaining(item.stage_deadline) }}
				</div>
				<div v-if="item.completion_status" class="flex items-center gap-2 text-sm">
					<Badge :theme="item.completion_status.passed ? 'green' : 'red'">
						{{ item.completion_status.passed ? __('Pass') : __('Fail') }}
					</Badge>
					<span class="text-ink-gray-6">
						{{ item.completion_status.score }} / {{ item.completion_status.score_out_of }}
					</span>
				</div>
				<Button
					class="mt-auto"
					:variant="item.status === 'Submitted' ? 'subtle' : 'solid'"
					@click="openAssessment(item)"
				>
					{{ actionLabel(item.status) }}
				</Button>
			</div>
		</div>
	</div>
</template>
<script setup>
import { Badge, Breadcrumbs, Button, createResource, LoadingIndicator } from 'frappe-ui'
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const assessments = createResource({
	url: 'assessments.assessments.api.get_dashboard_assessments',
	auto: true,
})

// Ticks once a second so every card's "Time Remaining" stays live without
// each card running its own interval.
const now = ref(Date.now())
let interval = null
onMounted(() => (interval = setInterval(() => (now.value = Date.now()), 1000)))
onUnmounted(() => clearInterval(interval))

const timeRemaining = (deadline) => {
	const seconds = Math.max(Math.floor((new Date(deadline).getTime() - now.value) / 1000), 0)
	if (seconds === 0) return __('Time up')
	const mins = Math.floor(seconds / 60)
		.toString()
		.padStart(2, '0')
	const secs = (seconds % 60).toString().padStart(2, '0')
	return `${mins}:${secs}`
}

const statusTheme = (status) => {
	if (status === 'Submitted') return 'green'
	if (status === 'In Progress') return 'orange'
	return 'gray'
}

const typeTheme = (type) => {
	if (type === 'Certification') return 'blue'
	if (type === 'Evaluation') return 'purple'
	return 'gray'
}

const actionLabel = (status) => {
	if (status === 'Submitted') return __('View Result')
	if (status === 'In Progress') return __('Resume')
	return __('Start')
}

const openAssessment = (item) => {
	router.push({
		name: 'AssessmentTaking',
		params: { assessmentID: item.assessment },
	})
}
</script>
