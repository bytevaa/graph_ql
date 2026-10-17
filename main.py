
import requests
import strawberry

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from strawberry.fastapi import GraphQLRouter

app = FastAPI(title="Book Finder")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

OPEN_LIBRARY_URL = "https://openlibrary.org/search.json"

def search_books(title: str, limit: int = 10):
    response = requests.get(
        OPEN_LIBRARY_URL,
        params={
            "title": title,
            "limit": limit,
            "fields": "title,author_name,first_publish_year,cover_i"
        },
        timeout=10
    )
    response.raise_for_status()

    data = response.json()
    books = []

    for item in data.get("docs", []):
        authors = item.get("author_name", [])

        books.append({
            "title": item.get("title", "Без названия"),
            "author": ", ".join(authors) if authors else "Не указан",
            "year": item.get("first_publish_year"),
            "cover_id": item.get("cover_i")
        })

    return books


# Главная страница
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html")

# ---------- REST API ----------
@app.get("/rest/books")
def get_books(title: str, limit: int = 10):
    if not title.strip():
        raise HTTPException(status_code=400, detail="Введите название книги")

    if not 1 <= limit <= 20:
        raise HTTPException(status_code=400, detail="Лимит должен быть от 1 до 20")

    try:
        return {"books": search_books(title, limit)}
    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Open Library временно недоступен"
        )

# ---------- GraphQL API ----------
@strawberry.type
class Book:
    title: str
    author: str
    year: int | None
    cover_id: int | None


@strawberry.type
class Query:

    @strawberry.field
    def search_books(self, title: str, limit: int = 10) -> list[Book]:
        if not title.strip():
            raise ValueError("Введите название книги")

        if not 1 <= limit <= 20:
            raise ValueError("Лимит должен быть от 1 до 20")

        books = search_books(title, limit)
        return [Book(**book) for book in books]


schema = strawberry.Schema(query=Query)
graphql_router = GraphQLRouter(schema)

app.include_router(graphql_router, prefix="/graphql")
