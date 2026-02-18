"""Data source toggle and health check endpoints."""

from fastapi import APIRouter

from options_pricer.bloomberg import BloombergClient, MockBloombergClient

from ..dependencies import get_client, set_client
from ..schemas import HealthResponse, SourceResponse

router = APIRouter()


@router.post("/toggle-source", response_model=SourceResponse)
def toggle_source():
    """Switch between Bloomberg API and Mock Data."""
    client = get_client()

    if isinstance(client, MockBloombergClient):
        new_client = BloombergClient()
        if new_client.connect():
            set_client(new_client)
            return SourceResponse(source="Bloomberg API", connected=True)
        return SourceResponse(
            source="Mock Data",
            connected=False,
            error="Bloomberg API connection failed. Check Terminal is running.",
        )
    else:
        client.disconnect()
        set_client(MockBloombergClient())
        return SourceResponse(source="Mock Data", connected=True)


@router.get("/health", response_model=HealthResponse)
def health():
    """Return current data source and connection status."""
    client = get_client()
    return HealthResponse(source=client.source_name, status="ok")
