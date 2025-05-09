from openai import AsyncOpenAI
from typing import List
from prompt import (
    SELECTION, DISAMBIGUATION, DECOMPOSITION,
    USER_PROMPT_SELECTION, USER_PROMPT_DISAMBIGUATION, USER_PROMPT_DECOMPOSITION
)
from splitter import split_text
import os

api_key = os.getenv("GRAPHRAG_API_KEY")
if not api_key:
    raise EnvironmentError("Missing GRAPHRAG_API_KEY environment variable.")

client = AsyncOpenAI(api_key=api_key)

class Claimify:
    def __init__(self, model: str = "gpt-4o-mini", p: int = 2, f: int = 2):
        self.model = model
        self.p = p
        self.f = f

    async def _ask(self, system_prompt: str, user_prompt: str) -> str:
        res = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,
        )
        return res.choices[0].message.content.strip()

    def _context_window(self, sents: List[str], idx: int) -> str:
        start, end = max(0, idx - self.p), min(len(sents), idx + self.f + 1)
        return " ".join(sents[start:idx] + sents[idx + 1:end])

    async def extract(self, question: str, answer: str) -> List[str]:
        sents = split_text(answer)
        claims = []

        for i, sent in enumerate(sents):
            ctx = self._context_window(sents, i)

            # 1. Selection
            sel_prompt = USER_PROMPT_SELECTION.format(sentence=sent, context=ctx, question=question)
            sel_result = await self._ask(SELECTION, sel_prompt)
            if "Does NOT contain" in sel_result:
                continue

            # 2. Disambiguation
            dis_prompt = USER_PROMPT_DISAMBIGUATION.format(sentence=sent, context=ctx, question=question)
            dis_result = await self._ask(DISAMBIGUATION, dis_prompt)
            if "Cannot be decontextualized" in dis_result:
                continue

            # Extract Decontextualized Sentence
            decontext_line = next(
                (l for l in reversed(dis_result.splitlines()) if l.startswith("DecontextualizedSentence:")),
                None
            )
            if not decontext_line or "Cannot" in decontext_line:
                continue
            decontext_sent = decontext_line.replace("DecontextualizedSentence:", "").strip()

            # 3. Decomposition
            dec_prompt = USER_PROMPT_DECOMPOSITION.format(sentence=decontext_sent, context=ctx, question=question)
            dec_result = await self._ask(DECOMPOSITION, dec_prompt)

            # Extract claims from output
            inside_block = False
            for line in dec_result.splitlines():
                if line.strip().startswith("["):
                    inside_block = True
                    continue
                if line.strip().startswith("]"):
                    break
                if inside_block and line.strip().startswith('"'):
                    claims.append(line.strip().strip('",'))

        return claims
