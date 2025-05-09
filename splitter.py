# graphrag_claimify/splitter.py
import re, nltk
nltk.download("punkt", quiet=True)


'''
Use nltk to analyze answer based on punctuation and language model to split paragraphs and sentences.

if lens < 5 and merged 
i.e. (dr,e.g,no so its too short to be useful alone and might be a mistaken split 
it merged this short sentence with previous one )

all other sentences are added normally. 

Reasoning: 
- Prevent tokenizer mistake from causing false sentence splits 
- Ensure sentence chuk make sense semantically
- Improve downstream LLM accuracy - especially for claimify stage like selection and disambiguation which assume well formed , meaningful sentences 
'''
def paragraph_split(text: str) -> list[str]:
    # two or more newlines → paragraph
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

def sentence_split(paragraph: str) -> list[str]:
    """NLTK split + merge sentences shorter than 5 chars."""
    sents, merged = nltk.sent_tokenize(paragraph), []
    for s in sents:
        if len(s) < 5 and merged:
            merged[-1] = merged[-1] + " " + s
        else:
            merged.append(s)
    return merged

def split_text(text: str) -> list[str]:
    sents = []
    for para in paragraph_split(text):
        sents.extend(sentence_split(para))
    return sents
