---
name: wiki-search
description: Retrieve relevant past knowledge. Filters out deprecated practices and follows migration trails.
---
# When to use
- BEFORE writing any code
- At the start of every task

# Input
- current task description

# Action
1. **Search via CLI (Recommended)**:
   - Run: `llm-wiki search "<task keywords>"`
   - This handles QMD semantic search with an automatic fallback to grep if QMD is unavailable.

2. **Follow Links**:
   - Use bidirectional links `[[link]]` and tags to navigate related knowledge.

3. **Deprecation Check (CRITICAL)**:
   - For every page found, check the YAML `status`.
   - If `status: deprecated`, follow `superseded_by`.

# Output Format
- Warnings: Include any anti-patterns or recently deprecated methods found.
- Recommendations: Based ONLY on `status: active` patterns.
- Related cases: [[case-link]]
