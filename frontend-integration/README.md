# Frontend Integration

The Vue SPA for this feature lives inside the **LMS** app's own frontend (`apps/lms/frontend`) rather than as a
separate bundle, so it shares LMS's existing components, stores, and design tokens (see the main README's
"Design Decisions" section for why).

Applying it to a fresh `lms` checkout takes two steps:

1. **Copy the new files** into the matching paths under `apps/lms/frontend/`:

   ```bash
   cp -r frontend-integration/lms/frontend/src/pages/Assessments apps/lms/frontend/src/pages/
   cp -r frontend-integration/lms/frontend/src/components/Assessments apps/lms/frontend/src/components/
   cp frontend-integration/lms/frontend/src/components/AssessmentTimer.vue apps/lms/frontend/src/components/
   cp frontend-integration/lms/frontend/src/components/SignaturePad.vue apps/lms/frontend/src/components/
   ```

2. **Apply the patch** for the three existing LMS files that were edited (adds the `/assessments` routes to
   `router.js`, the sidebar entry to `utils/index.js`, and the component type declarations):

   ```bash
   cd apps/lms
   git apply ../assessments/frontend-integration/lms-frontend-integration.patch
   ```

   If the patch fails to apply cleanly against a newer LMS version, the diff is small enough to apply by hand —
   open `lms-frontend-integration.patch` and mirror the three hunks.

3. Rebuild the frontend as usual:

   ```bash
   cd apps/lms/frontend
   yarn build
   ```

This has been tested end-to-end against LMS v2.61.0.
