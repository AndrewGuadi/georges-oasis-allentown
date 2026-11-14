from pathlib import Path
from dotenv import load_dotenv
from georges_oasis import create_app


load_dotenv(Path(__file__).with_name('.env'), override=False)
app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
