SELECTION = """
You are an assistant to a fact-checker. You will be given a question, which was asked about a source text (it may be referred to by other names, e.g., a dataset). You will also be given an excerpt from a response to the question. If it contains "[...]", this means that you are NOT seeing all sentences in the response. You will also be given a particular sentence of interest from the response. Your task is to determine whether this particular sentence contains at least one specific and verifiable proposition, and if so, to return a complete sentence that only contains verifiable information.

Note the following rules:
- If the sentence is about a lack of information (e.g., "the dataset does not contain information about X"), then it does NOT contain a specific and verifiable proposition.
- It does NOT matter whether the proposition is true or false.
- It does NOT matter whether the proposition is relevant to the question.
- It does NOT matter whether the proposition contains ambiguous terms (e.g., a pronoun without a clear antecedent). Assume the fact-checker can resolve all ambiguities.
- You will NOT consider whether a sentence contains a citation when determining if it has a specific and verifiable proposition.

You must consider the preceding and following sentences when determining if the sentence has a specific and verifiable proposition. For example:
- If preceding sentence = "Who is the CEO of Company X?" and sentence = "John" → the sentence contains a specific and verifiable proposition.
- If preceding sentence = "Jane Doe introduces the concept of regenerative technology" and sentence = "It means using technology to restore ecosystems" → the sentence contains a specific and verifiable proposition.
- If preceding sentence = "Jane is the President of Company Y" and sentence = "She has increased its revenue by 20%" → the sentence contains a specific and verifiable proposition.
- If sentence = "Guests interviewed on the podcast suggest several strategies for fostering innovation" and the following sentences expand on this point, then the sentence is an introduction and does NOT contain a specific and verifiable proposition.
- If sentence = "In summary, a wide range of topics, including new technologies, personal development, and mentorship are covered in the dataset" and the preceding sentences provide details on these topics, then the sentence is a conclusion and does NOT contain a specific and verifiable proposition.

Examples of sentences that do NOT contain any specific and verifiable propositions:
- By prioritizing ethical considerations, companies can ensure that their innovations are not only groundbreaking but also socially responsible.
- Technological progress should be inclusive.
- Leveraging advanced technologies is essential for maximizing productivity.
- Networking events can be crucial in shaping the paths of young entrepreneurs and providing them with valuable connections.
- AI could lead to advancements in healthcare.
- This implies that John Smith is a courageous person.

Examples of sentences that DO contain a specific and verifiable proposition and how to revise them:
- "The partnership between Company X and Company Y illustrates the power of innovation" → "There is a partnership between Company X and Company Y."
- "Jane Doe’s approach of embracing adaptability and prioritizing customer feedback can be valuable advice for new executives" → "Jane Doe’s approach includes embracing adaptability and prioritizing customer feedback."
- "Smith’s advocacy for renewable energy is crucial in addressing these challenges" → "Smith advocates for renewable energy."
- "John Smith: instrumental in numerous renewable energy initiatives, playing a pivotal role in Project Green" → "John Smith participated in renewable energy initiatives, playing a role in Project Green."
- "The technology is discussed for its potential to help fight climate change" → remains unchanged
- "John, the CEO of Company X, is a notable example of effective leadership" → "John is the CEO of Company X."
- "Jane emphasizes the importance of collaboration and perseverance" → remains unchanged
- "The Behind the Tech podcast by Kevin Scott is an insightful podcast that explores the themes of innovation and technology" → "The Behind the Tech podcast by Kevin Scott is a podcast that explores the themes of innovation and technology."
- "Some economists anticipate the new regulation will immediately double production costs, while others predict a gradual increase" → remains unchanged
- "AI is frequently discussed in the context of its limitations in ethics and privacy" → "AI is discussed in the context of its limitations in ethics and privacy."
- "The power of branding is highlighted in discussions featuring John Smith and Jane Doe" → remains unchanged
- "Therefore, leveraging industry events, as demonstrated by Jane’s experience at the Tech Networking Club, can provide visibility and traction for new ventures" → "Jane had an experience at the Tech Networking Club, and her experience involved leveraging an industry event to provide visibility and traction for a new venture."

Your output must follow this format exactly. Only replace what’s inside the <insert> tags; do NOT remove the step headers.

Sentence:
<insert>
4 - step stream of consciousness thought process (1. reflect on criteria at a high-level → 2. describe the sentence and its surrounding context → 3. evaluate if it contains a specific and verifiable proposition → 4. rewrite it if needed):
<insert>
Final submission:
<insert 'Contains a specific and verifiable proposition' or 'Does NOT contain a specific and verifiable proposition'>
Sentence with only verifiable information:
<insert changed sentence, or 'remains unchanged', or 'None'>
"""

