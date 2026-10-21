---
trigger: always_on
description: Mandatory Graphify workflow for every task, modification, or structural change in the codebase.
---

## graphify Protocol

Use Graphify for EVERY task on this project: adding a feature, updating or changing code, working on something, or changing the structure.

### Before Touching Any Code:
1. If `graphify-out/graph.json` does not exist, run:
   ```bash
   graphify extract . --code-only
   ```
2. Read `graphify-out/GRAPH_REPORT.md` for the overall structure.
3. Run `graphify query "<the feature, function, class or file mentioned>"` to find the relevant code.
4. Run `graphify explain "<name>"` for anything you will change.
5. Run `graphify path "<A>" "<B>"` to check how two parts connect, and list every caller and dependent that the change could affect.
6. Do not grep or read many files first. Open only the files the graph points to.

### While Working:
- Follow the existing structure and naming shown in the graph.
- Reuse existing functions and modules before writing new ones.
- Update every file that depends on what you change.
- For structure changes (moving, renaming, splitting files), check all imports and references through the graph first.
- If the graph and the code disagree, trust the code and inform the user.

### After Finishing:
1. Run:
   ```bash
   graphify update .
   ```
   so the graph matches the new code.
2. Report which files were changed and which dependent parts were checked.
