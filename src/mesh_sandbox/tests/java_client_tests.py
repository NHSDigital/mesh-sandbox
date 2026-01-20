import os
import pathlib
import shutil
import subprocess
from textwrap import dedent
from time import sleep
from typing import cast
from uuid import uuid4

import pytest
from lxml import etree
from lxml.etree import _ElementTree

from .helpers import ensure_java_client


def configure_client(base_uri: str, version: str):
    base_dir = ensure_java_client(version)

    java_client_config_path = f"{base_dir}/client/meshclient.cfg"
    java_client_jar_path = f"{base_dir}/client/meshClient.jar"
    java_client_log_config = f"-Dlog4j2.configurationFile={base_dir}/client/log4j2.xml"

    assert os.path.exists(java_client_jar_path), "Could not find java mesh client installation"

    # clean the log for this scenario
    pathlib.Path(f"{base_dir}/client/log/mesh.log").unlink(missing_ok=True)

    client_config = etree.parse(java_client_config_path)
    client_config.find("PrimaryURL").text = base_uri  # type: ignore
    client_config.find("KeyStorePassword").text = "password"  # type: ignore
    client_config.find("PollPeriod").text = "1"  # type: ignore
    auth_node = client_config.find("AuthenticationKey")
    if auth_node is None:
        auth_node = etree.Element("AuthenticationKey")
        client_config.getroot().append(auth_node)
    auth_node.text = "TestKey"

    proc_delay = client_config.find("ProcessingDelay")  # type: ignore
    if proc_delay is None:
        proc_delay = etree.Element("ProcessingDelay")
        client_config.getroot().append(proc_delay)
    proc_delay.text = "1"

    client_config.write(java_client_config_path, pretty_print=True)

    for path in os.listdir(f"{base_dir}/data"):
        if path != "_TEMPLATE":
            shutil.rmtree(f"{base_dir}/data/{path}")

    java_home = os.environ.get("JAVA_HOME")
    java_path = f"{java_home}/bin/java" if java_home else "java"

    return base_dir, [
        java_path,
        "-jar",
        java_client_log_config,
        java_client_jar_path,
        java_client_config_path,
    ]


def run_process_and_terminate_after(args: list[str], sleep_for: int = 1):
    process = subprocess.Popen(args)  # pylint: disable=consider-using-with
    # need to hard wait some time for process to start & messages to be sent/received
    # in future we may want to read the log file to determine state

    # make sure process started
    process.poll()
    assert process.returncode is None or process.returncode == 0, (
        f"java process failed to start {process.returncode}",
        " ".join(args),
    )
    try:
        sleep(sleep_for)
    finally:
        process.terminate()


def configure_mailboxes(base_dir: str, mailboxes: list[str]):
    java_client_config_path = f"{base_dir}/client/meshclient.cfg"
    parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)
    root = cast(_ElementTree, etree.parse(java_client_config_path, parser)).getroot()
    # remove existing clients
    client_configs = root.findall("Client")
    for conf in client_configs:
        root.remove(conf)

    for mailbox in mailboxes:
        mailbox = mailbox.strip().upper()
        mailbox_path = os.path.abspath(f"{base_dir}/data/{mailbox}")
        root.append(
            etree.fromstring(
                dedent(
                    f"""<Client>
                    <ClientIdentity>{mailbox}</ClientIdentity>
                    <ClientAuthentication>password</ClientAuthentication>
                    <MailboxType>MESH</MailboxType>
                    <InterfaceRoot>{mailbox_path}</InterfaceRoot>
                    <CollectReport>Y</CollectReport>
                    <TransferReport>N</TransferReport>
                    <PollReport>N</PollReport>
                    <SaveSent>Y</SaveSent>
                </Client>"""
                )
            )
        )
        shutil.copytree(f"{base_dir}/data/_TEMPLATE", mailbox_path)

    root.getroottree().write(java_client_config_path, pretty_print=True)


def send_message(
    data: bytes,
    sender: str,
    recipient: str,
    workflow_id: str,
    subject: str,
    local_id: str,
    base_dir: str,
    compress: bool = True,
):
    file_name = uuid4().hex
    file_path = f"{base_dir}/data/{sender}/OUT/{file_name}"

    with open(f"{file_path}.dat", "wb") as dat_file:
        dat_file.write(data)

    with open(f"{file_path}.ctl", "w", encoding="utf8") as ctl_file:
        ctl_file.write(
            f"""<DTSControl>
<Version>1.0</Version>
<AddressType>DTS</AddressType>
<MessageType>Data</MessageType>
<WorkflowId>{workflow_id}</WorkflowId>
<To_DTS>{recipient}</To_DTS>
<From_DTS>{sender}</From_DTS>
<Subject>{subject}</Subject>
<LocalId>{local_id}</LocalId>
<Compress>{'Y' if compress else 'N'}</Compress>
<AllowChunking>Y</AllowChunking>
<Encrypted>N</Encrypted>
</DTSControl>"""
        )

    sleep(1.5)  # have to wait as client will not pick up files added < 1 sec ago
    return file_name


_CANNED_MAILBOX1 = "X26ABC1"
_CANNED_MAILBOX2 = "X26ABC2"


def find_sent_message_id(ctl_file: str) -> str:
    parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)
    root = cast(_ElementTree, etree.parse(ctl_file, parser)).getroot()
    message_id = root.find("DTSId")
    assert message_id is not None
    return cast(str, message_id.text)


@pytest.mark.parametrize("version", ["6.3.6"])
def test_basic_send_and_receive(base_uri: str, version: str):  # pylint: disable=too-many-locals
    base_dir, client_args = configure_client(base_uri, version)

    sender, recipient = _CANNED_MAILBOX1, _CANNED_MAILBOX2

    configure_mailboxes(base_dir, [sender, recipient])

    message = f"test-{uuid4().hex}".encode()
    workflow_id = uuid4().hex
    subject = uuid4().hex
    local_id = uuid4().hex

    sent_file = send_message(message, sender, recipient, workflow_id, subject, local_id, base_dir)

    run_process_and_terminate_after(client_args, sleep_for=2)
    run_process_and_terminate_after(client_args, sleep_for=2)

    sender_dir = os.path.join(base_dir, f"data/{sender}")
    recipient_dir = os.path.join(base_dir, f"data/{recipient}")

    assert sent_file
    assert os.path.exists(f"{sender_dir}/SENT/{sent_file}.dat")
    assert os.path.exists(f"{sender_dir}/SENT/{sent_file}.ctl")

    message_id = find_sent_message_id(f"{sender_dir}/SENT/{sent_file}.ctl")

    assert os.path.exists(f"{recipient_dir}/IN/{message_id}.dat")
    assert os.path.exists(f"{recipient_dir}/IN/{message_id}.ctl")

    with open(f"{recipient_dir}/IN/{message_id}.dat", "rb") as f:
        read = f.read()
        assert read == message
