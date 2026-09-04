from app.schemas import query

from app.schemas.intent import QueryIntent, QueryPlan
from app.schemas.task import TaskType



class QueryClassifier:

    def classify(self, query: str) -> QueryIntent:
        query_lower = query.lower().strip().rstrip(".")

        # --------------------------------------------------
        # Grounding
        # --------------------------------------------------

        grounding_keywords = [
            "highlight",
            "locate",
            "find",
            "show",
            "mark",
            "outline",
            "where is",
            "where are",
            "identify the region",
            "bounding box",
        ]

        if any(keyword in query_lower for keyword in grounding_keywords):
            target = self._extract_target(query_lower)

            return QueryIntent(
                task_id="task_1",
                task=TaskType.GROUNDING,
                target=target,
                requires_spatial_evidence=True,
                requires_segmentation=(
                    "highlight" in query_lower
                    or "segment" in query_lower
                ),
                confidence=0.95,
            )

        # --------------------------------------------------
        # Change Detection
        # --------------------------------------------------

        change_keywords = [
            "what changed",
            "changes between",
            "change between",
            "difference between",
            "detect changes",
        ]

        if any(keyword in query_lower for keyword in change_keywords):
            return QueryIntent(
                task_id="task_1",
                task=TaskType.CHANGE_DETECTION,
                target="changes",
                
                requires_spatial_evidence=True,
                requires_comparison=True,
                confidence=0.95,
            )

        # --------------------------------------------------
        # Captioning
        # --------------------------------------------------

        caption_keywords = [
            "describe",
            "caption",
            "give me a description",
            "generate a description",
        ]

        if any(keyword in query_lower for keyword in caption_keywords):
            return QueryIntent(
                task_id="task_1",
                task=TaskType.CAPTIONING,
                target="image",
            
                confidence=0.95,
            )

        # --------------------------------------------------
        # VQA
        # --------------------------------------------------

        question_keywords = [
            "what",
            "which",
            "how many",
            "is there",
            "are there",
            "does",
            "do",
        ]

        if any(
            query_lower.startswith(keyword)
            for keyword in question_keywords
        ):
            return QueryIntent(
                task_id="task_1",
                task=TaskType.VQA,
                target=query,
                
                confidence=0.80,
            )

        # --------------------------------------------------
        # Unknown
        # --------------------------------------------------

        return QueryIntent(
            task_id="task_1",
            task=TaskType.UNKNOWN,
            target=query,
            
            confidence=0.30,
        )

    # ------------------------------------------------------
    # Target Extraction
    # ------------------------------------------------------

    def _extract_target(self, query: str) -> str:
        """
        Extract the object/region being referred to.

        This is intentionally simple for the first prototype.
        We will replace it with a more robust query parser later.
        """

        prefixes = [
            "highlight the ",
            "highlight ",
            "locate the ",
            "locate ",
            "find the ",
            "find ",
            "show the ",
            "show ",
            "mark the ",
            "mark ",
            "outline the ",
            "outline ",
        ]

        target = query

        for prefix in prefixes:
            if query.startswith(prefix):
                target = query[len(prefix):]
                break

        # Remove common trailing phrases.
        trailing_phrases = [
            " in this image",
            " in the image",
            " on this image",
            " on the image",
            " from this image",
            " from the image",
        ]

        for phrase in trailing_phrases:
            if target.endswith(phrase):
                target = target[:-len(phrase)]
                break

        return target.rstrip(" .")

    def create_plan(self, query: str) -> QueryPlan:
        """
        Convert a natural-language query into one or more tasks.

        The first version uses simple conjunction detection.
        The existing classify() method remains responsible for
        identifying each individual task.
        """

        query_lower = query.lower().strip()

        # Separators that may indicate multiple requests.
        separators = [
            " and ",
            " also ",
            " then ",
            " as well as ",
            " along with ",
        ]

        parts = [query]

        for separator in separators:
            if separator in query_lower:
                split_index = query_lower.find(separator)

                left = query[:split_index].strip()
                right = query[
                    split_index + len(separator):
                ].strip()

                if left and right:
                    parts = [left, right]
                    break

        tasks = []

        for part in parts:
            intent = self.classify(part)

            if intent.task != TaskType.UNKNOWN:
                tasks.append(intent)

        # If nothing could be classified, preserve the original query.
        if not tasks:
            tasks.append(self.classify(query))

        return QueryPlan(tasks=tasks)