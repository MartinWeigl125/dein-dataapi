from fastapi import FastAPI
from app.api.endpoints import router as api_router

app = FastAPI(
    title="Heating Optimization API",
    description="Visualisierung und Analyse von Homematic Heizungsdaten",
    version="1.0.0"
)

app.include_router(api_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "API läuft"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)