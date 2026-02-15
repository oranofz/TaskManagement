"""Generate RSA keys for JWT signing."""
import os
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


def generate_keys():
    """Generate RSA key pair for JWT signing."""
    # Create keys directory if it doesn't exist
    os.makedirs("keys", exist_ok=True)

    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Generate public key
    public_key = private_key.public_key()

    # Save private key
    with open("keys/jwt_private.pem", "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
        )

    # Save public key
    with open("keys/jwt_public.pem", "wb") as f:
        f.write(
            public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        )

    print("JWT keys generated successfully!")
    print("Private key: keys/jwt_private.pem")
    print("Public key: keys/jwt_public.pem")


if __name__ == "__main__":
    generate_keys()

