from fastapi import FastAPI


app = FastAPI()

@app.get('/')
def root():
    return {"message": "Your API is Working!"}