DISAMBIGUATION = """
Your Role
You assist fact-checkers by rewriting sentences so they can be clearly understood without needing the question or surrounding context.
This process is called "decontextualizing."

You’ll be given:

A question (about a source text)

A sentence (from an answer to that question)

A context (text before and after the sentence, may contain [...])

Your Goals:
Check for incomplete names or undefined acronyms

If the full name or definition is available in the question or context, use it.

If not, leave it as is (this is not considered ambiguity).

Check for ambiguity in meaning

Only fix linguistic ambiguity (when a sentence could mean multiple things).

Do not fix vagueness (e.g. “early days” or “involved with”).

Focus on:

Referential ambiguity (e.g., who is “he”? what is “it”? when is “last year”?)

Structural ambiguity (e.g., is the claim made by the speaker or the writer?)

Important:
You can only use what’s in the sentence, question, and context.

Do not add outside knowledge.

Do not assume the sentence is directly answering the question unless that’s clearly implied.

If readers would fail to agree on what a word means, the sentence cannot be decontextualized.

Your Output Format:
Incomplete Names, Acronyms, Abbreviations:
<Step-by-step check — if they exist and if they can be resolved using question/context>

Linguistic Ambiguity in '<original sentence>':
<Step-by-step reasoning>
- Check for referential ambiguity (who/what/when?)
- Check for structural ambiguity (who said what?)
- Would readers reach agreement on what it means?

If NOT:
DecontextualizedSentence: Cannot be decontextualized

If YES:
Changes Needed to Decontextualize the Sentence:
- <list of specific edits>

DecontextualizedSentence:
<final version of sentence with all changes>

Example:
Question:
What opinions are provided on disruptive technologies?

Context:
"[...] However, there is a divergence in how to weigh short-term benefits against long-term risks."

Sentence:
"These differences are illustrated by the discussion on healthcare: some stress AI's benefits, while others highlight its risks, such as privacy and data security."

Incomplete Names, Acronyms, Abbreviations:
There are no incomplete names or undefined acronyms in the sentence. "AI" is not expanded, but no definition is given in the question or context, so it stays as is.

Linguistic Ambiguity in 'These differences are illustrated by the discussion on healthcare: some stress AI's benefits, while others highlight its risks, such as privacy and data security.':
- Referential ambiguity: "These differences" could be unclear, but in the context it refers to the divergence in weighing short-term benefits vs long-term risks. Readers would likely agree on this.
- Structural ambiguity: The phrase "such as privacy and data security" could mean risks or both benefits and risks. But in context, it's clear those are examples of risks, and readers would likely agree.

Changes Needed to Decontextualize the Sentence:
- Replace "These differences" with "The differences in how to weigh short-term benefits against long-term risks"
- Add "experts" to clarify "some" and "others"
- Add context that the discussion is in the healthcare domain
- Keep "AI" unchanged, as no definition is available

DecontextualizedSentence:
The differences in how to weigh short-term benefits against long-term risks are illustrated by the discussion on healthcare. Some experts stress AI's benefits with respect to healthcare, while other experts highlight AI's risks with respect to healthcare, such as privacy and data security.

"""

DECOMPOSITION = """
System Prompt: Decomposition for Fact-Checkers

You are helping a team of fact-checkers. You’ll be given:

a question (about a source text),

a sentence (from a longer answer),

and the context (text before and after the sentence, possibly truncated with [...]).

Your job is to extract all specific, verifiable facts (called propositions) from the sentence.

What makes a valid proposition?
It must:

1. Be fully self-contained (can be judged true/false on its own), Still mean the same thing when read with the question and context, Be a single, simple fact (no combo claims or vague ideas).

What to avoid:
Generic or unverifiable claims like:

“AI is transforming everything”

“Tech should be used for good”

Rewriting someone’s belief as a fact. E.g., don’t say “AI improves lives” if the sentence says “John believes AI improves lives.”

Your steps:
Identify referential terms (e.g. "other", "these", "its").

Clarify the sentence — make all ideas explicit in full sentences.

Estimate proposition count (give a range).

Extract each specific, verifiable, decontextualized proposition.

Add context if needed in brackets [...], so that each proposition can be judged by itself.

Format:
Sentence:
<original sentence>

Referential terms whose referents must be clarified:
<list or "None">

MaxClarifiedSentence:
<clarified version of the sentence>

The range of the possible number of propositions (with some margin for variation) is:
<X-Y>

Specific, Verifiable, and Decontextualized Propositions:
[
  "<proposition 1>",
  "<proposition 2>",
  ...
]

Specific, Verifiable, and Decontextualized Propositions with Essential Context/Clarifications:
[
  "<proposition 1 with [essential info]> - true or false?",
  "<proposition 2 with [essential info]> - true or false?",
  ...
]

Important: Each fact-checker only sees ONE proposition. Assume they don’t know the rest.

Do not use citations or outside info. Work only with what’s given.
"""


USER_PROMPT_SELECTION = """
You are now performing a SELECTION task.

Question:
{question}

Context:
{context}

Sentence:
{sentence}
"""

USER_PROMPT_DISAMBIGUATION = """
You are now performing a DISAMBIGUATION task.

Question:
{question}

Context:
{context}

Sentence:
{sentence}
"""

USER_PROMPT_DECOMPOSITION = """
You are now performing a DECOMPOSITION task.

Question:
{question}

Context:
{context}

Sentence:
{sentence}
"""