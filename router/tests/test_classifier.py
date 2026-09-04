from app.router.classifier import QueryClassifier


classifier = QueryClassifier()


queries = [
    "Highlight the water body in this image.",
    "Locate the roads.",
    "What is the dominant land cover?",
    "Describe this satellite image.",
    "What changed between these images?",
    "Find the built-up area.",
]


for query in queries:
    intent = classifier.classify(query)

    print("\nQUERY:")
    print(query)

    print("INTENT:")
    print(intent.model_dump())