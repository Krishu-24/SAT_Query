from app.router.classifier import QueryClassifier


classifier = QueryClassifier()


queries = [
    "Highlight the water body in this image.",
    "Locate the roads.",
    "What is the dominant land cover?",
    "Describe this satellite image.",
    "What changed between these images?",
    "Find the water bodies and describe the image.",
    "Locate the roads and describe this satellite image.",
]


for query in queries:

    plan = classifier.create_plan(query)

    print("\nQUERY:")
    print(query)

    print("PLAN:")
    print(plan.model_dump())