from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=4  # Reduced from default 12 for faster hashing
)

# Bcrypt has a 72-byte limit for passwords
MAX_PASSWORD_LENGTH = 56


def hash_password(password: str) -> str:
    # Truncate to 72 bytes as bcrypt requires
    truncated = password[:MAX_PASSWORD_LENGTH]
    return pwd_context.hash(truncated)


def verify_password(plain: str, hashed: str) -> bool:
    # Truncate to 72 bytes to match what was hashed
    truncated = plain[:MAX_PASSWORD_LENGTH]
    return pwd_context.verify(truncated, hashed)