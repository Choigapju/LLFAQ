from app.database.session import reset_database
from app.models.faq import FAQ  # FAQ 모델을 import

if __name__ == "__main__":
    reset_database()