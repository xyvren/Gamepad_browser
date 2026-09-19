"""SSL Certificate Generator for local HTTPS support."""
import datetime
import ipaddress
from pathlib import Path
import ssl

def get_or_create_ssl_context(cert_dir: Path, lan_ip: str):
    cert_dir = Path(cert_dir)
    cert_dir.mkdir(parents=True, exist_ok=True)
    cert_file = cert_dir / "pocket_pad_cert.pem"
    key_file = cert_dir / "pocket_pad_key.pem"

    need_generate = True
    if cert_file.exists() and key_file.exists():
        try:
            # Quick check if readable
            ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ctx.load_cert_chain(str(cert_file), str(key_file))
            return ctx, cert_file, key_file
        except Exception:
            need_generate = True

    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"Pocket Pad Local Server"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Pocket Pad")
    ])

    alt_names = [
        x509.DNSName(u"localhost"),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
    ]
    try:
        if lan_ip and lan_ip not in ("127.0.0.1", "0.0.0.0"):
            alt_names.append(x509.IPAddress(ipaddress.IPv4Address(lan_ip)))
    except Exception:
        pass

    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(x509.SubjectAlternativeName(alt_names), critical=False)
        .sign(key, hashes.SHA256())
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )

    cert_file.write_bytes(cert_pem)
    key_file.write_bytes(key_pem)

    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.load_cert_chain(str(cert_file), str(key_file))
    return ctx, cert_file, key_file
