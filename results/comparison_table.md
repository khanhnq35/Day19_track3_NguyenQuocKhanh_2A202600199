# Evaluation Comparison Table

| ID | Category | Question | Flat RAG (C/F/H) | GraphRAG (C/F/H) | Win |
|---|---|---|---|---|---|
| 1 | single-hop | Where is OpenAI headquartered? | 1.0/1.0/1.0 | 0.0/1.0/1.0 | Flat |
| 2 | single-hop | Who is the CEO of OpenAI? | 1.0/1.0/1.0 | 1.0/1.0/1.0 | Draw |
| 3 | single-hop | What products did OpenAI develop? | 1.0/1.0/1.0 | 0.0/1.0/1.0 | Flat |
| 4 | single-hop | When was OpenAI founded? | 1.0/1.0/1.0 | 0.0/1.0/1.0 | Flat |
| 5 | single-hop | Who founded Google? | 1.0/1.0/1.0 | 1.0/0.5/0.0 | Draw |
| 6 | single-hop | What cloud platform does OpenAI use? | 1.0/1.0/1.0 | 0.0/1.0/1.0 | Flat |
| 7 | single-hop | Who is the CEO of Alphabet Inc.? | 1.0/1.0/1.0 | 0.0/1.0/1.0 | Flat |
| 8 | single-hop | What is the parent company of Google? | 1.0/1.0/1.0 | 1.0/1.0/1.0 | Draw |
| 9 | single-hop | What quantum computing chip did Alphabet unveil in December 2024? | 1.0/1.0/1.0 | 0.0/1.0/1.0 | Flat |
| 10 | single-hop | Who are the co-founders of OpenAI besides Sam Altman? | 1.0/1.0/1.0 | 1.0/1.0/1.0 | Draw |
| 11 | multi-hop | Who is the CEO of the company that developed ChatGPT? | 1.0/1.0/1.0 | 1.0/1.0/1.0 | Draw |
| 12 | multi-hop | Which company invested over $13 billion into the developer of DALL-E? | 0.0/0.0/1.0 | 0.0/1.0/0.8 | Draw |
| 13 | multi-hop | What cloud platform does the company that created GPT models use for its infrastructure? | 0.0/1.0/1.0 | 0.0/1.0/1.0 | Draw |
| 14 | multi-hop | Who is the CEO of the parent company that owns Google? | 1.0/1.0/1.0 | 1.0/1.0/1.0 | Draw |
| 15 | multi-hop | Which company co-founded by Elon Musk is headquartered in San Francisco and works on AI safety? | 0.0/0.9/1.0 | 1.0/0.8/0.7 | Graph |
| 16 | multi-hop | What percentage stake does Microsoft hold in the company that released ChatGPT after its 2025 restructuring? | 1.0/1.0/1.0 | 0.0/1.0/0.0 | Flat |
| 17 | multi-hop | Who replaced Larry Page as CEO of Google after the Alphabet restructuring in 2015? | 1.0/1.0/1.0 | 1.0/0.7/1.0 | Draw |
| 18 | complex-reasoning | Trace the chain: Who is the CEO of the company that developed the AI model powering Microsoft Copilot, and what cloud platform does that company use? | 1.0/1.0/1.0 | 0.0/1.0/1.0 | Flat |
| 19 | complex-reasoning | OpenAI was co-founded by someone who also leads SpaceX and Tesla. This person also invested in OpenAI. Who is this person, and what was OpenAI's stated mission regarding AGI? | 1.0/1.0/1.0 | 0.5/1.0/1.0 | Flat |
| 20 | complex-reasoning | Alphabet and OpenAI both have connections to Microsoft. How does Microsoft's relationship differ with each of these two companies? | 0.0/1.0/1.0 | 0.2/1.0/1.0 | Graph |

## Summary Statistics (Accuracy)

| Category | Flat RAG Avg | GraphRAG Avg | Delta (G-F) |
|---|---|---|---|
| single-hop | 1.00 | 0.40 | -0.60 |
| multi-hop | 0.57 | 0.57 | +0.00 |
| complex-reasoning | 0.67 | 0.23 | -0.43 |
