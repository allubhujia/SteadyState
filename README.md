# SteadyState

**Physiological speech markers: telling cognitive change apart from daily fatigue.**

Speech often gets simpler before cognitive decline is clinically obvious: vocabulary narrows, pauses get longer and syntax gets less complex. Sleep loss, stress and fatigue cause the same kinds of drop for a while. SteadyState uses continuous wearable data (sleep, HRV, circadian phase) to separate **temporary physiological states** from **lasting cognitive traits**.

## Research Question

> Can wearable physiology distinguish transient states from durable cognitive traits?

## Pipeline

1. **Extract**: linguistic and acoustic-timing features via vLLM
2. **Adapt**: parameter-efficient adapters for each participant, to model personal baselines
3. **Retrieve**: graph-linked retrieval of past utterances for longitudinal context
4. **Elicit**: a contextual bandit that picks prompts based on physiological state
5. **Decompose**: a state-space model that splits each observation into trait, state and noise

## Status

Early stage. Code and setup instructions are in progress.

## Author

Veer Vikram Saxena
Vasu Jindal
Sharvari Mahurkar
