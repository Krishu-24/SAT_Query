from typing import Any


class ResponseIntegrator:

    def combine(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Combine outputs from multiple specialist agents
        into one standardized response.
        """

        successful_results = [
            result
            for result in results
            if result.get("status") == "success"
        ]

        failed_results = [
            result
            for result in results
            if result.get("status") != "success"
        ]

        return {
            "status": "success" if successful_results else "failed",
            "agent_count": len(results),
            "successful_agents": len(successful_results),
            "failed_agents": len(failed_results),
            "results": results,
        }