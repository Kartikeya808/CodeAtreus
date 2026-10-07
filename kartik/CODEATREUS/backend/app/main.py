
import fastapi
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str

app = FastAPI()

@app.get("/users")
def read_users():
    return [User(id=1, name="John Doe"), User(id=2, name="Jane Doe")]