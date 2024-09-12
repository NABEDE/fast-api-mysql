from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text, insert, update, delete, Table, MetaData
from pydantic import BaseModel
import uvicorn
from typing import Optional
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Recuperation des variables d'environnement
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# Construction de l'URL de connexion
DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Initialisation de la connexion SQLAlchemy
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as connection:
        print("Connexion à la base de données réussie!")
except Exception as e:
    print(f"Erreur de connexion à la base de données: {e}")

# Définition du modèle Pydantic pour le corps de la requête
class Post(BaseModel):
    title: str
    body: str
    image: str

class PostUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    image: Optional[str] = None

# Création de l'API 
app = FastAPI()

# Création des routes 
@app.get("/")
def read_root():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT * FROM posts"))
        rows = result.mappings().all()
        return [dict(row) for row in rows]

#Insertion des informations dans la table

metadata = MetaData()
posts_table = Table('posts', metadata, autoload_with=engine)

@app.post("/posts/")
def create_post(post: Post):
    if not post.title or not post.body or not post.image:
        raise HTTPException(status_code=400, detail="Tous les champs sont requis.")

    try:
        with engine.connect() as connection:
            stmt = posts_table.insert().values(**post.dict())
            result = connection.execute(stmt)
            connection.commit()
            if result.rowcount == 0:
                raise HTTPException(status_code=400, detail="Erreur lors de l'insertion du post.")
            return {"message": "Post créé avec succès!", "id": result.inserted_primary_key[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


#Récupérer une imformation de la table
@app.get("/posts/{post_id}")
def read_post(post_id: int):
    with engine.connect() as connection:
        result = connection.execute(text("SELECT * FROM posts WHERE id = :id"), {"id": post_id})
        post = result.mappings().first()
        if post is None:
            raise HTTPException(status_code=404, detail="Post non trouvé")
        return dict(post)


#Mise à jour des informations dans la base de donnée
@app.put("/posts/{post_id}")
def update_post(post_id: int, post: PostUpdate):
    try:
        with engine.connect() as connection:
            update_data = {k: v for k, v in post.dict().items() if v is not None}
            if not update_data:
                raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")

            stmt = update(posts_table).where(posts_table.c.id == post_id).values(**update_data)
            result = connection.execute(stmt)

            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Post non trouvé")

            connection.commit()
            return {"message": "Post mis à jour avec succès"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


#Suppression d'une information
@app.delete("/posts/{post_id}")
def delete_post(post_id: int):
    with engine.connect() as connection:
        stmt = delete(posts_table).where(posts_table.c.id == post_id)
        result = connection.execute(stmt)
        connection.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Post non trouvé")
        
        return {"message": "Post supprimé avec succès"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8001, reload=True)
