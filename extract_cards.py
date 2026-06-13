import pymupdf
import re
import json

RED = 0xff0000
PDF = "4. Xceltestings solution - Exam question and answer.pdf"

doc = pymupdf.open(PDF)

# Flatten every text span across all pages, preserving order.
spans = []
for page in doc:
    d = page.get_text("dict")
    for block in d["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                txt = span["text"]
                if not txt.strip():
                    continue
                spans.append((txt, span["color"]))

# Walk the span stream with a small state machine.
questions = []
current_chapter = None
i = 0
n = len(spans)

def is_question_start(s):
    return re.match(r'^\d+\)\s*$', s.strip()) is not None

def is_choice_letter(s, letter=None):
    if letter:
        return re.match(rf'^{letter}\.\s*$', s.strip()) is not None
    return re.match(r'^[a-f]\.\s*$', s.strip()) is not None

while i < n:
    txt, color = spans[i]
    stripped = txt.strip()

    if stripped.startswith("Chapter "):
        current_chapter = stripped
        i += 1
        continue

    m = re.match(r'^(\d+)\)\s*$', stripped)
    if not m:
        i += 1
        continue

    qnum = int(m.group(1))
    i += 1

    # Question text: everything up to first choice letter.
    qparts = []
    while i < n:
        t2, _ = spans[i]
        if is_choice_letter(t2, "a"):
            break
        if is_question_start(t2):  # malformed — abort
            break
        qparts.append(t2)
        i += 1
    question_text = " ".join(p.strip() for p in qparts if p.strip())

    # Collect up to 6 choices.
    choices = []
    for letter in "abcdef":
        if i >= n:
            break
        t2, c2 = spans[i]
        if not is_choice_letter(t2, letter):
            break
        letter_red = (c2 == RED)
        i += 1
        cparts = []
        text_red = False
        while i < n:
            t3, c3 = spans[i]
            ts = t3.strip()
            if is_choice_letter(ts) or is_question_start(ts) or ts.startswith("Chapter "):
                break
            if c3 == RED:
                text_red = True
            cparts.append(t3)
            i += 1
        choice_text = " ".join(p.strip() for p in cparts if p.strip())
        choices.append({
            "letter": letter,
            "text": choice_text,
            "is_answer": letter_red or text_red,
        })

    questions.append({
        "num": qnum,
        "chapter": current_chapter or "Uncategorized",
        "question": question_text,
        "choices": choices,
    })

# Quality report
total = len(questions)
no_answer = [q for q in questions if not any(c["is_answer"] for c in q["choices"])]
multi_answer = [q for q in questions if sum(1 for c in q["choices"] if c["is_answer"]) > 1]
no_choices = [q for q in questions if len(q["choices"]) < 2]

print(f"Total questions extracted: {total}")
print(f"Questions with NO answer marked: {len(no_answer)}")
print(f"Questions with MULTIPLE answers marked: {len(multi_answer)}")
print(f"Questions with <2 choices: {len(no_choices)}")
print(f"Chapters: {sorted({q['chapter'] for q in questions})}")

if no_answer:
    print("\nNo-answer samples:")
    for q in no_answer[:5]:
        print(f"  #{q['num']}: {q['question'][:80]}")

if multi_answer:
    print("\nMulti-answer samples:")
    for q in multi_answer[:5]:
        print(f"  #{q['num']}: {q['question'][:80]}")

with open("cards.json", "w") as f:
    json.dump(questions, f, indent=2, ensure_ascii=False)
print(f"\nWrote cards.json")
