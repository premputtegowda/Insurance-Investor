import json
import re

import pymupdf

PDF = "/Users/premputtegowda/Downloads/1. 150 Exam - Q & A 2025.pdf"
RTL_OVERRIDE = "‭"
POP_DIR = "‬"


def clean(s):
    return s.replace(RTL_OVERRIDE, "").replace(POP_DIR, "").strip()


def yellow_rects(page):
    rects = []
    for d in page.get_drawings():
        f = d.get("fill")
        if f and len(f) >= 3 and f[0] > 0.9 and f[1] > 0.9 and f[2] < 0.3:
            rects.append(d["rect"])
    return rects


def overlaps_yellow(bbox, rects, min_ratio=0.3):
    """True if bbox overlap with any yellow rect covers at least min_ratio of the span area.
    Guards against floating-point precision causing tiny overlaps with the row above/below."""
    x0, y0, x1, y1 = bbox
    span_area = max(0.1, (x1 - x0) * (y1 - y0))
    for r in rects:
        ox0 = max(x0, r.x0)
        oy0 = max(y0, r.y0)
        ox1 = min(x1, r.x1)
        oy1 = min(y1, r.y1)
        if ox1 > ox0 and oy1 > oy0:
            if (ox1 - ox0) * (oy1 - oy0) / span_area >= min_ratio:
                return True
    return False


# Split a span containing mid-text choice markers like " a. " or ". b. " into sub-spans.
# Sub-bboxes are estimated by linear interpolation across the original bbox width.
def split_span(text, bbox, rects):
    matches = []
    for m in re.finditer(r"(?<=[\s.,;:])([a-d]\.(?:\s|$))", text):
        if m.start() == 0:
            continue
        matches.append(m.start())
    if not matches:
        return [(text, overlaps_yellow(bbox, rects))]

    cut_points = [0] + matches + [len(text)]
    x0, y0, x1, y1 = bbox
    width = x1 - x0
    total = len(text) if len(text) > 0 else 1
    out = []
    for a, b in zip(cut_points, cut_points[1:]):
        sub = text[a:b].strip()
        if not sub:
            continue
        sx0 = x0 + (a / total) * width
        sx1 = x0 + (b / total) * width
        sub_bbox = (sx0, y0, sx1, y1)
        out.append((sub, overlaps_yellow(sub_bbox, rects)))
    return out


def is_section(t):
    return "Exam Cram" in t or "Exam Update" in t


def is_choice_start(t, letter=None):
    if letter:
        return re.match(rf"^{letter}\.(\s|$)", t) is not None
    return re.match(r"^[a-f]\.(\s|$)", t) is not None


def is_question_start(t):
    return re.match(r"^\d+\.(\s|$)", t) is not None and not is_choice_start(t)


# Flatten spans (post-split) across all pages.
doc = pymupdf.open(PDF)
spans = []
for page in doc:
    rects = yellow_rects(page)
    d = page.get_text("dict")
    for block in d["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                t = clean(span["text"])
                if not t:
                    continue
                for sub_t, sub_y in split_span(t, span["bbox"], rects):
                    spans.append((sub_t, sub_y))

# Walk spans.
questions = []
current_chapter = None
i = 0
n = len(spans)

while i < n:
    t, _ = spans[i]

    if is_section(t):
        current_chapter = t
        i += 1
        continue

    if current_chapter is None:
        i += 1
        continue

    m = re.match(r"^(\d+)\.\s*(.*)", t)
    if m and not is_choice_start(t):
        section_num = int(m.group(1))
        rest = m.group(2).strip()
        i += 1
        q_parts = [rest] if rest else []
        while i < n:
            t2, _ = spans[i]
            if is_choice_start(t2, "a") or is_section(t2) or is_question_start(t2):
                break
            q_parts.append(t2)
            i += 1
        question_text = " ".join(p for p in q_parts if p).strip()

        choices = []
        for letter in "abcdef":
            if i >= n:
                break
            t2, y2 = spans[i]
            cm = re.match(rf"^{letter}\.\s*(.*)$", t2)
            if not cm:
                break
            letter_yellow = y2
            rest = cm.group(1).strip()
            i += 1
            c_parts = [rest] if rest else []
            text_yellow = letter_yellow
            while i < n:
                t3, y3 = spans[i]
                if is_choice_start(t3) or is_section(t3) or is_question_start(t3):
                    break
                if y3:
                    text_yellow = True
                c_parts.append(t3)
                i += 1
            choices.append({
                "letter": letter,
                "text": " ".join(p for p in c_parts if p).strip(),
                "is_answer": text_yellow,
            })

        questions.append({
            "section_num": section_num,
            "chapter": current_chapter,
            "question": question_text,
            "choices": choices,
        })
    else:
        i += 1

# Stats
print(f"Extracted {len(questions)} questions")
by_chap = {}
for q in questions:
    by_chap.setdefault(q["chapter"], 0)
    by_chap[q["chapter"]] += 1
for chap, count in by_chap.items():
    print(f"  {chap}: {count}")

no_ans = [q for q in questions if not any(c["is_answer"] for c in q["choices"])]
multi_ans = [q for q in questions if sum(1 for c in q["choices"] if c["is_answer"]) > 1]
few_choices = [q for q in questions if len(q["choices"]) < 2]
print(f"No answer marked: {len(no_ans)}")
print(f"Multi-answer: {len(multi_ans)}")
print(f"<2 choices: {len(few_choices)}")

if few_choices:
    print("\n<2 choices samples:")
    for q in few_choices[:5]:
        print(f'  Sec#{q["section_num"]} ({q["chapter"][:30]}): {q["question"][:90]}')
        for c in q["choices"]:
            ans = " [ANS]" if c["is_answer"] else ""
            print(f'    {c["letter"]}. {c["text"][:60]}{ans}')

if no_ans:
    print("\nNo-answer samples:")
    for q in no_ans[:5]:
        print(f'  Sec#{q["section_num"]} ({q["chapter"][:30]}): {q["question"][:80]}')

# Merge.
with open("cards.json") as f:
    existing = json.load(f)
# Strip any previously-appended cards (num >= 682) so we re-merge cleanly.
existing = [c for c in existing if c["num"] <= 681]
next_num = 682
print(f"\nStarting global num: {next_num}")

for q in questions:
    q["num"] = next_num
    next_num += 1
    del q["section_num"]

merged = existing + questions
with open("cards.json", "w") as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)
print(f"Wrote cards.json: {len(existing)} existing + {len(questions)} new = {len(merged)} total")
