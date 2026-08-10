from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.api.routes import router
from src.backend.api.auth_routes import router as auth_router
from src.backend.api.staff_routes import router as staff_router
from src.backend.api.ticket_routes import router as ticket_router
from src.backend.api.promotions_routes import router as promotions_router


app = FastAPI(
    title="Vinpearl Multilingual Travel Agent",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(auth_router)
app.include_router(staff_router)
app.include_router(ticket_router)
app.include_router(promotions_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
