#!/usr/bin/env python3
"""Run once to generate Ed25519 portfolio signing keys. Add output to .env"""
import base64

import nacl.signing  # type: ignore[import]

signing_key = nacl.signing.SigningKey.generate()
verify_key = signing_key.verify_key

private_b64 = base64.b64encode(bytes(signing_key)).decode()
public_b64 = base64.b64encode(bytes(verify_key)).decode()

print(f"PORTFOLIO_SIGNING_PRIVATE_KEY={private_b64}")
print(f"PORTFOLIO_SIGNING_PUBLIC_KEY={public_b64}")
print("\nAdd both lines to your .env file")
