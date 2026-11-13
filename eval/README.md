# Evals (docs/DESIGN.md §2.7)

Work backwards from the use cases (docs/PRD.md §2). Each question has a checked answer where one exists.

**Three arms:**
1. `raw`: an agent with only web search and the sources' raw dumps. This is the bar to beat.
2. `graph-default`: the agent's way in, starting from default dossiers.
3. `graph-picked`: the agent's way in, starting from dossiers picked for the question.

**Metrics:**
- right or wrong, where an answer exists;
- a judged side-by-side, where it doesn't;
- navigation: calls, dossiers read, tokens, wasted reads.

**Every new source is evaluated when it's added:** the trail's yield (new people and facts per person researched), and the answers.

`questions.example.yaml` shows the format. Real questions go in `questions.yaml`. Fake answers never go in that file.
