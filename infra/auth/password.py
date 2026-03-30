from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=4  # Reduced from default 12 for faster hashing
)


def hash_password(password: str) -> str:
    # Bcrypt automatically truncates to 72 bytes
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)