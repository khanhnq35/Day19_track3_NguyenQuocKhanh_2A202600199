# Evaluation Comparison Table

> Metric format: `Correctness / Faithfulness / No-Hallucination`.

## Overall Summary

| Category | # Questions | Flat RAG Acc | GraphRAG Acc | HybridRAG Acc | Best System |
|---|---:|---:|---:|---:|---|
| single-hop | 10 | 0.80 | 0.90 | 1.00 | Hybrid |
| multi-hop | 10 | 0.30 | 0.91 | 0.80 | Graph |
| complex-reasoning | 10 | 0.49 | 0.64 | 0.80 | Hybrid |
| **Overall** | **30** | **0.53** | **0.82** | **0.87** | **Hybrid** |

## Single-hop Questions

| ID | Question | Flat RAG | GraphRAG | HybridRAG | Best |
|---:|---|---:|---:|---:|---|
| 1 | Where is OpenAI headquartered? | 1.00/1.00/1.00 | 1.00/1.00/1.00 | 1.00/1.00/1.00 | Draw |
| 2 | Who is the CEO of OpenAI? | 0.00/1.00/1.00 | 1.00/1.00/1.00 | 1.00/1.00/0.00 | Draw |
| 3 | Which company developed ChatGPT? | 1.00/1.00/1.00 | 1.00/1.00/1.00 | 1.00/1.00/1.00 | Draw |
| 4 | What is Google's parent company? | 1.00/1.00/1.00 | 1.00/1.00/1.00 | 1.00/1.00/1.00 | Draw |
| 5 | Who founded Google? | 1.00/1.00/1.00 | 1.00/1.00/1.00 | 1.00/1.00/0.00 | Draw |
| 6 | Who is the CEO of Alphabet Inc.? | 1.00/1.00/1.00 | 1.00/1.00/1.00 | 1.00/1.00/1.00 | Draw |
| 7 | Which AI models are Anthropic's flagship product line? | 1.00/1.00/1.00 | 1.00/1.00/1.00 | 1.00/1.00/1.00 | Draw |
| 8 | Who are the co-founders and leaders of Anthropic mentioned in the corpus? | 1.00/1.00/1.00 | 1.00/1.00/1.00 | 1.00/1.00/0.00 | Draw |
| 9 | Which company develops GPUs and CUDA and is headquartered in Santa Clara? | 0.00/1.00/1.00 | 0.00/1.00/1.00 | 1.00/1.00/1.00 | Hybrid |
| 10 | What architecture did Databricks develop for managing structured and unstructured data? | 1.00/1.00/1.00 | 1.00/1.00/1.00 | 1.00/1.00/1.00 | Draw |

## Multi-hop Questions

| ID | Question | Flat RAG | GraphRAG | HybridRAG | Best |
|---:|---|---:|---:|---:|---|
| 11 | Who is the CEO of the company that developed ChatGPT? | 0.00/1.00/1.00 | 1.00/1.00/1.00 | 1.00/1.00/1.00 | Draw |
| 12 | Which company invested more than $13 billion into the company that developed DALL-E? | 1.00/1.00/1.00 | 1.00/1.00/1.00 | 1.00/1.00/1.00 | Draw |
| 13 | What cloud platform does the developer of GPT use for computing resources? | 0.00/1.00/1.00 | 1.00/1.00/1.00 | 1.00/1.00/1.00 | Draw |
| 14 | Who is the CEO of the parent company of Google? | 0.00/1.00/1.00 | 1.00/1.00/1.00 | 1.00/1.00/1.00 | Draw |
| 15 | Which company acquired DeepMind, and which larger holding company does DeepMind serve as a subsidiary of? | 0.00/1.00/1.00 | 1.00/1.00/1.00 | 0.00/1.00/0.00 | Graph |
| 16 | Who founded the company that developed AlphaGo? | 0.00/1.00/1.00 | 1.00/1.00/1.00 | 1.00/1.00/1.00 | Draw |
| 17 | Which company invested in Anthropic and also provides the cloud service used by Anthropic as its primary cloud provider? | 1.00/1.00/1.00 | 0.10/1.00/1.00 | 1.00/1.00/1.00 | Draw |
| 18 | Which AI company founded by former OpenAI employees later partnered with Google for up to one million TPUs? | 0.00/0.00/1.00 | 1.00/1.00/1.00 | 0.00/1.00/1.00 | Graph |
| 19 | Which company founded by original creators of Apache Spark partnered with OpenAI in a $100 million deal? | 0.00/1.00/1.00 | 1.00/1.00/0.00 | 1.00/1.00/1.00 | Draw |
| 20 | Which company invested $16 million in Mistral AI, and what country is Mistral AI based in? | 1.00/1.00/1.00 | 1.00/1.00/1.00 | 1.00/1.00/1.00 | Draw |

## Complex Reasoning Questions

| ID | Question | Flat RAG | GraphRAG | HybridRAG | Best |
|---:|---|---:|---:|---:|---|
| 21 | Compare Microsoft's relationships with OpenAI and Mistral AI using investment amount and strategic role. | 1.00/1.00/0.00 | 1.00/0.00/1.00 | 1.00/1.00/1.00 | Draw |
| 22 | How do OpenAI and Anthropic differ in origin, leadership, and flagship products? | 0.30/1.00/1.00 | 0.50/1.00/1.00 | 0.00/1.00/1.00 | Graph |
| 23 | Trace the Alphabet AI chain from Google to DeepMind to Gemini, and explain why GraphRAG should retrieve this better than Flat RAG. | 0.50/1.00/1.00 | 0.00/1.00/1.00 | 0.00/1.00/1.00 | Flat |
| 24 | Which two founders of Google became associated with Alphabet after the restructuring, and what role did Sundar Pichai take across Google and Alphabet? | 0.00/1.00/1.00 | 0.00/1.00/1.00 | 1.00/1.00/1.00 | Hybrid |
| 25 | Compare Databricks' AI partnerships with Anthropic, Alphabet, and OpenAI by partner and purpose. | 1.00/1.00/1.00 | 1.00/1.00/1.00 | 1.00/1.00/1.00 | Draw |
| 26 | Compare Amazon's strategic relationships with Anthropic and OpenAI based on the corpus. | 1.00/1.00/1.00 | 1.00/1.00/1.00 | 1.00/1.00/1.00 | Draw |
| 27 | How do Nvidia and Google differ in their AI hardware roles according to the corpus? | 0.00/1.00/1.00 | 0.40/1.00/1.00 | 1.00/1.00/0.00 | Hybrid |
| 28 | Using the corpus, explain how OpenAI, Anthropic, Mistral AI, and Databricks show different AI company archetypes. | 0.10/1.00/1.00 | 1.00/0.90/1.00 | 1.00/1.00/0.90 | Draw |
| 29 | What chain connects Elon Musk to OpenAI and Tesla, and why can this question test hallucination risk? | 0.00/1.00/1.00 | 1.00/1.00/1.00 | 1.00/1.00/1.00 | Draw |
| 30 | Across OpenAI, Alphabet, Anthropic, Amazon, and Databricks, which relationships are ownership/control relationships versus product or platform partnerships? | 1.00/1.00/1.00 | 0.50/1.00/1.00 | 1.00/1.00/0.00 | Draw |
