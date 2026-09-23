from parser import parse_questions


questions = parse_questions("questions.txt")


print("=" * 80)
print(f"TOTAL PARSED QUESTIONS: {len(questions)}")
print("=" * 80)


for q in questions:

    print(f"\nQuestion {q['number']}:")
    print(q["question"])

    print(f"OPTIONS ({len(q['options'])}):")

    for index, option in enumerate(q["options"]):
        letter = chr(ord("A") + index)
        print(f"  {letter}. {option}")


print("\n" + "=" * 80)

print("OPTION COUNT DISTRIBUTION")

distribution = {}

for q in questions:
    count = len(q["options"])
    distribution[count] = distribution.get(count, 0) + 1

for count in sorted(distribution):
    print(f"{count} options: {distribution[count]} questions")