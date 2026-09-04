from fastapi import FastAPI

from app.schemas.query import QueryRequest
from app.router.classifier import QueryClassifier
from app.router.router import QueryRouter
from app.integrator.response import ResponseIntegrator
from app.planner.planner import QueryPlanner
from app.executor.executor import QueryExecutor


app = FastAPI(
    title="SatQuery AI",
    description="Agentic remote-sensing query system",
    version="0.1.0",
)


planner = QueryPlanner()
router = QueryRouter()
integrator = ResponseIntegrator()
executor = QueryExecutor(router)


@app.get("/")
def root():
    return {
        "message": "SatQuery AI is running"
    }


@app.post("/query")
def process_query(request: QueryRequest):

    plan = planner.create_plan(
        request.query
    )

    results = executor.execute(
        plan,
        request.images
    )

    integrated_result = integrator.combine(
        results
    )

    return {
        "query": request.query,
        "plan": plan.model_dump(),
        "response": integrated_result,
        "images": request.images,
    }