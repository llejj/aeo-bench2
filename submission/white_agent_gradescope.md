# Final White Agent Submission - Questions

## Q6 Abstract (2 Points)

Briefly describe the task that your white agent is tested on.

---

## Q7 White Agent Implementation Details (6 Points)

### Q7.1 Agent Framework Design (3 Points)

Describe the architecture and overall decision-making framework of your white agent.

- What is the whole decision making pipeline?
- What input does the white agent take at each step and what is the output?
- What modules does your agent have (planner, executor, memory, verifier, tools, reflection, etc.)? How do they interact?
- Does the agent use chain-of-thought, tool-augmented reasoning, multi-step planning, action refinement, program synthesis, etc.?

---

### Q7.2 Data & Evaluation Design for the White Agent (3 Points)

- Describe the tasks and data that are used to test the white agent.
- Describe the evaluation metrics of the tasks.
- Describe the prompts used for the white agent.
- Describe some main results / performance on the white agent on the benchmark.

---

## Q8 White Agent Quality (12 Points)

### Q8.1 Performance Improvement Over the Existing Baselines (2 Points)

- What are the existing baselines or baselines you designed?
- How much better is your white agent than the existing baselines?
- What are the key designs/factors that make your white agent better than the baselines?

---

### Q8.2 Generalizability to Different Test Scenarios (2 Points)

- Does your agent generalize beyond the specific tasks it was tuned or designed for?
- Provide results from unseen tasks or held-out environment configurations, etc.

---

### Q8.3 Reasoning Quality / Interpretability (2 Points)

- Does your agent produce coherent, structured, and interpretable reasoning aligned with the task?
- Whether reasoning steps follow logically from observations.
- Provide 2–3 example trajectories showing high-quality reasoning and 1 trajectory showing failure + analysis.

---

### Q8.4 Efficiency & Resource Use (2 Points)

- Does the white agent solve tasks efficiently?
- Measure this by the number of steps or actions taken, token/compute efficiency, etc.

---

### Q8.5 Bias, Overfitting, or Contamination Checks (2 Points)

- Did you ensure that your white agent is not overfitting to specific test cases or leaking benchmark answers?
- If using external tools/data, demonstrate that answers are not leaked or contaminated.

---

### Q8.6 Impact, Reusability, and Documentation Quality (2 Points)

- Is your white agent implementation reusable, modular, and easy for others to understand?
- Provide clear README, instructions, and runnable examples in the GitHub repository submission.

---

## Q9 Demo Video (4 Points)

Your video should demonstrate the framework of your white agent, how your white agent completes the tasks, and its evaluation results.

**Your demo must include:**

### 1. Task Introduction
- What is the task?
- What does the environment look like?
- What actions can each agent take?

### 2. Agent Framework
- What is the overall framework design of the white agent?
- What is the decision making pipeline of the white agent?
- What are the inputs and outputs of the agent at each step?

### 3. Demonstration
- Show how your white agent completes different tasks on a few tasks.
- Clearly explain the input and output of the white agent at each step, and explain why the agent takes each action.
- Display the quantitative result of white agents on the benchmark (e.g., the accuracy).

**Tips:**
1. Keep it concise—5 minutes max.
2. You may record a screen-share walkthrough or an edited short demo.
3. Audio narration or captions are encouraged for clarity.

---

## Q10 Implementation and Documentation on GitHub (4 Points)

Provide the repo of your implementation and the branch.

**Please make it public, otherwise it will be counted as no submission.**

You need to have a README in the repo documenting how to use it:
- Document the commands for running the white agent to complete the task and reproduce the evaluation results on the white agent.

Make sure the white agent is runnable on AgentBeats.

---

## Q11 AgentBeats Assessment Link (4 Points)

Please provide the link to an assessment on AgentBeats platform in which your green agent evaluates your white agent.

---

## Q12 White Agent Report (10 Points)

The report should be 1-2 pages long.

### Required Sections:

**Abstract section:**
A brief overview/abstract of the important information of the whole report (e.g., what the task is, what the metric is, how the white agent is designed, what the main quantitative results are, how its performance is compared to baselines, etc.). Keep it brief by using 1-2 sentences for each bullet point.

**Benchmark section:**
A detailed introduction of the benchmark. This should include:
- A brief overview of the literature and related work on previous benchmarks on the same/similar task
- An overview of the benchmark you are using (what the benchmark evaluates, what the metric is, what kind of tasks or data are there in the benchmark, etc.)
- Details about the benchmark (e.g., what the inputs and outputs are for a white agent at each step, how the green agent evaluates a white agent, etc.)

**White agent framework section:**
A detailed description of the framework. It should cover all the points in Question 7(a).

**Experiment section:**
A detailed description of all the qualitative/quantitative results on the white agent. It should cover all the points in Question 8.