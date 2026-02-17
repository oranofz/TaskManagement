"""Generate TOTP code for MFA testing/demo."""
import sys
import pyotp

def generate_code(secret: str) -> str:
    """Generate current TOTP code from secret."""
    totp = pyotp.TOTP(secret)
    return totp.now()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_mfa_code.py <SECRET>")
        print("Example: python generate_mfa_code.py JBSWY3DPEHPK3PXP")
        sys.exit(1)

    secret = sys.argv[1]
    code = generate_code(secret)
    print(f"Current TOTP code: {code}")
    print(f"(Valid for ~30 seconds)")


