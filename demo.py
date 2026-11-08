import io
import os
from pathlib import Path
from typing import Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageOps

load_dotenv()
API_KEY = os.environ["PLANTNET_API_KEY"]

URL = "https://my-api.plantnet.org/v2/diseases/identify"
PLANT_URL = "https://my-api.plantnet.org/v2/identify/all"

app = FastAPI(title="Plant disease diagnosis")


@app.get("/", include_in_schema=False)
async def home():
    return FileResponse(Path(__file__).with_name("index.html"))


def shrink(raw: bytes) -> bytes:
    """Fix phone rotation, strip EXIF, shrink, re-encode as JPEG."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    img.thumbnail((1600, 1600))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=90)
    return out.getvalue()


@app.post("/identify")
async def identify(
    image: UploadFile = File(...),
    organ: Literal["auto", "leaf", "flower", "fruit", "bark"] = Form("auto"),
):
    try:
        jpg = shrink(await image.read())
    except Exception:
        raise HTTPException(400, "That file is not a readable image")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            disease_response = await client.post(
                URL,
                params={"api-key": API_KEY, "lang": "fr", "nb-results": 3},
                files={"images": ("photo.jpg", jpg, "image/jpeg")},
                data={"organs": [organ]},
            )
            plant_response = await client.post(
                PLANT_URL,
                params={"api-key": API_KEY, "lang": "fr", "nb-results": 1},
                files={"images": ("photo.jpg", jpg, "image/jpeg")},
                data={"organs": [organ]},
            )
    except httpx.HTTPError:
        raise HTTPException(504, "Could not reach Pl@ntNet (check the internet connection)")

    if disease_response.status_code == 429 or plant_response.status_code == 429:
        raise HTTPException(503, "Pl@ntNet API quota or credit limit reached")
    if disease_response.status_code == 404:
        return {"status": "not_a_plant", "results": []}
    if disease_response.status_code != 200:
        upstream_detail = disease_response.text.strip()[:500]
        detail = f"Pl@ntNet disease API error {disease_response.status_code}"
        if upstream_detail:
            detail = f"{detail}: {upstream_detail}"
        raise HTTPException(502, detail)
    if plant_response.status_code not in (200, 404):
        upstream_detail = plant_response.text.strip()[:500]
        detail = f"Pl@ntNet plant API error {plant_response.status_code}"
        if upstream_detail:
            detail = f"{detail}: {upstream_detail}"
        raise HTTPException(502, detail)

    try:
        body = disease_response.json()
        results = [
            {
                "eppo_code": disease["name"],
                "disease_name": disease["description"],
                "score": round(disease["score"], 3),
            }
            for disease in body.get("results", [])
        ]
        plant_body = plant_response.json() if plant_response.status_code == 200 else {}
        plant_matches = plant_body.get("results", [])
        plant = None
        if plant_matches:
            match = plant_matches[0]
            species = match["species"]
            plant = {
                "name": species["scientificNameWithoutAuthor"],
                "common_names": species.get("commonNames", [])[:3],
                "score": round(match["score"], 3),
            }
    except (AttributeError, KeyError, TypeError, ValueError):
        raise HTTPException(502, "Pl@ntNet returned an invalid identification response")

    return {
        "status": "ok" if results else "no_match",
        "plant": plant,
        "results": results,
        "remaining_quota": body.get(
            "remainingIdentificationRequests",
            plant_body.get("remainingIdentificationRequests"),
        ),
    }