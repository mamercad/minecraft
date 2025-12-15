"""SSH helper utilities."""

from pathlib import Path


def detect_ssh_keys() -> tuple[Path | None, Path | None]:
    """Detect available SSH key pairs.

    Returns:
        Tuple of (public_key_path, private_key_path) or (None, None) if not found
    """
    home = Path.home()

    # Check for ed25519 key first (more modern)
    ed25519_pub = home / ".ssh" / "id_ed25519.pub"
    ed25519_priv = home / ".ssh" / "id_ed25519"

    if ed25519_pub.exists() and ed25519_priv.exists():
        return ed25519_pub, ed25519_priv

    # Check for RSA key
    rsa_pub = home / ".ssh" / "id_rsa.pub"
    rsa_priv = home / ".ssh" / "id_rsa"

    if rsa_pub.exists() and rsa_priv.exists():
        return rsa_pub, rsa_priv

    # No keys found
    return None, None


def get_default_ssh_key_path() -> str:
    """Get the default SSH public key path.

    Returns:
        String path to default SSH public key, or empty string if none found
    """
    pub_key, _ = detect_ssh_keys()
    return str(pub_key) if pub_key else ""
