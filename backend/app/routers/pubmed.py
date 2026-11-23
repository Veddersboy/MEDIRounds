"""
API router for scraping and downloading PubMed Central (PMC) articles.
"""

from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.pubmed_scraper import (
    DEFAULT_OUTPUT_DIR,
    extract_all_pmcids,
    scrape_articles,
)

router = APIRouter(
    prefix="/api/v1/pubmed",
    tags=["PubMed"],
)


class PubMedFetchRequest(BaseModel):
    pmcids: list[str] = Field(..., min_length=1, description="List of PMCIDs or URLs")
    output_dir: str | None = Field(default=DEFAULT_OUTPUT_DIR, description="Directory to save JSON files")
    overwrite: bool = Field(default=False, description="Whether to overwrite existing JSON files")


class PubMedExtractRequest(BaseModel):
    text: str = Field(..., description="Raw pasted text containing PMCIDs or URLs")


@router.post("/extract")
async def extract_pmcids_endpoint(payload: PubMedExtractRequest) -> dict[str, Any]:
    ids = extract_all_pmcids(payload.text)
    return {"pmcids": ids, "count": len(ids)}


@router.post("/fetch")
async def fetch_articles_endpoint(payload: PubMedFetchRequest) -> dict[str, Any]:
    if not payload.pmcids:
        raise HTTPException(status_code=400, detail="No PMCIDs provided")

    output_directory = payload.output_dir or DEFAULT_OUTPUT_DIR
    results = await scrape_articles(
        pmcids=payload.pmcids,
        output_dir=output_directory,
        overwrite=payload.overwrite,
    )
    return results
