from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app(frontend_origin: str = "http://127.0.0.1:9999") -> FastAPI:
    app = FastAPI(title="CareerPilot", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_origin],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
