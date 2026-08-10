<template>
	<div class="flex items-center gap-2 mb-6">
		<template v-for="(stage, idx) in stages" :key="idx">
			<div class="flex items-center gap-2">
				<div
					class="size-6 rounded-full flex items-center justify-center text-xs shrink-0"
					:class="dotClass(stage, idx)"
				>
					<span v-if="stage.status === 'Completed'" class="lucide-check size-3.5" />
					<span v-else>{{ idx + 1 }}</span>
				</div>
				<span
					class="text-sm hidden sm:inline"
					:class="idx === currentIdx ? 'text-ink-gray-9 font-medium' : 'text-ink-gray-5'"
				>
					{{ stage.title }}
				</span>
			</div>
			<div
				v-if="idx < stages.length - 1"
				class="flex-1 h-px"
				:class="idx < currentIdx ? 'bg-outline-gray-4' : 'bg-outline-gray-2'"
			/>
		</template>
	</div>
</template>
<script setup>
defineProps({
	stages: {
		type: Array,
		required: true,
	},
	currentIdx: {
		type: Number,
		required: true,
	},
})

const dotClass = (stage, idx) => {
	if (stage.status === 'Completed') return 'bg-surface-gray-10 text-ink-white'
	if (idx === undefined) return ''
	return stage.status === 'In Progress'
		? 'bg-surface-blue-3 text-ink-blue-6 ring-2 ring-outline-blue-2'
		: 'bg-surface-gray-3 text-ink-gray-5'
}
</script>
