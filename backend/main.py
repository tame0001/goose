from fastapi import FastAPI

from tui import terminal_ui

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    terminal_ui()
