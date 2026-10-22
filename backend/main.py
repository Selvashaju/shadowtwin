from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from engine import (
    load_twin,
    find_attack_paths,
    analyze_attack,
    get_twin_summary
)


app = FastAPI(
    title="ShadowTwin",
    description="Cyber Attack Simulation and Defence Analysis",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():

    return {
        "application": "ShadowTwin",
        "status": "online",
        "version": "1.0.0"
    }


@app.get("/twin")
def twin():

    return load_twin()


@app.get("/summary")
def summary():

    return get_twin_summary()


@app.get("/simulate")
def simulate(
    source: str = "u_ravi",
    target: str = "db_payroll"
):

    try:

        return analyze_attack(
            source,
            target
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc)
        )