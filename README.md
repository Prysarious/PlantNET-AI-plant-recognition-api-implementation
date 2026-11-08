# Plant species and disease identification

FastAPI app using Pl@ntNet to identify plant species and supported diseases. The browser interface is served from [`index.html`](./index.html). No disease match does not guarantee a healthy plant.

## Run

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env`, set `PLANTNET_API_KEY`, then start the app:

```bash
uvicorn demo:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) for the upload page or [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for Swagger.

## Flow

Choose one or more images and an organ (`auto`, `leaf`, `flower`, `fruit`, `bark`). The page sends each image separately to `POST /identify`. The API fixes image orientation, converts to RGB, resizes to 1600 × 1600 maximum, and re-encodes as JPEG. It then calls Pl@ntNet's disease and species identification endpoints.

Each result card shows the plant's scientific and common names, its score, disease names/codes/scores, and remaining API quota when available. Each image uses two Pl@ntNet requests. Results are limited to Pl@ntNet's supported species and diseases.

## Example response

```json
{
  "status": "ok",
  "plant": {
    "name": "Solanum lycopersicum",
    "common_names": ["tomate"],
    "score": 0.982
  },
  "results": [
    {"eppo_code": "APHISP", "disease_name": "Aphis sp.", "score": 0.914}
  ],
  "remaining_quota": 495
}
```

Keep your API key private; do not commit `.env`.
