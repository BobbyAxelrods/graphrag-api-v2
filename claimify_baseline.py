# graphrag_claimify/claimify.py
from openai import AsyncOpenAI
from typing import List
from prompt import SELECTION, DISAMBIGUATION, DECOMPOSITION
from splitter import split_text
import os 
'''
use open ai 
in the context window previous p and futur f to include the context of the sentence

_ask is the function that will call the open ai api and return the response

_context_window is the function that will take the sentence and the index of the sentence and return the context window of the sentence
** select previous sentences and f future sentences - skip the current sentence since its being analyzed now  
** Join them together into single string sorroudning twext 

Example: 
sents = [
  "John joined the company in 2010.",
  "He became CEO in 2015.",
  "Under his leadership, revenue doubled.",
  "This attracted new investors.",
  "The company went public in 2020."
]
You're analyzing idx = 2 (3rd sentence: "Under his leadership, revenue doubled."), and p = 1, f = 1.

"He became CEO in 2015. This attracted new investors."
It skipped the main sentence (index 2), and included:

1 sentence before (idx-1)

1 sentence after (idx+1)


Reasoning :
- resolve pronouns he she they -> disambiguation
- understand time references like last year, recently, in the early days 
- Know what this or these refer to 
- Avoid extracting misleading claims out of structural intro / concolusion sentences


Then _context_window() will give you:

_extract is the function that will take the question and the answer and return the claims
-- sentences splitting : split the full answer into sentences list 
-- loop thru sentences list and extract context window around it 

-- Running thru multi stages prompts 
--- selection prompts : Run selection prompts to determine if the sentence is a claim or not, if not skip to next sentence
--- disambiguation prompts : Runs the Disambiguation prompt to resolve pronouns, acronyms, etc., if ambiguous skip to next sentence
--- decomposition prompts  : Decompose the claim into smaller, verifiable parts o extract multiple atomic, verifiable claims.
Skips if nothing is extractable.




'''
api_key = os.getenv("GRAPHRAG_API_KEY")
if not api_key:
    raise EnvironmentError("Missing GRAPHRAG_API_KEY environment variable.")

client = AsyncOpenAI(api_key=api_key)

class Claimify:
    def __init__(self, model: str = "gpt-4o-mini", p: int = 2, f: int = 2):
        self.model, self.p, self.f = model, p, f

    async def _ask(self, prompt: str) -> str:
        res = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return res.choices[0].message.content.strip()

    def _context_window(self, sents: List[str], idx: int) -> str:
        start, end = max(0, idx - self.p), min(len(sents), idx + self.f + 1)
        return " ".join(sents[start:idx] + sents[idx + 1 : end])

    async def extract(self, question: str, answer: str) -> List[str]:
        sents, claims = split_text(answer), []

        for i, sent in enumerate(sents):
            ctx = self._context_window(sents, i)

            # 1 Selection
            sel = await self._ask(SELECTION.format(sentence=sent, context=ctx, question=question))
            if sel == "NO_VERIFIABLE_CLAIMS":
                continue

            # 2 Disambiguation
            dis = await self._ask(DISAMBIGUATION.format(sentence=sel, context=ctx, question=question))
            if dis == "CANNOT_BE_DISAMBIGUATED":
                continue

            # 3 Decomposition
            dec = await self._ask(DECOMPOSITION.format(sentence=dis, context=ctx))
            if dec == "NO_CLAIMS":
                continue
            claims.extend([c.strip() for c in dec.splitlines() if c.strip()])

        return claims
