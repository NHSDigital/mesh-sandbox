import contextlib
import os
import pathlib
import shutil
import subprocess
from datetime import datetime
from typing import Optional
from uuid import uuid4

import httpx
from OpenSSL import crypto

from ..common import MESH_AUTH_SCHEME, generate_cipher_text


def generate_auth_token(
    mailbox_id: str,
    mailbox_password: str = "password",
    secret_key: str = "TestKey",
    timestamp: Optional[datetime] = None,
    nonce: Optional[str] = None,
    nonce_count: str = "1",
) -> str:
    nonce = nonce or uuid4().hex
    timestamp_string = (timestamp or datetime.now()).strftime("%Y%m%d%H%M")
    public_auth_data = f"{mailbox_id}:{nonce}:{nonce_count}:{timestamp_string}"
    cipher_text = generate_cipher_text(secret_key, mailbox_id, mailbox_password, timestamp_string, nonce, nonce_count)
    return f"{MESH_AUTH_SCHEME} {public_auth_data}:{cipher_text}"


@contextlib.contextmanager
def temp_env_vars(**kwargs):
    """
    Temporarily set the process environment variables.
    >>> with temp_env_vars(PLUGINS_DIR=u'test/plugins'):
    ...   "PLUGINS_DIR" in os.environ
    True
    >>> "PLUGINS_DIR" in os.environ
    """
    old_environ = dict(os.environ)
    kwargs = {k: str(v) for k, v in kwargs.items()}
    os.environ.update(**kwargs)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_environ)


def ensure_client_installed(java_path: str, base_dir: str, version: str):  # pylint: disable=too-many-locals
    install_dir = os.path.join(base_dir, version)

    client_dir = os.path.join(install_dir, "client")

    if os.path.exists(os.path.join(client_dir, "meshClient.jar")):
        return

    os.makedirs(install_dir, exist_ok=True)
    installer_dir = os.path.join(install_dir, "installer")
    data_dir = os.path.join(install_dir, "data")

    os.makedirs(installer_dir, exist_ok=True)
    os.makedirs(client_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)

    installer_rar = os.path.join(installer_dir, "installer.rar")
    if not os.path.exists(installer_rar):
        version_dash = version.replace(".", "-")

        installer_uri = (
            "https://digital.nhs.uk/binaries/content/assets/website-assets/services"
            f"/message-exchange-for-social-care-and-health-mesh/mesh-installation-pack-client-{version_dash}.rar"
        )

        with httpx.Client() as client:
            res = client.get(installer_uri)
            with open(installer_rar, "wb+") as f:
                f.write(res.read())

    subprocess.check_call(f"unrar x -y {installer_rar} {installer_dir}".split(" "))

    found = list(pathlib.Path(installer_dir).glob("**/*-installer-signed.jar"))
    assert found
    installer_jar = found[0]

    install_xml = os.path.join(installer_dir, "auto-install.xml")
    with open(install_xml, "w+", encoding="utf-8") as f:
        f.write(
            f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<AutomatedInstallation langpack="eng">
    <com.izforge.izpack.panels.hello.HelloPanel id="HelloPanel_0"/>
    <com.izforge.izpack.panels.target.TargetPanel id="TargetPanel_1">
        <installpath>{client_dir}</installpath>
    </com.izforge.izpack.panels.target.TargetPanel>
    <com.izforge.izpack.panels.userinput.UserInputPanel id="Config.DataLocation">
        <entry key="data.path" value="{data_dir}"/>
    </com.izforge.izpack.panels.userinput.UserInputPanel>
    <com.izforge.izpack.panels.userinput.UserInputPanel id="Config.NewMailboxDetails">
        <entry key="mailboxId" value="_TEMPLATE"/>
        <entry key="mailboxType" value="MESH"/>
    </com.izforge.izpack.panels.userinput.UserInputPanel>
    <com.izforge.izpack.panels.userinput.UserInputPanel id="Config.AllowAutoUpdates">
        <entry key="autoupdate.allow" value="N"/>
    </com.izforge.izpack.panels.userinput.UserInputPanel>
    <com.izforge.izpack.panels.summary.SummaryPanel id="SummaryPanel_6"/>
    <com.izforge.izpack.panels.install.InstallPanel id="InstallPanel_7"/>
    <com.izforge.izpack.panels.process.ProcessPanel id="ProcessPanel_8"/>
    <com.izforge.izpack.panels.finish.FinishPanel id="FinishPanel_9"/>
</AutomatedInstallation>"""
        )

    subprocess.check_call(f"{java_path} -jar {installer_jar} {install_xml}".split(" "))


def ensure_client_keystore(source_keystore: str, base_dir: str, version: str):
    keystore_dir = os.path.join(base_dir, version, "client/KEYSTORE")
    keystore_file = os.path.join(keystore_dir, "mesh.keystore")
    if os.path.exists(keystore_file):
        return

    os.makedirs(keystore_dir, exist_ok=True)
    shutil.copy(source_keystore, keystore_file)


def create_certificate(  # pylint: disable=too-many-arguments
    output_dir: str,
    common_name: str,
    email: str = "mest.test@nhs.net",
    country: str = "GB",
    locality: str = "Leeds",
    state: str = "West Yorkshire",
    organisation: str = "NHS",
    organisation_unit: str = "devices",
    serial=0,
    valid_seconds=10 * 365 * 24 * 60 * 60,
):
    combined_file = os.path.join(output_dir, f"{common_name}.combined.pem")

    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 4096)
    cert = crypto.X509()
    cert.get_subject().C = country
    cert.get_subject().ST = state
    cert.get_subject().L = locality
    cert.get_subject().O = organisation
    cert.get_subject().OU = organisation_unit
    cert.get_subject().CN = common_name
    cert.get_subject().emailAddress = email
    cert.set_serial_number(serial)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(valid_seconds)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, "sha512")
    with open(combined_file, "w+", encoding="utf-8") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode("utf-8"))
        f.write("\n")
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key).decode("utf-8"))

    return combined_file


def ensure_keystore(base_dir: str) -> str:
    certs_dir = os.path.join(base_dir, "certs")
    keystore_file = os.path.join(certs_dir, "mesh.keystore")

    if os.path.exists(keystore_file):
        return keystore_file

    os.makedirs(certs_dir, exist_ok=True)

    cert_file = create_certificate(certs_dir, "client_cert")

    cmd = (
        f"openssl pkcs12 -export -in {cert_file} -out {keystore_file} -name "
        "client_cert -password pass:password -noiter -nomaciter"
    )

    subprocess.check_call(cmd.split(" "))

    return keystore_file


def ensure_java_client(version: str):
    java_home = os.environ.get("JAVA_HOME")
    java_path = f"{java_home}/bin/java" if java_home else "java"

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../java_client"))
    ensure_client_installed(java_path, base_dir, version)
    ensure_client_keystore(ensure_keystore(base_dir), base_dir, version)

    return os.path.join(base_dir, version)
