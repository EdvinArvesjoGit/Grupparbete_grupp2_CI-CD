from fastapi import FastAPI

import reports.riksdag.schemas as schemas

app = FastAPI()


@app.get("/riksdagen/ledamoter")
async def get_ledamoter(
    parti: schemas.Parti | None = None,
    kon: schemas.Kon | None = None,
    aldersgrupp: schemas.Aldersgrupp | None = None,
):
    return []
