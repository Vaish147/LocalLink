# LocalLink — Flask Backend

## Run
1. Open a terminal in the `backend` folder.
2. Create a virtual environment (optional):
   `python -m venv venv`
3. Activate it:
   - Windows: `venv\\Scripts\\activate`
4. Install:
   `pip install -r requirements.txt`
5. Start:
   `python app.py`
6. Open: http://127.0.0.1:5000

The SQLite database is created automatically at `backend/locallink.db`.
Uploaded owner ID proofs and logos are stored in `backend/uploads/`.

## API
- `GET /api/health`
- `POST /api/auth/signup`
- `POST /api/auth/login`
- `POST /api/shops/register` (multipart/form-data)
- `POST /api/shops/login`
- `GET /api/shops?search=&category=&city=`
- `GET /api/shops/<id>`

Passwords are stored as hashes, not plain text.
