<template>
	<div class="flex flex-col gap-x-1 my-4">
		<div class="mb-2">
			<span class="text-ink-gray-9">{{ __('Time Remaining') }}: </span>
			<span
				class="font-semibold"
				:class="secondsLeft <= 60 ? 'text-ink-red-6' : 'text-ink-gray-9'"
			>
				{{ formatted }}
			</span>
		</div>
		<ProgressBar :progress="progress" />
	</div>
</template>
<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import ProgressBar from '@/components/ProgressBar.vue'

const props = defineProps({
	deadline: {
		// ISO datetime string, as returned by the backend's stage_deadline
		type: String,
		required: true,
	},
})

const emit = defineEmits(['expired'])

const secondsLeft = ref(0)
const totalSeconds = ref(1)
let interval = null

const tick = () => {
	const remaining = Math.floor(
		(new Date(props.deadline).getTime() - Date.now()) / 1000
	)
	secondsLeft.value = Math.max(remaining, 0)
	if (secondsLeft.value === 0) {
		clearInterval(interval)
		emit('expired')
	}
}

onMounted(() => {
	totalSeconds.value = Math.max(
		Math.floor((new Date(props.deadline).getTime() - Date.now()) / 1000),
		1
	)
	tick()
	interval = setInterval(tick, 1000)
})

onUnmounted(() => clearInterval(interval))

const progress = computed(() => (secondsLeft.value / totalSeconds.value) * 100)

const formatted = computed(() => {
	const hrs = Math.floor(secondsLeft.value / 3600)
		.toString()
		.padStart(2, '0')
	const mins = Math.floor((secondsLeft.value % 3600) / 60)
		.toString()
		.padStart(2, '0')
	const secs = (secondsLeft.value % 60).toString().padStart(2, '0')
	return hrs !== '00' ? `${hrs}:${mins}:${secs}` : `${mins}:${secs}`
})
</script>
