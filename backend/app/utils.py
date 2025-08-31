import secrets, string
ALPHABET = string.ascii_letters + string.digits
def generate_code(n: int = 7) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(n))
