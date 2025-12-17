# Final Green Agent Submission - Questions

## Q6 Abstract (2 Points)

Briefly describe the task that your green agent evaluates.

---

## Q7 Implementation Details (9 Points)

### Q7.1 Environment Design (3 Points)

Describe how the environment is set up. For example:
- What is the goal of the task?
- What is the state space of the task environment?
- What are the actions a white agent can take in the environment?
- How does the state of the environment change when a white agent takes different actions?
- When is the task accomplished or ended?

---

### Q7.2 Evaluation Design (3 Points)

Describe how your green agent evaluates white agents. For example:
- What are the metrics used to measure the white agent performance?
- How is the score for each metric evaluated?
- Please also provide a few examples of different trajectories taken by a white agent and how the green agent evaluates them.

---

### Q7.3 Data Design (3 Points)

Describe the data you prepared, including:
- The tasks and environments you prepared to test white agents in
- The test cases you prepared to test if the green agent can provide reasonable evaluation results on those test cases

---

## Q8 Green Agent Quality (20 Points)

### Q8.1 Quality Improvement Over The Original Benchmark / Goal & Novelty (3 Points)

**If you are working on an existing benchmark:**
- What analysis did you do to check whether there are any flaws in the original benchmark?
- Did you find any quality issue or flaw in the original benchmark? If yes, how did you correct those flaws?

**If you are working on a new benchmark:**
- Is your benchmark important, novel, and covering new capability space?
- Describe the literature on previous related benchmarks and explain why your benchmark is novel and covering new capability space.

---

### Q8.2 Faithfulness / Scope & Scale (3 Points)

**If you are working on an existing benchmark:**
- Does your implementation of the benchmark reproduce the results from the original benchmark?
- How did you ensure this?
- Please also provide quantitative results that show your re-implementation of the benchmark can reproduce the results in the original benchmark.
- Note that you will also need to provide commands to reproduce these results in the GitHub repo you submit.

**If you are working on a new benchmark:**
- Is the benchmark large and diverse enough to give reliable results?
- Explain why this is the case by providing some quantitative analysis.

---

### Q8.3 Coverage Expansion / Realism (2 Points)

**If you are working on an existing benchmark:**
- Does your implementation of the benchmark expand the coverage of the original benchmark (e.g., broader coverage of more tasks, more test cases, etc.)?
- Describe in detail how you expand the coverage.

**If you are working on a new benchmark:**
- Is the benchmark realistic, e.g., with real world workload, instead of toy or unrealistic settings?
- Explain why this is the case.

---

### Q8.4 Evaluator Quality (3 Points)

- Is the metric faithfully reflecting the capability of white agents in the task?
- Is the metric fine-grained enough to discriminate different white agents (e.g., instead of only evaluating the final outcome, we should also evaluate the process)?
- Is the evaluation consistent across different runs?
- Describe how you ensure these.
- Please also provide evaluation results of different white agents you tried, analyze if their performance are different, and provide some examples to explain what difference in their capabilities has caused this difference in performance.

---

### Q8.5 Validation (3 Points)

- Did you conduct manual or spot validations on the Green Agent outputs to ensure the evaluation results are accurate?
- How did you conduct the validations?
- Please provide 3 examples of different test cases and the evaluation results the green agent outputs for these test cases.
- Note that you will need to provide command that reproduce the evaluation results on your test cases in the GitHub repo you submit.

---

### Q8.6 Robustness (2 Points)

- Do your evaluation scripts and Green Agents run robustly on AgentBeats?
- How did you ensure that?

---

### Q8.7 Bias or Contamination (2 Points)

- Did you ensure if the evaluation is biased or contaminated?
- How did you ensure there is no bias or contamination?
- Provide quantitative analysis of whether your benchmark is biased or contaminated and whether you've fixed the problem.

---

### Q8.8 Impact (2 Points)

- Is the implementation reusable, well-documented, and presented clearly?
- How did you ensure that?
- Note that you will need to have a README of the documentation in your GitHub repo.

---

## Q9 Demo Video (5 Points)

Your video should demonstrate how your green agent evaluates outputs from white agents in your task.

**Your demo must include:**

1. **Task Introduction**
   - What is the task?
   - What does the environment look like?
   - What actions can each agent take?

2. **Demonstration**
   - Show how your green agent evaluates outputs from different White Agents on a few concrete examples.
   - Show whether your green agent evaluates reliably by showing its evaluation on some test cases with ground-truth evaluation results.
   - Clearly explain what the green agent is assessing (e.g., correctness, helpfulness, alignment, etc.).
   - Display the quantitative result of white agents on the benchmark (e.g., the accuracy).

**Tips:**
1. Keep it concise—5 minutes max.
2. You may record a screen-share walkthrough or an edited short demo.
3. Audio narration or captions are encouraged for clarity.